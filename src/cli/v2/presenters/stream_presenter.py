"""流式展示器 - 使用Rich实现优雅的流式输出"""
import asyncio
import time
from typing import Dict, Any, Optional
import logging

from rich.console import Console
from rich.panel import Panel
from src.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


class StreamPresenter:
    """
    流式输出展示器
    
    职责：
    - 实时展示Agent思考过程
    - 管理进度指示器和时间更新
    - 格式化工具调用和消息内容
    """
    
    def __init__(self, console: Optional[Console] = None, detailed: bool = False):
        """
        初始化展示器
        
        Args:
            console: Rich Console实例（可选）
            detailed: 是否显示详细内容
        """
        self.console = console or Console()
        self.detailed = detailed
        self.step_count = 0
        self.start_time = time.time()
        
    async def display_stream(
        self,
        event_stream,
        show_spinner: bool = True
    ) -> Optional[str]:
        """
        展示流式事件
        
        Args:
            event_stream: 异步事件迭代器
            show_spinner: 是否显示进度指示器
            
        Returns:
            最终答案文本
        """
        final_answer = None
        mode_hint = "详细模式" if self.detailed else "简洁模式"
        
        if show_spinner:
            with self.console.status(
                f"[bold green]⏳ Agent思考中... [cyan]0.0s[/cyan] [dim]({mode_hint})[/dim]",
                spinner="dots"
            ) as status:
                # 启动时间更新任务
                stop_time_update = False
                
                async def update_time():
                    """后台更新时间显示"""
                    nonlocal stop_time_update
                    while not stop_time_update:
                        await asyncio.sleep(0.5)
                        elapsed = time.time() - self.start_time
                        status.update(
                            f"[bold green]⏳ Agent思考中... [cyan]{elapsed:.1f}s[/cyan] [dim]({mode_hint})[/dim]"
                        )
                
                time_task = asyncio.create_task(update_time())
                
                try:
                    async for event in event_stream:
                        final_answer = await self._process_event(event, status)
                finally:
                    stop_time_update = True
                    time_task.cancel()
                    try:
                        await time_task
                    except asyncio.CancelledError:
                        pass
        else:
            # 不显示spinner，直接处理事件
            async for event in event_stream:
                final_answer = await self._process_event(event, None)
        
        # 显示完成信息
        total_time = time.time() - self.start_time
        self.console.print(
            f"[dim]✨ 完成！共 {self.step_count} 个节点，总耗时 [cyan]{total_time:.1f}s[/cyan][/dim]"
        )
        
        return clean_text(final_answer) if final_answer else "无法生成答案"
    
    async def _process_event(
        self,
        event: Dict[str, Any],
        status: Optional[Any]
    ) -> Optional[str]:
        """
        处理单个事件
        
        Args:
            event: 事件字典
            status: Rich status对象（可选）
            
        Returns:
            如果是最终答案则返回，否则返回None
        """
        final_answer = None
        
        for key, value in event.items():
            self.step_count += 1
            elapsed = time.time() - self.start_time
            
            # 更新spinner
            node_symbol = "🔄" if key == "tools" else "🧠"
            
            if status:
                status.update(
                    f"[bold green]{node_symbol} 步骤{self.step_count}: {key}[/bold green] [cyan]总计{elapsed:.1f}s[/cyan]",
                    spinner="dots"
                )
                status.stop()
            
            # 打印步骤信息
            self.console.print(
                f"[dim cyan]{node_symbol} 步骤{self.step_count}: {key}[/dim cyan] [cyan]总计{elapsed:.1f}s[/cyan]"
            )
            
            # 处理消息
            if isinstance(value, dict) and "messages" in value:
                messages = value.get("messages", [])
                if messages:
                    final_answer = await self._display_message(messages[-1])
            
            if status:
                status.start()
            
            await asyncio.sleep(0.02)  # 微小延迟，避免刷新过快
        
        return final_answer
    
    async def _display_message(self, message) -> Optional[str]:
        """
        显示单条消息
        
        Args:
            message: 消息对象
            
        Returns:
            如果是AI消息则返回内容，否则返回None
        """
        # AI消息（包含思考或工具调用）
        if hasattr(message, 'content'):
            content = clean_text(message.content)
            
            # 检查工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    self.console.print(f"[yellow]  🔧 {tool_name}[/yellow]")
                    
                    # 详细模式：显示参数
                    if self.detailed:
                        tool_args = tool_call.get('args', {})
                        if tool_args:
                            import json
                            args_str = json.dumps(tool_args, ensure_ascii=False, indent=2)
                            if len(args_str) > 200:
                                args_str = args_str[:200] + "..."
                            self.console.print(f"[dim]  📋 {args_str}[/dim]")
            else:
                # 显示思考内容
                if content and len(content) > 5:
                    max_len = 200 if self.detailed else 50
                    preview = content[:max_len].replace('\n', ' ')
                    self.console.print(f"[green]  💭 {preview}...[/green]")
            
            return content
        
        # 工具消息
        elif hasattr(message, 'name'):
            tool_name = message.name if hasattr(message, 'name') else 'tool'
            content = clean_text(message.content) if hasattr(message, 'content') else ''
            max_len = 200 if self.detailed else 50
            preview = content[:max_len].replace('\n', ' ')
            self.console.print(f"[blue]  ✅ {tool_name}: {preview}...[/blue]")
        
        return None
    
    def display_answer(self, answer: str, title: str = "Agent回答"):
        """
        显示最终答案
        
        Args:
            answer: 答案文本
            title: 面板标题
        """
        self.console.print()  # 空行
        self.console.print(Panel(
            answer,
            title=f"[bold green]{title}[/bold green]",
            border_style="green"
        ))
    
    def display_context_info(self, context_info: Dict):
        """
        显示上下文信息
        
        Args:
            context_info: 上下文信息字典
        """
        if context_info.get("injected"):
            confidence = context_info.get("confidence", 0)
            self.console.print(
                f"[dim]📍 上下文已注入 (置信度: {confidence:.2f})[/dim]"
            )
            if self.detailed:
                injected = context_info.get("injected_context", [])
                if injected:
                    self.console.print(f"[dim]💡 注入: {injected[:1]}[/dim]\n")

