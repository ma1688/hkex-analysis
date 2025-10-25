"""FastAPI主应用"""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.agent.context_injector import inject_query_context
from src.agent.document_agent import get_document_agent
from src.agent.memory import get_memory_manager
from src.agent.supervisor import get_supervisor
from src.api.schemas import (
    QueryRequest, QueryResponse, HealthResponse,
    ToolInfo, ToolCallRecord, SessionHistoryResponse
)
from src.config.settings import get_settings
from src.llm.manager import get_llm_manager
from src.tools.loader import load_all_tools
from src.utils.clickhouse import get_clickhouse_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
settings = get_settings()
app = FastAPI(
    title="HK Stock Analysis Agent API",
    description="基于LangGraph的港股公告智能问答系统",
    version="0.1.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    logger.info("=" * 50)
    logger.info("HK Stock Analysis Agent API Starting...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Port: {settings.app_port}")
    logger.info("=" * 50)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HK Stock Analysis Agent API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    问答接口
    
    提交问题，同步返回Agent分析结果
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    try:
        logger.info(f"收到查询: {request.question[:50]}... (session: {session_id})")

        # 上下文注入 - Layer 2
        enhanced_query, context_info = inject_query_context(
            request.question,
            request.user_id
        )

        if context_info.get("injected"):
            logger.info(f"上下文已注入，置信度: {context_info.get('confidence', 0):.2f}")
            logger.debug(f"注入上下文: {context_info.get('injected_context', [])}")

        # 获取Document Agent
        agent = get_document_agent()

        # 构建配置
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        # 调用Agent（使用增强后的查询）
        result = agent.invoke(
            {"messages": [("user", enhanced_query)]},
            config
        )

        # 提取答案
        messages = result.get("messages", [])
        answer = messages[-1].content if messages else "无法生成答案"

        # 处理工具调用记录
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(ToolCallRecord(
                        tool_name=tc.get("name", "unknown"),
                        tool_input=tc.get("args", {}),
                        tool_output="",  # 简化版不详细追踪
                        timestamp=datetime.now(),
                        agent="document"
                    ))

        processing_time = time.time() - start_time

        logger.info(f"查询完成: {processing_time:.2f}s, 工具调用{len(tool_calls)}次")

        return QueryResponse(
            answer=answer,
            session_id=session_id,
            user_id=request.user_id,
            tool_calls=tool_calls,
            processing_time=processing_time,
            metadata={
                "agent": "document",
                "message_count": len(messages)
            }
        )

    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/stream")
async def stream_query(request: QueryRequest):
    """
    流式问答接口
    
    使用Server-Sent Events (SSE)流式返回Agent执行过程
    """
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        try:
            logger.info(f"流式查询开始: {request.question[:50]}... (session: {session_id})")

            # 上下文注入 - Layer 2
            enhanced_query, context_info = inject_query_context(
                request.question,
                request.user_id
            )

            if context_info.get("injected"):
                logger.info(f"流式查询上下文已注入，置信度: {context_info.get('confidence', 0):.2f}")
                logger.debug(f"流式查询注入上下文: {context_info.get('injected_context', [])}")

            # 发送开始事件
            start_data = {
                'session_id': session_id,
                'question': request.question,
                'context_injected': context_info.get("injected", False),
                'confidence': context_info.get("confidence", 0)
            }
            yield f"event: start\ndata: {json.dumps(start_data)}\n\n"

            # 获取Supervisor
            supervisor = get_supervisor()

            # 构建初始状态（dict形式，包含supervisor节点需要的所有字段）
            initial_state = {
                # 基础字段（Supervisor实际使用的）
                "query": enhanced_query,  # 使用增强后的查询
                "original_query": request.question,  # 保留原始查询
                "user_id": request.user_id or "anonymous",
                "session_id": session_id,
                "messages": [],
                "context": {
                    "context_injected": context_info.get("injected", False),
                    "injection_info": context_info
                },

                # 规划字段
                "plan": [],
                "current_step": 0,

                # 执行字段
                "agent_results": {},
                "reflection_notes": [],

                # 会话字段
                "user_profile": {},
                "session_context": {},

                # 元数据字段
                "processing_start": datetime.now(),
                "tool_calls": [],
                "error_count": 0
            }

            config = {"configurable": {"thread_id": session_id}}

            # 流式执行
            step_count = 0
            async for event in supervisor.graph.astream(initial_state, config):
                step_count += 1

                # 提取事件信息
                node_name = list(event.keys())[0] if event else "unknown"
                node_data = event.get(node_name, {})

                # 发送步骤事件
                stream_event = {
                    "event": "step",
                    "data": {
                        "step": step_count,
                        "node": node_name,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield f"event: step\ndata: {json.dumps(stream_event)}\n\n"

                # 如果是计划节点，发送计划
                if node_name == "plan" and "plan" in node_data:
                    plan_event = {
                        "event": "plan",
                        "data": {"plan": str(node_data.get("plan", {}))}
                    }
                    yield f"event: plan\ndata: {json.dumps(plan_event)}\n\n"

                # 如果是执行节点，发送进度
                if node_name in ["execute_document"]:
                    progress_event = {
                        "event": "progress",
                        "data": {
                            "current_step": node_data.get("current_step", 0),
                            "message": "执行中..."
                        }
                    }
                    yield f"event: progress\ndata: {json.dumps(progress_event)}\n\n"

                # 如果是反思节点，发送反思结果
                if node_name == "reflect" and "reflection" in node_data:
                    reflection_event = {
                        "event": "reflection",
                        "data": {"reflection": str(node_data.get("reflection", {}))}
                    }
                    yield f"event: reflection\ndata: {json.dumps(reflection_event)}\n\n"

                # 等待一小段时间，确保客户端能接收
                await asyncio.sleep(0.01)

            # 获取最终结果
            final_state = event.get(list(event.keys())[0], {}) if event else {}
            final_answer = final_state.get("final_answer", "无法生成答案")

            # 发送最终答案
            answer_event = {
                "event": "answer",
                "data": {
                    "answer": final_answer,
                    "session_id": session_id,
                    "total_steps": step_count
                }
            }
            yield f"event: answer\ndata: {json.dumps(answer_event)}\n\n"

            # 发送完成事件
            yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

            logger.info(f"流式查询完成: {step_count}步")

        except Exception as e:
            logger.error(f"流式查询失败: {e}", exc_info=True)
            error_event = {
                "event": "error",
                "data": {"error": str(e)}
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/v1/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
        session_id: str,
        limit: int = 50,
        offset: int = 0
):
    """
    获取会话历史
    
    返回指定会话的对话历史记录
    """
    try:
        logger.info(f"获取会话历史: {session_id}, limit={limit}, offset={offset}")

        # 获取Memory Manager
        memory_manager = get_memory_manager()

        # 获取消息历史
        all_messages = memory_manager.get_messages(session_id)

        # 应用分页
        total = len(all_messages)
        start = offset
        end = offset + limit
        messages = all_messages[start:end]

        # 转换消息格式
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.__class__.__name__.replace("Message", "").lower(),
                "content": msg.content,
                "timestamp": datetime.now().isoformat()  # 简化版，实际应从消息中获取
            })

        # 获取会话元数据
        metadata = memory_manager.get_session_metadata(session_id) or {}

        return SessionHistoryResponse(
            session_id=session_id,
            messages=formatted_messages,
            total=total,
            offset=offset,
            limit=limit,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"获取会话历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    services = {}
    overall_status = "healthy"

    # 检查ClickHouse
    try:
        ch_manager = get_clickhouse_manager()
        if ch_manager.test_connection():
            services["clickhouse"] = "healthy"
        else:
            services["clickhouse"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        services["clickhouse"] = f"unhealthy: {str(e)[:30]}"
        overall_status = "degraded"

    # 检查LLM
    try:
        llm_manager = get_llm_manager()
        llm_health = llm_manager.check_health()
        services.update(llm_health)

        # 如果有任何LLM不健康，降级状态
        if any("unhealthy" in v for v in llm_health.values()):
            overall_status = "degraded"
    except Exception as e:
        services["llm"] = f"unhealthy: {str(e)[:30]}"
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        services=services,
        timestamp=datetime.now(),
        version="0.1.0"
    )


@app.get("/api/v1/tools")
async def list_tools():
    """列出所有可用工具"""
    try:
        all_tools = load_all_tools()

        tools_info = []
        for tool in all_tools:
            tools_info.append(ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters={},  # 简化版
                agent="document",
                enabled=True
            ))

        return {
            "tools": tools_info,
            "total": len(tools_info)
        }
    except Exception as e:
        logger.error(f"列出工具失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
