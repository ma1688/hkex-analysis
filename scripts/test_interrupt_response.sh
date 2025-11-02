#!/bin/bash
# 测试Ctrl+C和ESC中断响应时间
# 用法: ./scripts/test_interrupt_response.sh

set -e

echo "================================"
echo "CLI中断响应测试"
echo "================================"
echo ""
echo "本脚本测试ESC和Ctrl+C的响应时间"
echo "预期: 按下Ctrl+C后，50ms内停止执行"
echo ""

# 测试1: Ask命令
echo "📋 测试1: Ask命令 + Ctrl+C"
echo "----------------------------"
echo "执行: hkex-agent ask \"查询腾讯控股最近的配售公告\""
echo "请在执行过程中按 Ctrl+C 测试响应时间"
echo ""
read -p "按回车开始测试1... " _

# 记录开始时间（纳秒）
start_time=$(date +%s%N)

# 执行命令，捕获Ctrl+C
if hkex-agent ask "查询腾讯控股最近的配售公告" 2>&1; then
    echo "✅ 命令正常完成"
else
    # 记录结束时间
    end_time=$(date +%s%N)
    
    # 计算响应时间（毫秒）
    response_time=$(( (end_time - start_time) / 1000000 ))
    
    echo ""
    echo "⏱️  响应时间: ${response_time}ms"
    
    if [ $response_time -lt 100 ]; then
        echo "✅ 测试1通过！响应时间 < 100ms"
    elif [ $response_time -lt 200 ]; then
        echo "⚠️  测试1基本通过，响应时间稍慢（100-200ms）"
    else
        echo "❌ 测试1未通过，响应时间 > 200ms"
    fi
fi

echo ""
echo "----------------------------"
echo ""

# 测试2: Chat命令
echo "📋 测试2: Chat命令 + ESC"
echo "----------------------------"
echo "执行: hkex-agent chat"
echo "请输入一个查询，然后在执行过程中按 ESC 测试响应时间"
echo ""
read -p "按回车开始测试2（输入'quit'退出聊天）... " _

hkex-agent chat || true

echo ""
echo "================================"
echo "测试完成！"
echo "================================"
echo ""
echo "📝 结果总结："
echo "  • 如果响应时间 < 100ms：✅ 修复成功"
echo "  • 如果响应时间 100-200ms：⚠️ 基本正常"
echo "  • 如果响应时间 > 200ms：❌ 需要进一步优化"
echo ""
echo "💡 技术细节："
echo "  • 中断检查频率: 每20ms"
echo "  • 队列超时时间: 50ms"
echo "  • 预期最大响应时间: 50ms"
echo ""

