"""CLI命令 - 使用Typer实现"""
import asyncio
import logging
import uuid

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agent.context_injector import inject_query_context
from src.agent.document_agent import get_document_agent
from src.config.settings import get_settings
from src.tools.loader import load_all_tools
from src.utils.text_cleaner import clean_text

# 创建CLI应用
app = typer.Typer(help="HK Stock Analysis Agent - 港股公告智能问答系统")
console = Console()

# 配置日志
logging.basicConfig(level=logging.WARNING)  # CLI模式下减少日志输出


async def stream_agent_with_display(agent, question: str, config: dict, console: Console, detailed: bool = False):
    """
    流式执行Agent并实时动态展示思考过程
    
    Args:
        agent: Agent实例
        question: 用户问题
        config: Agent配置
        console: Rich Console实例
        detailed: 是否显示详细内容
        
    Returns:
        最终答案
    """
    import time

    final_answer = None
    step_count = 0
    last_update = time.time()

    # 创建输入（清理问题中的无效字符）
    clean_question = clean_text(question)
    input_data = {"messages": [("user", clean_question)]}

    # 流式执行 - 实时展示
    try:
        event_count = 0
        thinking_start = time.time()  # 记录开始时间

        from rich.spinner import Spinner
        from rich import box
        import sys

        # 使用Rich的spinner来显示动态进度
        mode_hint = "详细模式" if detailed else "简洁模式"

        # 初始显示
        elapsed_time = 0
        with console.status(f"[bold green]⏳ Agent思考中... [cyan]{elapsed_time:.1f}s[/cyan] [dim]({mode_hint})[/dim]",
                            spinner="dots") as status:

            # 创建后台时间更新任务
            update_interval = 0.5  # 每0.5秒更新一次时间
            should_stop_time_update = False

            async def update_time_display():
                """后台任务：定期更新时间显示"""
                nonlocal should_stop_time_update
                while not should_stop_time_update:
                    await asyncio.sleep(update_interval)
                    current_time = time.time()
                    elapsed = current_time - thinking_start
                    status.update(
                        f"[bold green]⏳ Agent思考中... [cyan]{elapsed:.1f}s[/cyan] [dim]({mode_hint})[/dim]",
                        spinner="dots"
                    )

            # 启动时间更新任务
            time_update_task = asyncio.create_task(update_time_display())

            try:
                # 流式处理每个事件
                async for event in agent.astream(input_data, config):
                    event_count += 1
                    current_time = time.time()
                    elapsed_time = current_time - thinking_start

                    # 提取事件信息（移到循环内部）
                    for key, value in event.items():
                        step_count += 1
                        elapsed = f"{current_time - last_update:.1f}s"
                        last_update = current_time

                        # 计算总思考时间
                        total_elapsed = current_time - thinking_start

                        # 在spinner中显示当前操作（包含总时间）
                        node_symbol = "🔄" if key == "tools" else "🧠"

                        # Spinner中只显示简要信息
                        spinner_text = f"[bold green]{node_symbol} 步骤{step_count}: {key}[/bold green] [cyan]总计{total_elapsed:.1f}s[/cyan]"
                        status.update(spinner_text, spinner="dots")

                        # 停止spinner，打印详细内容，然后继续
                        status.stop()
                        console.print(
                            f"[dim cyan]{node_symbol} 步骤{step_count}: {key}[/dim cyan] [cyan]总计{total_elapsed:.1f}s[/cyan] [dim](+{elapsed})[/dim]")

                        # 打印消息详情
                        if isinstance(value, dict) and "messages" in value:
                            messages = value.get("messages", [])
                            if messages:
                                last_message = messages[-1]

                                # 检查是否是AI消息
                                if hasattr(last_message, 'content'):
                                    content = clean_text(last_message.content)

                                    # 如果包含工具调用
                                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                                        for tool_call in last_message.tool_calls:
                                            tool_name = tool_call.get('name', 'unknown')
                                            console.print(f"[yellow]  🔧 {tool_name}[/yellow]")

                                            # 详细模式：显示参数
                                            if detailed:
                                                tool_args = tool_call.get('args', {})
                                                if tool_args:
                                                    import json
                                                    args_str = json.dumps(tool_args, ensure_ascii=False, indent=2)
                                                    # 限制参数显示长度
                                                    if len(args_str) > 200:
                                                        args_str = args_str[:200] + "..."
                                                    console.print(f"[dim]  📋 {args_str}[/dim]")
                                    else:
                                        # 显示思考内容
                                        if content and len(content) > 5:
                                            if detailed:
                                                # 详细模式：多行显示
                                                preview = content[:200].replace('\n', ' ')
                                                console.print(f"[green]  💭 {preview}...[/green]")
                                            else:
                                                # 简洁模式：一行显示
                                                preview = content[:50].replace('\n', ' ')
                                                console.print(f"[green]  💭 {preview}...[/green]")

                                # 检查是否是工具消息
                                elif hasattr(last_message, 'name'):
                                    tool_name = last_message.name if hasattr(last_message, 'name') else 'tool'
                                    content = clean_text(last_message.content) if hasattr(last_message,
                                                                                          'content') else ''

                                    if detailed:
                                        preview = content[:200].replace('\n', ' ')
                                    else:
                                        preview = content[:50].replace('\n', ' ')
                                    console.print(f"[blue]  ✅ {tool_name}: {preview}...[/blue]")

                        # 重新启动spinner
                        status.start()

                        # 添加微小延迟
                        await asyncio.sleep(0.02)

            finally:
                # 停止时间更新任务
                should_stop_time_update = True
                time_update_task.cancel()
                try:
                    await time_update_task
                except asyncio.CancelledError:
                    pass

        # 获取最终答案
        if event:
            for key, value in event.items():
                if isinstance(value, dict) and "messages" in value:
                    messages = value.get("messages", [])
                    if messages:
                        final_answer = messages[-1].content if hasattr(messages[-1], 'content') else "无法生成答案"

        final_answer = clean_text(final_answer) if final_answer else "无法生成答案"

        # 计算总耗时
        total_time = time.time() - thinking_start

        # 显示完成标记（包含总时间）
        console.print(f"[dim]✨ 完成！共 {step_count} 个节点，总耗时 [cyan]{total_time:.1f}s[/cyan][/dim]")

        return final_answer

    except Exception as e:
        import traceback
        console.print(f"[bold red]流式执行错误: {e}[/bold red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return f"执行出错: {e}"


def run_agent_stream(agent, question: str, config: dict, console: Console, detailed: bool = False):
    """运行流式Agent（同步包装）- 优化版避免卡顿"""
    import asyncio

    # 创建新的事件循环（避免冲突）
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 运行异步函数
        result = loop.run_until_complete(
            stream_agent_with_display(agent, question, config, console, detailed)
        )
        return result
    finally:
        # 清理事件循环
        try:
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # 让任务完成取消（设置短超时）
            if pending:
                loop.run_until_complete(
                    asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=0.1
                    )
                )
        except:
            pass  # 忽略清理错误
        finally:
            loop.close()


@app.command()
def ask(
        question: str = typer.Argument(..., help="要询问的问题"),
        session: str = typer.Option(None, "--session", "-s", help="会话ID（可选）"),
        show_thoughts: bool = typer.Option(True, "--thoughts/--no-thoughts", help="是否显示思考过程"),
        detailed: bool = typer.Option(False, "--detailed", "-d", help="详细模式（显示完整内容）")
):
    """
    单次问答
    
    示例：
        hkex-agent ask "查询腾讯控股最近的配售公告"
        hkex-agent ask "查询00700配售数据" --no-thoughts
        hkex-agent ask "问题" -d  # 详细模式
    """
    try:
        # 上下文注入 - Layer 2
        enhanced_query, context_info = inject_query_context(question, "cli_user")

        if context_info.get("injected"):
            console.print(f"[dim]📍 上下文已注入 (置信度: {context_info.get('confidence', 0):.2f})[/dim]")
            if show_thoughts:
                console.print(f"[dim]💡 注入: {context_info.get('injected_context', [])[:1]}[/dim]\n")

        # 获取并显示模型信息
        from src.agent.document_agent import load_agent_config
        from src.config.settings import get_settings
        settings = get_settings()
        agent_config = load_agent_config("document")
        # 优先使用 Settings 中的模型（与 document_agent.py 逻辑一致）
        model_name = agent_config.get("model") or settings.siliconflow_fast_model
        temperature = agent_config.get("temperature", 0.1)

        # 获取Agent
        agent = get_document_agent()

        # 会话ID
        session_id = session or str(uuid.uuid4())

        # 配置
        config = {
            "configurable": {
                "thread_id": session_id
            },
            "recursion_limit": 50  # 增加递归限制（默认25）
        }

        console.print(f"\n[bold cyan]问题:[/bold cyan] {question}")
        console.print(f"[dim]📍 模型: [cyan]{model_name}[/cyan] (温度: {temperature})[/dim]\n")

        if show_thoughts:
            # 实时流式展示思考过程（使用增强后的查询）
            answer = run_agent_stream(agent, enhanced_query, config, console, detailed)

            # 显示答案
            console.print()  # 空行
            console.print(Panel(
                answer,
                title="[bold green]Agent回答[/bold green]",
                border_style="green"
            ))
        else:
            # 普通模式（使用增强后的查询）
            with console.status("[bold green]思考中..."):
                result = agent.invoke(
                    {"messages": [("user", enhanced_query)]},
                    config
                )

                # 提取答案
                messages = result.get("messages", [])
                answer = messages[-1].content if messages else "无法生成答案"
                # 清理可能的无效字符
                answer = clean_text(answer)

            # 显示结果
            console.print("[bold green]回答:[/bold green]")
            console.print(answer)

        console.print(f"\n[dim]会话ID: {session_id}[/dim]")

    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def chat(
        show_thoughts: bool = typer.Option(True, "--thoughts/--no-thoughts", help="是否显示思考过程"),
        detailed: bool = typer.Option(False, "--detailed", "-d", help="详细模式（显示完整内容）")
):
    """
    交互式对话
    
    示例：
        hkex-agent chat                  # 显示思考过程（默认）
        hkex-agent chat --no-thoughts    # 不显示思考过程
        hkex-agent chat -d               # 详细模式（显示完整内容）
    """
    # 获取并显示模型信息
    from src.agent.document_agent import load_agent_config
    from src.config.settings import get_settings
    settings = get_settings()
    agent_config = load_agent_config("document")
    # 优先使用 Settings 中的模型（与 document_agent.py 逻辑一致）
    model_name = agent_config.get("model") or settings.siliconflow_fast_model
    temperature = agent_config.get("temperature", 0.1)

    session_id = str(uuid.uuid4())
    console.print(f"[bold green]开始对话[/bold green] (会话ID: {session_id})")
    console.print(f"[dim]📍 模型: [cyan]{model_name}[/cyan] (温度: {temperature})[/dim]")
    console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]")

    if show_thoughts:
        mode_desc = "详细模式" if detailed else "简洁模式"
        console.print(f"[dim]💡 提示: 思考过程展示已启用 ({mode_desc})[/dim]\n")
    else:
        console.print("[dim]💡 提示: 使用 --thoughts 可查看思考过程[/dim]\n")

    try:
        agent = get_document_agent()
        config = {
            "configurable": {
                "thread_id": session_id
            },
            "recursion_limit": 50  # 增加递归限制（默认25）
        }

        while True:
            # 获取用户输入
            question = console.input("\n[bold cyan]You:[/bold cyan] ")

            if question.lower() in ["exit", "quit", "q"]:
                console.print("[bold yellow]再见！[/bold yellow]")
                break

            if not question.strip():
                continue

            # 上下文注入 - Layer 2
            enhanced_query, context_info = inject_query_context(question, "cli_chat_user")

            if context_info.get("injected"):
                console.print(f"[dim]📍 上下文已注入 (置信度: {context_info.get('confidence', 0):.2f})[/dim]")

            # 调用Agent（流式或普通）
            if show_thoughts:
                # 实时流式展示思考过程
                console.print()  # 空行

                answer = run_agent_stream(agent, enhanced_query, config, console, detailed)

                # 显示答案
                console.print()  # 空行
                console.print(Panel(
                    answer,
                    title="[bold green]Agent回答[/bold green]",
                    border_style="green"
                ))
            else:
                # 普通模式（不显示思考过程）
                with console.status("[bold green]思考中..."):
                    result = agent.invoke(
                        {"messages": [("user", enhanced_query)]},
                        config
                    )

                    messages = result.get("messages", [])
                    answer = messages[-1].content if messages else "无法生成答案"
                    # 清理可能的无效字符
                    answer = clean_text(answer)

                # 显示答案
                console.print(f"\n[bold green]Agent:[/bold green] {answer}\n")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]对话中断[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("tools-list")
def tools_list():
    """
    列出所有可用工具
    
    示例：
        hkex-agent tools-list
    """
    try:
        tools = load_all_tools()

        # 创建表格
        table = Table(title="可用工具列表")
        table.add_column("工具名", style="cyan", no_wrap=True)
        table.add_column("描述", style="magenta")

        for tool in tools:
            table.add_row(tool.name, tool.description)

        console.print(table)
        console.print(f"\n[dim]共 {len(tools)} 个工具[/dim]")

    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("config")
def show_config():
    """
    显示当前配置
    
    示例：
        hkex-agent config
    """
    try:
        settings = get_settings()

        table = Table(title="当前配置")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")

        table.add_row("环境", settings.app_env)
        table.add_row("端口", str(settings.app_port))
        table.add_row("日志级别", settings.app_log_level)
        table.add_row("ClickHouse Host", settings.clickhouse_host)
        table.add_row("ClickHouse DB", settings.clickhouse_database)
        table.add_row("快速模型", settings.siliconflow_fast_model)
        table.add_row("强模型", settings.siliconflow_strong_model)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def version():
    """显示版本信息"""
    console.print("[bold green]HK Stock Analysis Agent[/bold green]")
    console.print("Version: [cyan]0.1.0[/cyan]")
    console.print("基于LangGraph的港股公告智能问答系统")


if __name__ == "__main__":
    app()
