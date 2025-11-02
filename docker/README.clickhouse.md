# ClickHouse 独立部署指南

本文档说明如何使用 Docker 独立部署 ClickHouse 数据库（使用非默认端口）。

## 快速开始

### 1. 一键启动

```bash
# 使用启动脚本（推荐）
./docker/clickhouse-start.sh

# 或手动启动
docker-compose -f docker-compose.clickhouse.yml up -d
```

### 2. 访问数据库

启动成功后，可通过以下方式访问：

- **HTTP 端口**: `http://localhost:18168` (默认 8123)
- **TCP 端口**: `localhost:19168` (默认 9000)
- **数据库**: `hkex_analysis`

## 端口配置

为避免端口冲突，使用以下非默认端口：

| 协议 | 默认端口 | 自定义端口 | 说明 |
|------|---------|-----------|------|
| HTTP | 8123 | **18168** | REST API、Web UI |
| TCP  | 9000 | **19168** | Native 协议（CLI、JDBC） |

**容器内部仍使用默认端口**，仅宿主机映射到自定义端口。

## 用户凭证

系统预配置了三个用户：

| 用户名 | 密码 | 权限 | 用途 |
|--------|------|------|------|
| `default` | (无密码) | 管理员 | 开发调试 |
| `hkex_user` | `hkex_password_2025` | 读写 | 应用连接 |
| `readonly_user` | `readonly_2025` | 只读 | 查询分析 |

## 应用配置

更新应用的 `.env` 文件：

```bash
# ClickHouse 连接配置
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=18168
CLICKHOUSE_USER=hkex_user
CLICKHOUSE_PASSWORD=hkex_password_2025
CLICKHOUSE_DATABASE=hkex_analysis
```

**注意**: 如果应用和 ClickHouse 都在 Docker 容器中，使用服务名 `clickhouse` 和内部端口 `8123`。

## 数据库结构

系统会自动创建以下表：

1. **documents_v2**: 文档元信息表
2. **document_sections**: 文档章节切块表
3. **section_entities**: 章节实体提取表

详细结构参见 `docker/clickhouse/init/02-create-tables.sql`。

## 常用操作

### 查看日志

```bash
# 实时日志
docker-compose -f docker-compose.clickhouse.yml logs -f

# 最近100行
docker-compose -f docker-compose.clickhouse.yml logs --tail=100
```

### 连接数据库

#### 方式1: Docker CLI

```bash
# 进入容器
docker exec -it hkex-clickhouse bash

# 使用 clickhouse-client
docker exec -it hkex-clickhouse clickhouse-client

# 直接执行查询
docker exec hkex-clickhouse clickhouse-client --query="SHOW DATABASES"
docker exec hkex-clickhouse clickhouse-client --query="USE hkex_analysis; SHOW TABLES"
```

#### 方式2: HTTP API

```bash
# 健康检查
curl http://localhost:18168/ping

# 查询版本
echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @-

# 查询数据库
echo 'SHOW DATABASES' | curl -s 'http://localhost:18168/' --data-binary @-

# 查询表
echo 'USE hkex_analysis; SHOW TABLES' | curl -s 'http://localhost:18168/' --data-binary @-

# 指定用户认证
curl -u hkex_user:hkex_password_2025 \
  'http://localhost:18168/?query=SELECT+count()+FROM+documents_v2'
```

#### 方式3: Python 客户端

```python
from clickhouse_driver import Client

client = Client(
    host='localhost',
    port=19168,  # TCP端口
    user='hkex_user',
    password='hkex_password_2025',
    database='hkex_analysis'
)

# 执行查询
result = client.execute('SHOW TABLES')
print(result)
```

### 管理服务

```bash
# 启动
docker-compose -f docker-compose.clickhouse.yml up -d

# 停止
docker-compose -f docker-compose.clickhouse.yml down

# 重启
docker-compose -f docker-compose.clickhouse.yml restart

# 停止并删除数据
docker-compose -f docker-compose.clickhouse.yml down -v
```

### 数据备份

```bash
# 备份数据卷
docker run --rm \
  -v hkex_clickhouse_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/clickhouse-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# 恢复数据
docker run --rm \
  -v hkex_clickhouse_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/clickhouse-YYYYMMDD-HHMMSS.tar.gz -C /data
```

### 数据导入导出

```bash
# 导出CSV
docker exec hkex-clickhouse clickhouse-client \
  --query="SELECT * FROM hkex_analysis.documents_v2 FORMAT CSV" > documents.csv

# 导入CSV
cat documents.csv | docker exec -i hkex-clickhouse clickhouse-client \
  --query="INSERT INTO hkex_analysis.documents_v2 FORMAT CSV"

# 导出JSON
docker exec hkex-clickhouse clickhouse-client \
  --query="SELECT * FROM hkex_analysis.documents_v2 FORMAT JSONEachRow" > documents.json
```

## 性能配置

### 资源限制

配置文件中已设置资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### 调优建议

1. **内存配置** (`docker/clickhouse/config.xml`):
   - `max_server_memory_usage`: 服务器最大内存（默认2GB）
   - `max_memory_usage`: 单个查询最大内存（默认2GB）

2. **并发配置**:
   - `max_connections`: 最大连接数（默认4096）
   - `max_concurrent_queries`: 最大并发查询（默认100）

3. **查询限制**:
   - `max_execution_time`: 最大执行时间（默认300秒）
   - `max_result_rows`: 最大返回行数（默认1000000）

## 故障排查

### 服务无法启动

```bash
# 1. 检查端口占用
lsof -i :18168
lsof -i :19168

# 2. 查看容器状态
docker-compose -f docker-compose.clickhouse.yml ps

# 3. 查看日志
docker-compose -f docker-compose.clickhouse.yml logs

# 4. 检查配置文件
docker exec hkex-clickhouse cat /etc/clickhouse-server/config.d/custom.xml
```

### 连接失败

```bash
# 1. 测试健康检查
curl http://localhost:18168/ping

# 2. 检查容器网络
docker network inspect hkex-network

# 3. 测试内部连接（容器内部）
docker exec hkex-clickhouse wget -qO- http://localhost:8123/ping
```

### 数据库未初始化

```bash
# 1. 查看数据库列表
docker exec hkex-clickhouse clickhouse-client --query="SHOW DATABASES"

# 2. 手动执行初始化脚本
docker exec -i hkex-clickhouse clickhouse-client < docker/clickhouse/init/01-create-database.sql
docker exec -i hkex-clickhouse clickhouse-client < docker/clickhouse/init/02-create-tables.sql

# 3. 检查初始化日志
docker-compose -f docker-compose.clickhouse.yml logs | grep -i "create"
```

### 权限问题

```bash
# 1. 测试用户认证
echo 'SELECT currentUser()' | curl -u hkex_user:hkex_password_2025 \
  -s 'http://localhost:18168/' --data-binary @-

# 2. 查看用户权限
docker exec hkex-clickhouse clickhouse-client \
  --query="SHOW GRANTS FOR hkex_user"

# 3. 重置用户配置
docker-compose -f docker-compose.clickhouse.yml restart
```

## 安全建议

### 生产环境

1. **修改默认密码**:
   - 编辑 `docker/clickhouse/users.xml`
   - 使用强密码替换默认密码

2. **限制网络访问**:
   - 不要将端口暴露到公网
   - 使用防火墙规则限制访问
   - 配置 IP 白名单

3. **启用 SSL**:
   ```xml
   <!-- config.xml -->
   <https_port>18443</https_port>
   <openSSL>
       <server>
           <certificateFile>/path/to/cert.pem</certificateFile>
           <privateKeyFile>/path/to/key.pem</privateKeyFile>
       </server>
   </openSSL>
   ```

4. **定期备份**:
   - 设置自动备份任务
   - 测试恢复流程

### 日志管理

```bash
# 设置日志轮转
docker exec hkex-clickhouse bash -c "
cat > /etc/logrotate.d/clickhouse <<EOF
/var/log/clickhouse-server/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
"
```

## 监控

### 系统指标

```sql
-- 查看表大小
SELECT 
    database,
    table,
    formatReadableSize(sum(bytes)) AS size
FROM system.parts
WHERE database = 'hkex_analysis'
GROUP BY database, table;

-- 查看查询统计
SELECT 
    query_duration_ms,
    read_rows,
    result_rows,
    query
FROM system.query_log
WHERE type = 'QueryFinish'
ORDER BY event_time DESC
LIMIT 10;

-- 查看连接数
SELECT count() FROM system.processes;

-- 查看内存使用
SELECT 
    formatReadableSize(total_memory_tracker) AS memory_used
FROM system.metrics
WHERE metric = 'MemoryTracking';
```

### 健康检查

```bash
# 脚本方式
#!/bin/bash
if curl -sf http://localhost:18168/ping > /dev/null; then
    echo "✓ ClickHouse is healthy"
else
    echo "✗ ClickHouse is down"
    exit 1
fi
```

## 升级

### 版本升级

```bash
# 1. 备份数据
./docker/clickhouse-start.sh backup

# 2. 修改 docker-compose.clickhouse.yml 中的版本号
# image: clickhouse/clickhouse-server:25.8-alpine

# 3. 重新构建
docker-compose -f docker-compose.clickhouse.yml pull
docker-compose -f docker-compose.clickhouse.yml up -d

# 4. 验证
docker exec hkex-clickhouse clickhouse-client --query="SELECT version()"
```

## 参考资源

- [ClickHouse 官方文档](https://clickhouse.com/docs)
- [ClickHouse Docker Hub](https://hub.docker.com/r/clickhouse/clickhouse-server)
- [ClickHouse GitHub](https://github.com/ClickHouse/ClickHouse)

## 常见问题

**Q: 为什么使用非默认端口？**
A: 避免与系统中其他服务（如本地 ClickHouse）冲突，提高部署灵活性。

**Q: 如何修改端口配置？**
A: 编辑 `docker-compose.clickhouse.yml` 中的 `ports` 配置，格式为 `宿主机端口:容器端口`。

**Q: 数据存储在哪里？**
A: 数据存储在 Docker 卷 `hkex_clickhouse_data` 中，即使删除容器也不会丢失。

**Q: 如何重置数据库？**
A: 执行 `docker-compose -f docker-compose.clickhouse.yml down -v` 删除数据卷，然后重新启动。

**Q: 可以在生产环境使用吗？**
A: 可以，但需要：
   1. 修改默认密码
   2. 配置备份策略
   3. 启用监控告警
   4. 根据负载调整资源限制

