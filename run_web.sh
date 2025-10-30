#!/bin/bash

# 港股公告分析Web管理系统启动脚本
# 用法: ./run_web.sh [port]

set -e

# 默认端口
PORT=${1:-8080}

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f ".venv/bin/activate" ]; then
        echo "📦 激活虚拟环境..."
        source .venv/bin/activate
    else
        echo "❌ 错误: 未找到虚拟环境"
        echo "请先运行: pip install -e ."
        exit 1
    fi
fi

# 检查依赖
echo "🔍 检查依赖..."
python -c "import fastapi, clickhouse_connect, fitz" 2>/dev/null || {
    echo "❌ 缺少依赖，正在安装..."
    pip install -e ".[dev]"
}

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到 .env 文件"
    echo "请复制 .env.example 并配置相关参数"
    echo ""
    echo "示例:"
    echo "  cp .env.example .env"
    echo "  # 编辑 .env 文件，设置 CLICKHOUSE_* 和 SILICONFLOW_API_KEY"
    echo ""
fi

# 创建上传目录
mkdir -p src/web/static/uploads

echo ""
echo "================================================"
echo "  🚀 港股公告分析Web管理系统"
echo "================================================"
echo ""
echo "  📍 访问地址: http://localhost:${PORT}"
echo "  📚 API文档: http://localhost:${PORT}/api/docs"
echo "  🏠 首页:     http://localhost:${PORT}/"
echo ""
echo "  📤 文件上传: http://localhost:${PORT}/upload"
echo "  📋 任务管理: http://localhost:${PORT}/tasks"
echo "  💾 数据管理: http://localhost:${PORT}/data"
echo "  📊 统计分析: http://localhost:${PORT}/stats"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "================================================"
echo ""

# 启动服务
cd /Users/ericp/hkex-analysis
exec uvicorn src.web.main:app --host 0.0.0.0 --port ${PORT} --reload
