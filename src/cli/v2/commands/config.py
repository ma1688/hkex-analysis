"""Config命令 - 配置查看"""
import click
from rich.console import Console

from src.config.settings import get_settings
from src.cli.v2.presenters.table_presenter import TablePresenter


@click.command('config')
def show_config():
    """
    显示当前配置
    
    示例：
    \b
        hkex-agent config
    """
    console = Console()
    
    try:
        # 获取配置
        settings = get_settings()
        
        # 构建配置字典
        config_dict = {
            "环境": settings.app_env,
            "端口": str(settings.app_port),
            "日志级别": settings.app_log_level,
            "ClickHouse Host": settings.clickhouse_host,
            "ClickHouse DB": settings.clickhouse_database,
            "快速模型": settings.siliconflow_fast_model,
            "强模型": settings.siliconflow_strong_model,
        }
        
        # 展示表格
        presenter = TablePresenter(console)
        presenter.display_config_table(config_dict)
        
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise click.Abort()


if __name__ == "__main__":
    show_config()

