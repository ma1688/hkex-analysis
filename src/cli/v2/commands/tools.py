"""Tools命令 - 工具列表查看"""
import click
from rich.console import Console

from src.tools.loader import load_all_tools
from src.cli.v2.presenters.table_presenter import TablePresenter


@click.command('tools-list')
def tools_list():
    """
    列出所有可用工具
    
    示例：
    \b
        hkex-agent tools-list
    """
    console = Console()
    
    try:
        # 加载工具
        tools = load_all_tools()
        
        # 展示表格
        presenter = TablePresenter(console)
        presenter.display_tools_table(tools)
        
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise click.Abort()


if __name__ == "__main__":
    tools_list()

