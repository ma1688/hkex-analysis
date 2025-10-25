"""工具自动加载器 - 扫描并加载custom目录下的工具"""
import importlib
import inspect
import logging
from pathlib import Path
from typing import List
from langchain_core.tools import BaseTool
import yaml

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ToolLoader:
    """工具加载器 - 自动加载所有工具并支持配置控制"""
    
    def __init__(self, custom_dir: str = "src/tools/custom"):
        self.custom_dir = Path(custom_dir)
        self.config = self._load_config()
        self._all_tools: List[BaseTool] = []
    
    def _load_config(self) -> dict:
        """从配置文件加载工具配置"""
        config_file = Path("config/tools.yaml")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"加载工具配置失败: {e}")
        return {}
    
    def load_all_tools(self) -> List[BaseTool]:
        """加载所有工具（内置+自定义）"""
        if self._all_tools:
            return self._all_tools
        
        tools = []
        
        # 1. 加载内置工具
        tools.extend(self._load_built_in_tools())
        
        # 2. 加载自定义工具
        if self.config.get("custom_tools", {}).get("enabled", True):
            tools.extend(self._load_custom_tools())
        
        # 3. 过滤禁用的工具
        disabled = self.config.get("custom_tools", {}).get("disabled_tools", [])
        tools = [t for t in tools if t.name not in disabled]
        
        self._all_tools = tools
        logger.info(f"加载工具完成: {len(tools)}个工具")
        return tools
    
    def _load_built_in_tools(self) -> List[BaseTool]:
        """加载内置工具"""
        tools = []
        
        # 导入内置工具模块
        builtin_modules = [
            "src.tools.structured_data",
            "src.tools.document_retrieval",
            "src.tools.synthesis",
            "src.tools.time_utils"
        ]
        
        for module_name in builtin_modules:
            try:
                module = importlib.import_module(module_name)
                
                # 获取模块中所有的工具
                for name, obj in inspect.getmembers(module):
                    if isinstance(obj, BaseTool):
                        tools.append(obj)
                        logger.debug(f"加载内置工具: {obj.name} from {module_name}")
            except Exception as e:
                logger.warning(f"加载模块 {module_name} 失败: {e}")
        
        return tools
    
    def _load_custom_tools(self) -> List[BaseTool]:
        """自动加载custom目录下的所有@tool装饰的函数"""
        tools = []
        
        if not self.custom_dir.exists():
            logger.info(f"自定义工具目录不存在: {self.custom_dir}")
            return tools
        
        # 扫描所有Python文件
        for py_file in self.custom_dir.glob("*.py"):
            if py_file.stem.startswith("_"):
                continue
            
            try:
                # 动态导入模块
                module_name = f"src.tools.custom.{py_file.stem}"
                module = importlib.import_module(module_name)
                
                # 查找所有Tool对象
                for name, obj in inspect.getmembers(module):
                    if isinstance(obj, BaseTool):
                        tools.append(obj)
                        logger.info(f"加载自定义工具: {obj.name} from {py_file.name}")
            
            except Exception as e:
                logger.error(f"加载自定义工具失败 {py_file}: {e}")
        
        return tools
    
    def get_tools_by_agent(self, agent_name: str) -> List[BaseTool]:
        """根据Agent名称获取对应的工具列表"""
        # 从配置中读取该agent的工具列表
        agents_config = self._load_agents_config()
        agent_config = agents_config.get("sub_agents", {}).get(agent_name, {})
        tool_names = agent_config.get("tools", [])
        
        if not tool_names:
            logger.warning(f"Agent {agent_name} 没有配置工具")
            return []
        
        # 加载所有工具
        all_tools = self.load_all_tools()
        
        # 过滤出该agent需要的工具
        agent_tools = [t for t in all_tools if t.name in tool_names]
        
        logger.info(f"为Agent {agent_name} 加载了 {len(agent_tools)} 个工具")
        return agent_tools
    
    def _load_agents_config(self) -> dict:
        """加载agents配置"""
        config_file = Path("config/agents.yaml")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"加载agents配置失败: {e}")
        return {}


# 全局单例
_tool_loader: ToolLoader | None = None


def get_tool_loader() -> ToolLoader:
    """获取工具加载器单例"""
    global _tool_loader
    if _tool_loader is None:
        _tool_loader = ToolLoader()
    return _tool_loader


def load_all_tools() -> List[BaseTool]:
    """快捷函数：加载所有工具"""
    return get_tool_loader().load_all_tools()


def get_tools_for_agent(agent_name: str) -> List[BaseTool]:
    """快捷函数：获取特定Agent的工具"""
    return get_tool_loader().get_tools_by_agent(agent_name)

