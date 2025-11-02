# Docker部署指南

本文档说明如何使用Docker部署港股公告分析系统。

## 快速开始

### 1. 配置环境变量

复制环境变量示例文件：
```bash
cp .env.docker .env
```

编辑 `.env` 文件，设置必要的配置：
- `SILICONFLOW_API_KEY`: 硅基流动API密钥
- 其他配置根据需要调整

### 2. 启动所有服务

使用docker-compose启动完整系统（包括ClickHouse）：

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f web
```

### 3. 访问系统

启动成功后，可通过以下地址访问：

- **Web管理界面**: http://localhost:8080
- **API文档**: http://localhost:8080/api/docs
- **API服务**: http://localhost:8000
- **API健康检查**: http://localhost:8000/api/v1/health
- **ClickHouse Web**: http://localhost:8123

## 开发环境

### 使用热重载

对于开发调试，可以使用开发环境配置：

```bash
# 启动开发环境（支持热重载）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看开发环境日志
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f web-dev
```

开发模式下，代码修改会自动重启服务。

## 服务说明

### Web界面 (hkex-web)
- 端口: 8080
- 功能: Web管理界面、文件上传、任务管理、数据查看、统计分析
- 健康检查: `/api/v1/health`

### API服务 (hkex-api)
- 端口: 8000
- 功能: REST API接口、同步和流式查询
- 健康检查: `/api/v1/health`

### ClickHouse数据库 (clickhouse)
- HTTP端口: 8123
- TCP端口: 9000
- 数据目录: 持久化存储
- 默认数据库: hkex_analysis

## 常用命令

### 构建镜像
```bash
# 重新构建镜像
docker-compose build

# 强制重新构建
docker-compose build --no-cache
```

### 启动/停止服务
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f api
docker-compose logs -f clickhouse

# 查看最近100行日志
docker-compose logs --tail=100 web
```

### 进入容器
```bash
# 进入Web容器
docker-compose exec web bash

# 进入ClickHouse容器
docker-compose exec clickhouse bash

# 使用clickhouse-client
docker-compose exec clickhouse clickhouse-client
```

### 数据库操作
```bash
# 查看ClickHouse日志
docker-compose logs clickhouse

# 连接ClickHouse
docker-compose exec clickhouse clickhouse-client

# 查看数据库列表
docker-compose exec clickhouse clickhouse-client --query="SHOW DATABASES"

# 查看表列表
docker-compose exec clickhouse clickhouse-client --query="USE hkex_analysis; SHOW TABLES"
```

## 持久化数据

以下数据会被持久化存储：

1. **ClickHouse数据**: `clickhouse_data` 卷
2. **ClickHouse日志**: `clickhouse_logs` 卷
3. **应用上传文件**: `app_uploads` 卷

如需完全清理数据：
```bash
docker-compose down -v
```

## 网络配置

所有服务都在 `hkex-network` 网络中：
- 服务间通过服务名通信（如 `clickhouse:8123`）
- 外部访问通过宿主机端口映射

## 故障排查

### 服务无法启动

1. 检查端口占用：
```bash
lsof -i :8080
lsof -i :8000
lsof -i :8123
```

2. 查看容器日志：
```bash
docker-compose logs web
docker-compose logs api
docker-compose logs clickhouse
```

3. 检查环境变量：
```bash
docker-compose exec web env | grep SILICONFLOW
```

### ClickHouse连接失败

1. 确认ClickHouse服务健康：
```bash
docker-compose ps clickhouse
curl http://localhost:8123
```

2. 检查网络连接：
```bash
docker-compose exec web nc -zv clickhouse 8123
```

3. 查看ClickHouse日志：
```bash
docker-compose logs clickhouse
```

### API调用失败

1. 确认服务状态：
```bash
curl http://localhost:8000/api/v1/health
```

2. 检查API密钥配置：
```bash
docker-compose exec api env | grep SILICONFLOW_API_KEY
```

## 生产环境部署

### 安全建议

1. **使用环境变量文件**:
   - 不要将`.env`文件提交到代码库
   - 使用`.env.docker`作为模板

2. **限制端口访问**:
   - 如无必要，不要暴露ClickHouse端口8123到公网
   - 使用反向代理（如Nginx）处理外部访问

3. **定期备份**:
   ```bash
   # 备份ClickHouse数据
   docker run --rm -v hkex-analysis_clickhouse_data:/data \
     -v $(pwd)/backup:/backup \
     alpine tar czf /backup/clickhouse-$(date +%Y%m%d).tar.gz -C /data .
   ```

4. **监控**:
   - 使用健康检查端点监控服务状态
   - 设置日志轮转防止日志文件过大

### 性能优化

1. **调整资源限制**:
   ```yaml
   # 在docker-compose.yml中添加
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

2. **数据库优化**:
   - 调整ClickHouse配置
   - 定期清理历史数据

## 更新部署

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build

# 3. 重启服务
docker-compose up -d

# 4. 清理旧镜像
docker image prune
```
