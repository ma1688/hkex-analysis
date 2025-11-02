#!/bin/bash

# Docker停止脚本 - 停止港股分析系统

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

# 停止服务
stop_services() {
    local remove_volumes=${1:-false}

    info "停止所有服务..."

    if [ "$remove_volumes" = "true" ]; then
        warning "将删除所有数据卷（不可恢复！）"
        read -p "确认删除数据卷？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            success "所有服务和数据卷已删除"
        else
            info "取消删除操作"
        fi
    else
        docker-compose down
        success "所有服务已停止"
    fi
}

# 清理资源
cleanup() {
    info "清理未使用的Docker资源..."

    # 删除未使用的镜像
    docker image prune -f

    # 删除未使用的网络
    docker network prune -f

    # 删除未使用的卷
    docker volume prune -f

    success "清理完成"
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示帮助信息"
    echo "  -v, --volumes   停止服务并删除所有数据卷"
    echo "  -c, --cleanup   停止服务并清理Docker资源"
    echo "  --full          完全清理（停止+删除卷+清理资源）"
    echo ""
}

# 主函数
main() {
    local action="stop"

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--volumes)
                action="volumes"
                shift
                ;;
            -c|--cleanup)
                action="cleanup"
                shift
                ;;
            --full)
                action="full"
                shift
                ;;
            *)
                error "未知参数: $1"
                ;;
        esac
    done

    echo ""
    echo "================================================"
    echo "  🛑 港股公告分析系统 Docker 停止脚本"
    echo "================================================"
    echo ""

    # 执行相应操作
    case $action in
        stop)
            stop_services
            ;;
        volumes)
            stop_services true
            ;;
        cleanup)
            stop_services
            cleanup
            ;;
        full)
            stop_services true
            cleanup
            ;;
    esac

    echo ""
    success "操作完成"
    echo ""
}

# 执行主函数
main "$@"
