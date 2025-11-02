"""Chat命令 - 使用Click+Prompt-Toolkit实现的交互式对话"""
import asyncio
import uuid
import signal
import os
from pathlib import Path

import click
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from src.cli.v2.services.agent_service import get_agent_service
from src.cli.v2.services.context_service import get_context_service
from src.cli.v2.presenters.stream_presenter import StreamPresenter


# Prompt-Toolkit 样式
prompt_style = Style.from_dict({
    'prompt': '#00aa00 bold',
})


@click.command()
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
def chat(thoughts: bool, detailed: bool):
    """
    交互式对话命令
    
    示例：
    \b
        hkex-agent chat                  # 显示思考过程（默认）
        hkex-agent chat --no-thoughts    # 不显示思考过程
        hkex-agent chat -d               # 详细模式
    """
    # 在新事件循环中运行异步函数
    asyncio.run(async_chat(thoughts, detailed))


async def async_chat(thoughts: bool, detailed: bool):
    """
    异步执行交互式对话逻辑

    Args:
        thoughts: 是否显示思考过程
        detailed: 是否显示详细内容
    """
    console = Console()
    agent_service = get_agent_service()

    # 全局Ctrl+C标志
    global_interrupt = False

    def global_signal_handler(signum, frame):
        """全局Ctrl+C信号处理器（立即响应）"""
        nonlocal global_interrupt
        if not global_interrupt:  # 避免重复处理
            global_interrupt = True
            # 立即中断Agent执行
            agent_service.interrupt()
            console.print("\n[bold red]⚠️  中断信号已发送[/bold red]")
            console.print("[dim]💡 等待Agent停止（最多50ms）...[/dim]")

    # 注册全局信号处理器
    if hasattr(signal, 'SIGINT'):
        try:
            signal.signal(signal.SIGINT, global_signal_handler)
        except (ValueError, OSError):
            pass

    try:
        # 初始化服务
        context_service = get_context_service()
        presenter = StreamPresenter(console, detailed)

        # 会话ID
        session_id = str(uuid.uuid4())

        # 显示欢迎信息
        console.print(f"[bold green]开始对话[/bold green] (会话ID: {session_id})")
        console.print(
            f"[dim]📍 模型: [cyan]{agent_service.model_name}[/cyan] "
            f"(温度: {agent_service.temperature})[/dim]"
        )
        console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]")
        console.print("[dim]💡 提示: 执行过程中按 Ctrl+C 可中断Agent[/dim]")

        if thoughts:
            mode_desc = "详细模式" if detailed else "简洁模式"
            console.print(f"[dim]💡 提示: 思考过程展示已启用 ({mode_desc})[/dim]\n")
        else:
            console.print("[dim]💡 提示: 使用 --thoughts 可查看思考过程[/dim]\n")

        # 创建Prompt会话（带历史记录）
        history_file = Path.home() / ".hkex_agent_history"
        session = PromptSession(
            history=FileHistory(str(history_file)),
            style=prompt_style
        )

        while True:
            try:
                # 检查全局中断标志
                if global_interrupt:
                    console.print("\n[bold yellow]⚠️  已中断，正在退出...[/bold yellow]")
                    break

                # 获取用户输入
                question = await session.prompt_async("You> ", style=prompt_style)

                # 检查退出命令
                if question.lower().strip() in ["exit", "quit", "q"]:
                    console.print("[bold yellow]再见！[/bold yellow]")
                    break

                if not question.strip():
                    continue

                # 检查全局中断标志
                if global_interrupt:
                    break

                # 上下文注入
                enhanced_query, context_info = await context_service.enhance_query(
                    question,
                    user_id="cli_chat_user"
                )

                # 显示上下文信息
                if context_service.should_display_context(context_info):
                    presenter.display_context_info(context_info)

                if thoughts:
                    # 流式展示思考过程
                    console.print()  # 空行
                    event_stream = agent_service.ask_stream(enhanced_query, session_id)
                    answer = await presenter.display_stream(event_stream)

                    # 显示答案（如果不是中断的）
                    if not presenter.is_interrupted():
                        presenter.display_answer(answer)

                    # 重置Presenter的中断标志
                    presenter._interrupted = False
                else:
                    # 普通模式（不显示思考过程）
                    with console.status("[bold green]思考中..."):
                        result = agent_service.ask_sync(enhanced_query, session_id)
                        answer = agent_service.extract_answer(result)

                        if not answer:
                            answer = "无法生成答案"

                    # 显示答案
                    console.print(f"\n[bold green]Agent:[/bold green] {answer}\n")

            except KeyboardInterrupt:
                # 处理Ctrl+C
                console.print("\n[bold yellow]⚠️  检测到 Ctrl+C，正在中断...[/bold yellow]")
                agent_service.interrupt()
                console.print("[dim]💡 提示: 再次按 Ctrl+C 可强制退出[/dim]")
                # 短暂延迟，避免重复触发
                await asyncio.sleep(0.5)
            except EOFError:
                console.print("\n[bold yellow]对话结束[/bold yellow]")
                break

    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()
    finally:
        # 恢复默认信号处理器
        if hasattr(signal, 'SIGINT'):
            try:
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            except:
                pass


if __name__ == "__main__":
    chat()

