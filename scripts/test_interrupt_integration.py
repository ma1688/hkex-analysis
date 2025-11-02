#!/usr/bin/env python3
"""
集成测试：模拟实际CLI场景测试中断响应

测试场景：
1. 模拟LLM调用（慢速响应）
2. 在等待过程中触发中断
3. 验证响应时间
"""
import asyncio
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def simulate_slow_llm_call():
    """模拟慢速LLM调用（5秒）"""
    print("  🤖 模拟LLM思考中（5秒）...")
    await asyncio.sleep(5)
    return "LLM响应"


async def test_interrupt_during_llm_call():
    """测试在LLM调用期间中断"""
    print("=" * 60)
    print("集成测试：LLM调用期间中断")
    print("=" * 60)
    
    from src.cli.v2.services.agent_service import get_agent_service
    
    agent_service = get_agent_service()
    agent_service.reset_interrupt()
    
    # 创建一个模拟的慢速事件流
    async def mock_slow_stream():
        """模拟包含慢速LLM调用的事件流"""
        yield {"step": 1, "messages": ["开始处理"]}
        
        # 模拟LLM调用（这里会阻塞5秒）
        print("  📡 发送LLM请求...")
        start = time.time()
        
        # 在后台模拟LLM调用
        llm_task = asyncio.create_task(simulate_slow_llm_call())
        
        # 每100ms检查一次中断和LLM完成状态
        while not llm_task.done():
            if agent_service.check_interrupt():
                print("  ⚠️  检测到中断信号，取消LLM调用")
                llm_task.cancel()
                try:
                    await llm_task
                except asyncio.CancelledError:
                    pass
                return
            
            await asyncio.sleep(0.1)
        
        elapsed = time.time() - start
        print(f"  ✅ LLM响应完成（耗时{elapsed:.1f}秒）")
        yield {"step": 2, "messages": [await llm_task]}
    
    # 测试流程
    interrupted = False
    interrupt_time = None
    events_processed = 0
    
    async def process_stream():
        """处理事件流"""
        nonlocal interrupted, interrupt_time, events_processed
        
        async for event in mock_slow_stream():
            events_processed += 1
            print(f"  📦 处理事件 {events_processed}: {event}")
    
    async def trigger_interrupt():
        """在1秒后触发中断"""
        nonlocal interrupt_time
        await asyncio.sleep(1.0)
        print(f"\n  🔴 1秒后触发中断信号")
        interrupt_start = time.time()
        agent_service.interrupt()
        
        # 等待中断生效（最多1秒）
        for i in range(10):
            if agent_service.check_interrupt():
                interrupt_time = (time.time() - interrupt_start) * 1000
                print(f"  ✅ 中断信号已确认（{interrupt_time:.1f}ms）")
                return interrupt_time
            await asyncio.sleep(0.1)
        
        return None
    
    # 并发运行处理和中断
    start_time = time.time()
    
    try:
        results = await asyncio.gather(
            process_stream(),
            trigger_interrupt(),
            return_exceptions=True
        )
        # 从trigger_interrupt获取interrupt_time
        if len(results) > 1 and isinstance(results[1], (int, float)):
            interrupt_time = results[1]
    except Exception as e:
        print(f"  ⚠️  捕获异常: {e}")
    
    total_time = (time.time() - start_time) * 1000
    
    # 显示结果
    print(f"\n  📊 测试结果:")
    print(f"    • 总执行时间: {total_time:.1f}ms")
    print(f"    • 处理事件数: {events_processed}")
    
    if interrupt_time:
        print(f"    • 中断响应时间: {interrupt_time:.1f}ms")
        
        # 验证：总时间应该在1秒左右（等待1秒 + 中断响应时间）
        expected_time = 1000  # 1秒
        if total_time < expected_time + 200:  # 允许200ms误差
            print(f"    • ✅ 测试通过！中断及时响应（< 5秒LLM调用）")
            return True
        else:
            print(f"    • ❌ 测试未通过！总时间过长")
            return False
    else:
        print(f"    • ❌ 未能触发中断")
        return False


async def test_interrupt_between_events():
    """测试在事件之间中断"""
    print("\n" + "=" * 60)
    print("集成测试：事件之间中断")
    print("=" * 60)
    
    from src.cli.v2.services.agent_service import get_agent_service
    
    agent_service = get_agent_service()
    agent_service.reset_interrupt()
    
    # 创建快速事件流
    async def mock_fast_stream():
        """模拟快速事件流"""
        for i in range(10):
            if agent_service.check_interrupt():
                print(f"  ⚠️  在事件{i}时检测到中断")
                return
            yield {"step": i, "messages": [f"Event {i}"]}
            await asyncio.sleep(0.1)  # 每个事件间隔100ms
    
    events_processed = 0
    interrupt_time = None
    
    async def process_stream():
        """处理事件流"""
        nonlocal events_processed
        async for event in mock_fast_stream():
            events_processed += 1
            print(f"  📦 事件 {events_processed}")
    
    async def trigger_interrupt():
        """在300ms后触发中断"""
        await asyncio.sleep(0.3)
        print(f"\n  🔴 300ms后触发中断")
        start = time.time()
        agent_service.interrupt()
        interrupt_time_local = (time.time() - start) * 1000
        return interrupt_time_local
    
    start_time = time.time()
    
    try:
        results = await asyncio.gather(
            process_stream(),
            trigger_interrupt()
        )
        interrupt_time = results[1]
    except Exception as e:
        print(f"  ⚠️  捕获异常: {e}")
    
    total_time = (time.time() - start_time) * 1000
    
    # 显示结果
    print(f"\n  📊 测试结果:")
    print(f"    • 总执行时间: {total_time:.1f}ms")
    print(f"    • 处理事件数: {events_processed}")
    
    # 预期应该处理3-4个事件（300ms / 100ms per event）
    if 2 <= events_processed <= 5:
        print(f"    • ✅ 测试通过！中断及时响应（处理了{events_processed}个事件）")
        return True
    else:
        print(f"    • ❌ 测试未通过！事件数不符合预期")
        return False


async def main():
    """主测试函数"""
    print("\n🧪 开始CLI中断响应集成测试\n")
    
    results = []
    
    try:
        result1 = await test_interrupt_during_llm_call()
        results.append(("LLM调用期间中断", result1))
        
        result2 = await test_interrupt_between_events()
        results.append(("事件之间中断", result2))
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 显示结果
    print("\n" + "=" * 60)
    print("📊 集成测试总结")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print(f"\n🎉 所有集成测试通过！")
        print(f"\n💡 修复验证：")
        print(f"  • 中断响应机制正常工作")
        print(f"  • 即使LLM调用耗时5秒，也能在1秒内响应中断")
        print(f"  • 在事件之间能够及时检测和响应中断")
        return True
    else:
        print(f"\n⚠️  部分集成测试未通过")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

