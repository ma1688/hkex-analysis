#!/bin/bash

# Docker启动脚本 - 快速部署港股分析系统

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 检查Docker和docker-compose
check_dependencies() {
    info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        error "Docker未安装，请先安装Docker"
    fi

    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose未安装，请先安装docker-compose"
    fi

    success "依赖检查通过"
}

# 初始化环境变量
init_env() {
    info "初始化环境变量..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.docker" ]; then
            warning "未找到.env文件，从.env.docker复制..."
            cp .env.docker .env
            warning "请编辑.env文件设置必要的API密钥和配置"
        else
            error "未找到.env或.env.docker文件"
        fi
    fi

    # 检查关键配置
    if ! grep -q "SILICONFLOW_API_KEY=" .env || grep -q "your_siliconflow_api_key_here" .env; then
        warning "请在.env文件中设置SILICONFLOW_API_KEY"
    fi

    success "环境变量初始化完成"
}

# 启动服务
start_services() {
    local mode=${1:-production}

    if [ "$mode" = "dev" ]; then
        info "启动开发环境（热重载模式）..."
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    else
        info "启动生产环境..."
        docker-compose up -d
    fi

    success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    info "等待服务就绪..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:8000/api/v1/health &> /dev/null; then
            success "API服务已就绪"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            warning "API服务启动可能需要更多时间"
            break
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
}

# 显示服务信息
show_info() {
    echo ""
    echo "================================================"
    success "  港股公告分析系统已启动"
    echo "================================================"
    echo ""
    echo "  🌐 Web管理界面: http://localhost:8080"
    echo "  📚 API文档:      http://localhost:8080/api/docs"
    echo "  🔌 API服务:      http://localhost:8000"
    echo "  ❤️  健康检查:    http://localhost:8000/api/v1/health"
    echo "  💾 ClickHouse:   http://localhost:8123"
    echo ""
    echo "  常用命令:"
    echo "    查看日志: docker-compose logs -f"
    echo "    停止服务: docker-compose down"
    echo "    重启服务: docker-compose restart"
    echo "================================================"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "================================================"
    echo "  🚀 港股公告分析系统 Docker 启动脚本"
    echo "================================================"
    echo ""

    # 检查参数
    local mode="production"
    if [ "$1" = "dev" ]; then
        mode="dev"
    fi

    # 执行步骤
    check_dependencies
    init_env
    start_services $mode
    wait_for_services
    show_info
}

# 执行主函数
main "$@"
