"""键盘监听工具 - 支持ESC和Ctrl+C中断"""
import asyncio
import os
import sys
import signal
from typing import Optional


class KeyboardInterruptHandler:
    """键盘中断处理器"""

    def __init__(self):
        self._interrupted = False
        self._esc_pressed = False
        self._original_handler = None

    def is_interrupted(self) -> bool:
        """检查是否被中断"""
        return self._interrupted or self._esc_pressed

    def is_esc_pressed(self) -> bool:
        """检查是否按了ESC"""
        return self._esc_pressed

    def reset(self):
        """重置中断标志"""
        self._interrupted = False
        self._esc_pressed = False

    def interrupt(self):
        """手动中断"""
        self._interrupted = True

    def esc_interrupt(self):
        """ESC中断"""
        self._esc_pressed = True

    def install_signal_handlers(self):
        """安装信号处理器"""
        if hasattr(signal, 'SIGINT'):
            try:
                self._original_handler = signal.signal(signal.SIGINT, self._signal_handler)
            except (ValueError, OSError):
                pass

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self._interrupted = True

    def restore_signal_handlers(self):
        """恢复信号处理器"""
        if hasattr(signal, 'SIGINT') and self._original_handler is not None:
            try:
                signal.signal(signal.SIGINT, self._original_handler)
            except:
                pass


async def listen_for_escape(handler: KeyboardInterruptHandler, stop_event: asyncio.Event):
    """
    监听ESC键（需要终端支持）

    注意：ESC键监听需要终端配置，在某些环境下可能无法工作

    Args:
        handler: 中断处理器
        stop_event: 停止事件
    """
    if os.name != 'posix':
        # 非POSIX系统不支持标准输入监听
        return

    try:
        # 保存终端设置
        import termios
        import tty
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        # 设置非阻塞模式
        tty.setraw(fd)

        while not stop_event.is_set():
            # 检查是否有输入
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)

                # 检查ESC键（ASCII 27）
                if ord(ch) == 27:
                    # 尝试读取后续字符（可能是方向键等）
                    ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.1)[0] else ''
                    ch3 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.1)[0] else ''

                    # 如果是单独的ESC（不是方向键等），则触发中断
                    if not ch2 and not ch3:
                        handler.esc_interrupt()
                        break

    except Exception as e:
        # 如果无法设置终端模式，ESC键监听可能不可用
        # 这是正常的，在某些环境下可能会失败
        pass
    finally:
        try:
            # 恢复终端设置
            import termios
            import tty

            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except:
            pass


def is_escape_listening_supported() -> bool:
    """
    检查当前环境是否支持ESC键监听

    Returns:
        True如果支持，False否则
    """
    if os.name != 'posix':
        return False

    try:
        import termios
        import tty
        import select
        return True
    except ImportError:
        return False
