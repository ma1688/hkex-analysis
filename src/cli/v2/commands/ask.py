"""Ask命令 - 使用Click实现的单次问答命令"""
import asyncio
import uuid
import signal
from typing import Optional

import click
from rich.console import Console

from src.cli.v2.services.agent_service import get_agent_service
from src.cli.v2.services.context_service import get_context_service
from src.cli.v2.presenters.stream_presenter import StreamPresenter


@click.command()
@click.argument('question', type=str)
@click.option(
    '--session', '-s',
    type=str,
    default=None,
    help='会话ID（可选）'
)
@click.option(
    '--thoughts/--no-thoughts',
    default=True,
    help='是否显示思考过程'
)
@click.option(
    '--detailed', '-d',
    is_flag=True,
    default=False,
    help='详细模式（显示完整内容）'
)
def ask(
    question: str,
    session: Optional[str],
    thoughts: bool,
    detailed: bool
):
    """
    单次问答命令
    
    示例：
    \b
        hkex-agent ask "查询腾讯控股最近的配售公告"
        hkex-agent ask "查询00700配售数据" --no-thoughts
        hkex-agent ask "问题" -d  # 详细模式
    """
    # 在新事件循环中运行异步函数
    asyncio.run(async_ask(question, session, thoughts, detailed))


async def async_ask(
    question: str,
    session: Optional[str],
    thoughts: bool,
    detailed: bool
):
    """
    异步执行问答逻辑

    Args:
        question: 用户问题
        session: 会话ID
        thoughts: 是否显示思考过程
        detailed: 是否显示详细内容
    """
    console = Console()
    agent_service = get_agent_service()

    # 记录原始信号处理器
    original_handler = None
    if hasattr(signal, 'SIGINT'):
        try:
            original_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        except (ValueError, OSError):
            pass

    try:
        # 初始化服务
        context_service = get_context_service()
        presenter = StreamPresenter(console, detailed)

        # 会话ID
        session_id = session or str(uuid.uuid4())

        # 上下文注入
        enhanced_query, context_info = await context_service.enhance_query(
            question,
            user_id="cli_user"
        )

        # 显示上下文信息
        if context_service.should_display_context(context_info):
            presenter.display_context_info(context_info)

        # 显示问题和模型信息
        console.print(f"\n[bold cyan]问题:[/bold cyan] {question}")
        console.print(
            f"[dim]📍 模型: [cyan]{agent_service.model_name}[/cyan] "
            f"(温度: {agent_service.temperature})[/dim]\n"
        )
        console.print("[dim]💡 提示: 执行过程中按 Ctrl+C 可中断Agent[/dim]\n")

        if thoughts:
            # 流式展示思考过程
            event_stream = agent_service.ask_stream(enhanced_query, session_id)
            answer = await presenter.display_stream(event_stream)

            # 显示最终答案（如果不是中断的）
            if not presenter.is_interrupted():
                presenter.display_answer(answer)
        else:
            # 普通模式（不显示思考过程）
            with console.status("[bold green]思考中..."):
                result = agent_service.ask_sync(enhanced_query, session_id)
                answer = agent_service.extract_answer(result)

                if not answer:
                    answer = "无法生成答案"

            # 显示答案
            console.print("[bold green]回答:[/bold green]")
            console.print(answer)

        console.print(f"\n[dim]会话ID: {session_id}[/dim]")

    except KeyboardInterrupt:
        # 处理Ctrl+C
        console.print("\n[bold red]⚠️  中断信号已发送[/bold red]")
        console.print("[dim]💡 等待Agent停止（最多50ms）...[/dim]")
        # 中断Agent
        agent_service.interrupt()
        # 短暂等待Agent停止
        import time
        time.sleep(0.1)
        console.print("[bold yellow]✅ 操作已取消[/bold yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()
    finally:
        # 恢复原始信号处理器
        if hasattr(signal, 'SIGINT') and original_handler is not None:
            try:
                signal.signal(signal.SIGINT, original_handler)
            except:
                pass


if __name__ == "__main__":
    ask()

