# Docker快速入门指南

本文档帮助您快速使用Docker部署港股公告分析系统。

## 前置要求

- Docker >= 20.10
- docker-compose >= 2.0
- 至少4GB可用内存
- 至少10GB可用磁盘空间

## 快速开始

### 方式一：使用便捷脚本（推荐）

```bash
# 1. 启动服务（生产模式）
./docker/docker-up.sh

# 2. 启动开发环境（热重载模式）
./docker/docker-up.sh dev

# 3. 停止服务
./docker/docker-down.sh

# 4. 查看日志
./docker/docker-logs.sh web -f
```

### 方式二：使用Make命令

```bash
# 1. 查看所有命令
make -C docker help

# 2. 启动服务
make -C docker up

# 3. 启动开发环境
make -C docker up-dev

# 4. 停止服务
make -C docker down

# 5. 查看日志
make -C docker logs
```

### 方式三：使用docker-compose

```bash
# 1. 配置环境变量
cp .env.docker .env
# 编辑 .env 文件，设置 SILICONFLOW_API_KEY

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

## 第一次使用

### 1. 克隆项目
```bash
git clone <项目地址>
cd hkex-analysis
```

### 2. 配置环境变量
```bash
cp .env.docker .env
```

编辑 `.env` 文件，设置：
- `SILICONFLOW_API_KEY`: 硅基流动API密钥
- 其他配置使用默认值

### 3. 启动服务
```bash
# 使用便捷脚本
./docker/docker-up.sh
```

### 4. 等待服务就绪
启动过程大约需要2-3分钟，首次启动会下载Docker镜像。

### 5. 访问系统
- **Web管理界面**: http://localhost:8080
- **API文档**: http://localhost:8080/api/docs
- **API服务**: http://localhost:8000

## 开发环境

### 热重载模式

开发时建议使用开发环境，支持代码变更自动重启：

```bash
./docker/docker-up.sh dev
```

或：

```bash
make -C docker up-dev
```

### 进入容器调试

```bash
# 进入Web容器
docker-compose exec web bash

# 进入API容器
docker-compose exec api bash

# 进入ClickHouse容器
docker-compose exec clickhouse bash
```

### 查看实时日志

```bash
# 查看所有服务日志
./docker/docker-logs.sh all -f

# 查看Web服务日志
./docker/docker-logs.sh web -f

# 查看API服务日志
./docker/docker-logs.sh api -f

# 查看最近50行
./docker/docker-logs.sh api --tail 50
```

## 常用操作

### 查看服务状态
```bash
docker-compose ps
```

或使用Make：
```bash
make -C docker status
```

### 重启服务
```bash
docker-compose restart web
```

或重启所有服务：
```bash
make -C docker restart
```

### 重新构建镜像
```bash
docker-compose build --no-cache
make -C docker build
```

### 停止服务
```bash
docker-compose down
./docker/docker-down.sh
```

### 完全清理（包括数据）
```bash
./docker/docker-down.sh --full
make -C docker clean
```

## 访问数据库

### Web界面
http://localhost:8123

### 命令行
```bash
docker-compose exec clickhouse clickhouse-client
```

### 查看表
```sql
USE hkex_analysis;
SHOW TABLES;
```

## 数据持久化

数据存储在Docker卷中：
- `hkex-analysis_clickhouse_data`: ClickHouse数据
- `hkex-analysis_clickhouse_logs`: ClickHouse日志
- `hkex-analysis_app_uploads`: 应用上传文件

备份数据：
```bash
make -C docker backup
```

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web界面 | 8080 | 主界面、文件上传、任务管理等 |
| API服务 | 8000 | REST API、SSE流式接口 |
| ClickHouse HTTP | 8123 | ClickHouse Web界面、HTTP API |
| ClickHouse TCP | 9000 | ClickHouse TCP连接（客户端） |

## 故障排查

### 1. 服务无法启动

检查端口占用：
```bash
lsof -i :8080
lsof -i :8000
lsof -i :8123
```

### 2. 查看容器日志
```bash
docker-compose logs web
docker-compose logs api
docker-compose logs clickhouse
```

### 3. 检查环境变量
```bash
docker-compose exec web env | grep SILICONFLOW
```

### 4. 健康检查
```bash
make -C docker health
```

### 5. 进入容器调试
```bash
docker-compose exec web bash
# 然后手动执行命令调试
```

## 性能调优

### 调整资源限制

编辑 `docker-compose.yml`，添加：
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 数据库优化

进入ClickHouse调整配置：
```bash
docker-compose exec clickhouse bash
# 编辑配置文件：/etc/clickhouse-server/config.xml
```

## 安全建议

1. **不要暴露敏感端口到公网**
   - ClickHouse端口8123和9000仅用于本地访问
   - 生产环境使用反向代理（Nginx）

2. **定期备份数据**
   ```bash
   make -C docker backup
   ```

3. **更新镜像**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## 获取帮助

- 完整文档: `docker/README.md`
- 配置说明: `.env.docker`
- 项目文档: `README.md`

## 下一步

启动成功后：
1. 访问Web界面 http://localhost:8080
2. 上传PDF文档进行测试
3. 查看API文档 http://localhost:8080/api/docs
4. 使用CLI工具进行查询

享受使用！🎉
