"""Document Agent - 公告文档分析Agent"""
import logging
from pathlib import Path

import yaml
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.llm.manager import get_llm_manager
from src.tools.loader import get_tools_for_agent
from src.utils.prompts import DOCUMENT_AGENT_SYSTEM_PROMPT, get_prompt_loader
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
    # 获取项目根目录（hkex-analysis/）
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    config_file = project_root / "config" / "agents.yaml"

    logger.debug(f"尝试加载配置文件: {config_file}")

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                agent_config = config.get("sub_agents", {}).get(agent_name, {})
                logger.debug(f"Agent '{agent_name}' 配置: enabled={agent_config.get('enabled')}")
                return agent_config
        except Exception as e:
            logger.warning(f"加载Agent配置失败: {e}")
            logger.warning(f"配置文件路径: {config_file}")
    else:
        logger.warning(f"配置文件不存在: {config_file}")

    return {}


def create_document_agent():
    """
    创建Document Agent
    
    使用create_react_agent构建，支持配置化模型选择和工具加载
    
    Returns:
        配置好的Document Agent实例
    """
    # 1. 加载配置
    from src.config.settings import get_settings
    settings = get_settings()
    agent_config = load_agent_config("document")

    if not agent_config.get("enabled", False):
        raise ValueError("Document Agent未启用，请检查config/agents.yaml")

    # 2. 获取LLM模型
    llm_manager = get_llm_manager()

    # 配置优先级: YAML配置 > Settings默认值
    # 优先使用 Settings 中的模型配置（从 .env 读取）
    model_name = agent_config.get("model") or settings.siliconflow_fast_model
    temperature = agent_config.get("temperature", 0.1)

    logger.info(f"Document Agent 使用模型: {model_name}")

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

    # 4. 构建系统提示词（优先使用配置，否则使用硬编码）
    task_placeholder = "{task}"  # 运行时会被替换
    prompt_loader = get_prompt_loader()
    
    # 从配置加载提示词模板，如果不存在则使用默认
    prompt_template = prompt_loader.get_prompt(
        "document_agent_system_prompt",
        DOCUMENT_AGENT_SYSTEM_PROMPT
    )
    system_prompt = prompt_template.format(task=task_placeholder)
    
    logger.info(f"Document Agent 提示词已加载（配置化={prompt_template != DOCUMENT_AGENT_SYSTEM_PROMPT}）")

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
