"""表格展示器 - 封装Rich表格展示逻辑"""
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table


class TablePresenter:
    """
    表格展示器
    
    职责：
    - 格式化数据为表格
    - 提供统一的表格展示接口
    - 支持多种样式和配置
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        初始化表格展示器
        
        Args:
            console: Rich Console实例（可选）
        """
        self.console = console or Console()
    
    def display_tools_table(self, tools: List[Any], title: str = "可用工具列表"):
        """
        展示工具列表
        
        Args:
            tools: 工具列表
            title: 表格标题
        """
        table = Table(title=title)
        table.add_column("工具名", style="cyan", no_wrap=True)
        table.add_column("描述", style="magenta")
        
        for tool in tools:
            table.add_row(tool.name, tool.description)
        
        self.console.print(table)
        self.console.print(f"\n[dim]共 {len(tools)} 个工具[/dim]")
    
    def display_config_table(self, config_dict: Dict[str, Any], title: str = "当前配置"):
        """
        展示配置信息
        
        Args:
            config_dict: 配置字典
            title: 表格标题
        """
        table = Table(title=title)
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        
        for key, value in config_dict.items():
            table.add_row(key, str(value))
        
        self.console.print(table)
    
    def display_generic_table(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        title: Optional[str] = None,
        column_styles: Optional[Dict[str, str]] = None
    ):
        """
        展示通用表格
        
        Args:
            data: 数据列表，每项为字典
            columns: 列名列表
            title: 表格标题（可选）
            column_styles: 列样式字典（可选）
        """
        table = Table(title=title) if title else Table()
        
        # 添加列
        for col in columns:
            style = column_styles.get(col, "white") if column_styles else "white"
            table.add_column(col, style=style)
        
        # 添加数据
        for item in data:
            row = [str(item.get(col, "")) for col in columns]
            table.add_row(*row)
        
        self.console.print(table)
        
        if data:
            self.console.print(f"\n[dim]共 {len(data)} 条记录[/dim]")

