"""Document Agent - 公告文档分析Agent"""
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
import logging
import yaml
from pathlib import Path

from src.llm.manager import get_llm_manager
from src.tools.loader import get_tools_for_agent
from src.utils.prompts import DOCUMENT_AGENT_SYSTEM_PROMPT
from src.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


def clean_message(message: BaseMessage) -> BaseMessage:
    """清理消息中的无效UTF-8字符"""
    if isinstance(message, HumanMessage):
        return HumanMessage(content=clean_text(message.content))
    elif isinstance(message, AIMessage):
        cleaned_content = clean_text(message.content)
        # 保留tool_calls但不修改
        return AIMessage(
            content=cleaned_content,
            tool_calls=message.tool_calls if hasattr(message, 'tool_calls') else []
        )
    elif isinstance(message, ToolMessage):
        return ToolMessage(
            content=clean_text(message.content),
            tool_call_id=message.tool_call_id
        )
    elif isinstance(message, SystemMessage):
        return SystemMessage(content=clean_text(message.content))
    else:
        # 其他类型消息，尝试清理content
        try:
            if hasattr(message, 'content'):
                message.content = clean_text(message.content)
        except:
            pass
        return message


def load_agent_config(agent_name: str = "document") -> dict:
    """从配置文件加载Agent配置"""
    config_file = Path("config/agents.yaml")
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("sub_agents", {}).get(agent_name, {})
        except Exception as e:
            logger.warning(f"加载Agent配置失败: {e}")
    return {}


def create_document_agent():
    """
    创建Document Agent
    
    使用create_react_agent构建，支持配置化模型选择和工具加载
    
    Returns:
        配置好的Document Agent实例
    """
    # 1. 加载配置
    agent_config = load_agent_config("document")
    
    if not agent_config.get("enabled", False):
        raise ValueError("Document Agent未启用，请检查config/agents.yaml")
    
    # 2. 获取LLM模型
    llm_manager = get_llm_manager()
    
    # 根据配置选择模型
    model_name = agent_config.get("model")
    temperature = agent_config.get("temperature", 0.1)
    
    # 创建模型配置
    model_config = {
        "model": model_name,
        "temperature": temperature
    }
    
    # 获取模型实例
    llm = llm_manager.get_model_for_task("query", model_config)
    
    # 注意：消息清理已在工具层完成，LLM直接使用即可
    
    # 3. 加载工具
    tools = get_tools_for_agent("document")
    
    if not tools:
        logger.warning("Document Agent没有可用工具，将使用空工具列表")
    
    logger.info(f"Document Agent 加载了 {len(tools)} 个工具")
    
    # 4. 构建系统提示词
    task_placeholder = "{task}"  # 运行时会被替换
    system_prompt = DOCUMENT_AGENT_SYSTEM_PROMPT.format(task=task_placeholder)
    
    # 5. 创建checkpointer（用于会话持久化）
    checkpointer = MemorySaver()
    
    # 6. 创建Agent
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
        checkpointer=checkpointer
    )
    
    logger.info(f"Document Agent 创建成功: model={model_name}, tools={len(tools)}")
    
    return agent


# 便捷函数：创建并缓存agent
_document_agent = None


def get_document_agent():
    """获取Document Agent单例"""
    global _document_agent
    if _document_agent is None:
        _document_agent = create_document_agent()
    return _document_agent

