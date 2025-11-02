#!/bin/bash

# Docker日志查看脚本

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

# 显示帮助
show_help() {
    echo "用法: $0 [服务名] [选项]"
    echo ""
    echo "服务名:"
    echo "  web        查看Web界面日志"
    echo "  api        查看API服务日志"
    echo "  clickhouse 查看ClickHouse日志"
    echo "  all        查看所有服务日志（默认）"
    echo ""
    echo "选项:"
    echo "  -f, --follow    跟踪日志输出"
    echo "  -t, --tail N    显示最后N行（默认100）"
    echo "  -h, --help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 web -f              # 跟踪Web服务日志"
    echo "  $0 api --tail 50       # 显示API服务最后50行"
    echo "  $0 clickhouse          # 查看ClickHouse日志"
    echo ""
}

# 查看服务状态
show_status() {
    info "服务状态:"
    docker-compose ps
    echo ""
}

# 查看日志
view_logs() {
    local service=$1
    local follow=$2
    local tail=$3

    local cmd="docker-compose logs"
    local options=""

    if [ "$follow" = "true" ]; then
        options="$options --follow"
    fi

    if [ -n "$tail" ]; then
        options="$options --tail=$tail"
    fi

    case $service in
        web)
            info "查看Web界面日志..."
            $cmd $options web
            ;;
        api)
            info "查看API服务日志..."
            $cmd $options api
            ;;
        clickhouse)
            info "查看ClickHouse日志..."
            $cmd $options clickhouse
            ;;
        all|"")
            info "查看所有服务日志..."
            $cmd $options
            ;;
        *)
            error "未知服务: $service"
            ;;
    esac
}

# 主函数
main() {
    local service="all"
    local follow="false"
    local tail="100"

    # 如果没有参数，显示帮助
    if [ $# -eq 0 ]; then
        show_status
        view_logs "" "$follow" "$tail"
        exit 0
    fi

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--follow)
                follow="true"
                shift
                ;;
            -t|--tail)
                tail="$2"
                shift 2
                ;;
            web|api|clickhouse|all)
                service="$1"
                shift
                ;;
            *)
                warning "未知参数: $1，使用 'all' 服务"
                shift
                ;;
        esac
    done

    echo ""
    echo "================================================"
    echo "  📋 港股公告分析系统 日志查看"
    echo "================================================"
    echo ""

    # 检查docker-compose是否运行
    if ! docker-compose ps &> /dev/null; then
        error "未找到运行中的服务，请先启动Docker服务"
    fi

    # 查看日志
    view_logs "$service" "$follow" "$tail"
}

# 执行主函数
main "$@"
