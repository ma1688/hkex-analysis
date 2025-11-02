# Docker管理Makefile
# 提供便捷的Docker操作命令

.PHONY: help build up down logs clean status shell web api clickhouse

# 默认目标
help:
	@echo "港股公告分析系统 - Docker管理命令"
	@echo ""
	@echo "常用命令:"
	@echo "  make up          - 启动所有服务（生产模式）"
	@echo "  make up-dev      - 启动开发环境（热重载）"
	@echo "  make down        - 停止所有服务"
	@echo "  make down-full   - 停止并删除数据卷"
	@echo "  make logs        - 查看所有日志"
	@echo "  make logs-web    - 查看Web界面日志"
	@echo "  make logs-api    - 查看API服务日志"
	@echo "  make logs-db     - 查看ClickHouse日志"
	@echo "  make status      - 查看服务状态"
	@echo "  make clean       - 清理Docker资源"
	@echo "  make shell-web   - 进入Web容器"
	@echo "  make shell-api   - 进入API容器"
	@echo "  make shell-db    - 进入ClickHouse容器"
	@echo "  make build       - 重新构建镜像"
	@echo "  make restart     - 重启所有服务"
	@echo ""
	@echo "开发命令:"
	@echo "  make up-dev      - 开发模式（代码变更自动重启）"
	@echo ""
	@echo "维护命令:"
	@echo "  make backup      - 备份数据库"
	@echo "  make restore     - 恢复数据库"
	@echo ""

# 启动服务（生产模式）
up:
	@echo "启动生产环境..."
	docker-compose up -d

# 启动服务（开发模式）
up-dev:
	@echo "启动开发环境（热重载模式）..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 停止服务
down:
	@echo "停止所有服务..."
	docker-compose down

# 停止服务并删除数据卷
down-full:
	@echo "停止所有服务并删除数据卷..."
	docker-compose down -v

# 查看日志
logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

logs-api:
	docker-compose logs -f api

logs-db:
	docker-compose logs -f clickhouse

# 查看服务状态
status:
	docker-compose ps

# 清理Docker资源
clean:
	@echo "清理未使用的Docker资源..."
	docker-compose down -v
	docker image prune -f
	docker network prune -f
	docker volume prune -f

# 重新构建镜像
build:
	@echo "重新构建镜像..."
	docker-compose build --no-cache

# 重启服务
restart:
	@echo "重启所有服务..."
	docker-compose restart

# 进入容器
shell-web:
	docker-compose exec web bash

shell-api:
	docker-compose exec api bash

shell-db:
	docker-compose exec clickhouse bash

# 数据库操作
db-shell:
	docker-compose exec clickhouse clickhouse-client

db-logs:
	docker-compose logs -f clickhouse

# 健康检查
health:
	@echo "检查服务健康状态..."
	@curl -sf http://localhost:8000/api/v1/health > /dev/null && echo "✅ API服务正常" || echo "❌ API服务异常"
	@curl -sf http://localhost:8080/api/v1/health > /dev/null && echo "✅ Web服务正常" || echo "❌ Web服务异常"
	@curl -sf http://localhost:8123 > /dev/null && echo "✅ ClickHouse正常" || echo "❌ ClickHouse异常"

# 备份数据库（需要配置备份路径）
backup:
	@echo "备份数据库..."
	@mkdir -p ./backups
	@docker run --rm -v hkex-analysis_clickhouse_data:/data \
		-v $(PWD)/backups:/backup \
		alpine tar czf /backup/clickhouse-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "备份完成"

# 恢复数据库（谨慎使用）
restore:
	@echo "⚠️ 恢复数据库将覆盖现有数据！"
	@echo "请确保已停止所有服务，然后手动执行恢复操作"
	@echo "备份文件位于 ./backups 目录"

# 安装依赖并启动（首次使用）
init: build up
	@echo "等待服务启动..."
	@sleep 10
	@make health

# 完整清理（谨慎使用）
distclean: down-full clean
	@echo "完全清理完成"
