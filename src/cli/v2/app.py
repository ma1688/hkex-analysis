"""CLI主入口 - 使用Click Group组织命令"""
import click
from src.cli.v2.commands.ask import ask
from src.cli.v2.commands.chat import chat
from src.cli.v2.commands.tools import tools_list
from src.cli.v2.commands.config import show_config


@click.group()
@click.version_option(version="0.2.0", prog_name="hkex-agent")
def cli():
    """
    HK Stock Analysis Agent - 港股公告智能问答系统 v2
    
    基于LangGraph的多Agent架构，全新CLI实现：
    - 原生异步支持（Click 8.1+）
    - 分层架构（Services/Presenters）
    - 交互式增强（Prompt-Toolkit）
    """
    pass


# 注册命令
cli.add_command(ask)
cli.add_command(chat)
cli.add_command(tools_list)
cli.add_command(show_config)


# 添加 version 命令
@cli.command()
def version():
    """显示版本信息"""
    from rich.console import Console
    console = Console()
    console.print("[bold green]HK Stock Analysis Agent v2[/bold green]")
    console.print("Version: [cyan]0.2.0[/cyan]")
    console.print("基于LangGraph的港股公告智能问答系统")
    console.print("\n[dim]架构升级:[/dim]")
    console.print("  • 原生异步支持（零事件循环管理）")
    console.print("  • 分层架构（Services → Presenters）")
    console.print("  • 交互式CLI（Prompt-Toolkit）")


if __name__ == "__main__":
    cli()

