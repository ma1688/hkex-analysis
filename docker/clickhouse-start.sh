#!/bin/bash

# ============================================================================
# ClickHouse 独立启动脚本
# 用于快速部署 ClickHouse 数据库（使用非默认端口）
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

section() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}================================${NC}"
}

# 检查Docker
check_docker() {
    info "检查 Docker..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装，请先安装 Docker"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker 未运行，请启动 Docker"
    fi
    
    success "Docker 检查通过"
}

# 检查端口占用
check_ports() {
    info "检查端口占用..."
    
    local ports=(18168 19168)
    local port_occupied=false
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            warning "端口 $port 已被占用"
            port_occupied=true
        fi
    done
    
    if [ "$port_occupied" = true ]; then
        read -p "是否继续？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "用户取消操作"
        fi
    else
        success "端口检查通过"
    fi
}

# 启动服务
start_services() {
    info "启动 ClickHouse 服务..."
    
    docker-compose -f docker-compose.clickhouse.yml up -d
    
    success "服务启动命令已执行"
}

# 等待服务就绪
wait_for_services() {
    info "等待 ClickHouse 就绪..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:18168/ping &> /dev/null; then
            success "ClickHouse 已就绪"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            warning "ClickHouse 启动超时，请检查日志"
            return 1
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
}

# 验证数据库
verify_database() {
    info "验证数据库..."
    
    # 检查数据库是否创建成功
    local db_check=$(docker exec hkex-clickhouse clickhouse-client --query="SHOW DATABASES" 2>/dev/null | grep -c "hkex_analysis" || true)
    
    if [ "$db_check" -eq 1 ]; then
        success "数据库 hkex_analysis 创建成功"
        
        # 显示表列表
        info "数据库表列表："
        docker exec hkex-clickhouse clickhouse-client --query="USE hkex_analysis; SHOW TABLES" 2>/dev/null || true
    else
        warning "数据库可能未正确创建，请检查初始化脚本"
    fi
}

# 显示服务信息
show_info() {
    section "ClickHouse 服务已启动"
    echo ""
    echo "  📊 连接信息："
    echo "     HTTP端口:  http://localhost:18168"
    echo "     TCP端口:   localhost:19168"
    echo "     数据库:    hkex_analysis"
    echo ""
    echo "  👤 用户凭证："
    echo "     管理员:    default / (无密码)"
    echo "     应用用户:  hkex_user / hkex_password_2025"
    echo "     只读用户:  readonly_user / readonly_2025"
    echo ""
    echo "  🔧 常用命令："
    echo "     查看日志:    docker-compose -f docker-compose.clickhouse.yml logs -f"
    echo "     停止服务:    docker-compose -f docker-compose.clickhouse.yml down"
    echo "     重启服务:    docker-compose -f docker-compose.clickhouse.yml restart"
    echo "     进入容器:    docker exec -it hkex-clickhouse bash"
    echo "     CLI连接:     docker exec -it hkex-clickhouse clickhouse-client"
    echo ""
    echo "  📝 测试连接："
    echo "     curl http://localhost:18168/ping"
    echo "     echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @-"
    echo ""
    echo "  🔗 应用配置（更新 .env 文件）："
    echo "     CLICKHOUSE_HOST=localhost"
    echo "     CLICKHOUSE_PORT=18168"
    echo "     CLICKHOUSE_USER=hkex_user"
    echo "     CLICKHOUSE_PASSWORD=hkex_password_2025"
    echo "     CLICKHOUSE_DATABASE=hkex_analysis"
    echo ""
}

# 测试连接
test_connection() {
    section "测试连接"
    
    info "测试 HTTP 端口..."
    if curl -sf http://localhost:18168/ping &> /dev/null; then
        success "HTTP 端口 18168 连接正常"
    else
        warning "HTTP 端口 18168 连接失败"
    fi
    
    info "测试 ClickHouse 版本..."
    local version=$(echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @- 2>/dev/null)
    if [ -n "$version" ]; then
        success "ClickHouse 版本: $version"
    else
        warning "无法获取版本信息"
    fi
}

# 主函数
main() {
    section "🚀 ClickHouse Docker 启动脚本"
    echo "  使用非默认端口："
    echo "  - HTTP: 18168 (默认 8123)"
    echo "  - TCP:  19168 (默认 9000)"
    
    # 执行步骤
    check_docker
    check_ports
    start_services
    wait_for_services
    verify_database
    test_connection
    show_info
    
    section "✅ 部署完成"
}

# 执行主函数
main "$@"

