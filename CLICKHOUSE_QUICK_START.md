# ClickHouse 独立部署 - 快速开始

## 🚀 一键启动

```bash
# 方式1：使用启动脚本（推荐）
./docker/clickhouse-start.sh

# 方式2：手动启动
docker-compose -f docker-compose.clickhouse.yml up -d
```

## 📊 连接信息

**非默认端口配置**：
- **HTTP 端口**: `18168` (默认 8123)
- **TCP 端口**: `19168` (默认 9000)
- **数据库**: `hkex_analysis`

## 👤 用户凭证

| 用户名 | 密码 | 权限 | 用途 |
|--------|------|------|------|
| `default` | (无密码) | 管理员 | 开发调试 |
| `hkex_user` | `hkex_password_2025` | 读写 | **应用连接（推荐）** |
| `readonly_user` | `readonly_2025` | 只读 | 查询分析 |

## 🔧 快速测试

```bash
# 健康检查
curl http://localhost:18168/ping

# 查询版本
echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @-

# 查看数据库
echo 'SHOW DATABASES' | curl -s 'http://localhost:18168/' --data-binary @-

# 查看表
docker exec hkex-clickhouse clickhouse-client --query="USE hkex_analysis; SHOW TABLES"
```

## ⚙️ 应用配置

更新你的 `.env` 文件：

```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=18168
CLICKHOUSE_USER=hkex_user
CLICKHOUSE_PASSWORD=hkex_password_2025
CLICKHOUSE_DATABASE=hkex_analysis
```

## 📝 常用命令

```bash
# 查看日志
docker-compose -f docker-compose.clickhouse.yml logs -f

# 停止服务
docker-compose -f docker-compose.clickhouse.yml down

# 重启服务
docker-compose -f docker-compose.clickhouse.yml restart

# 进入容器
docker exec -it hkex-clickhouse bash

# CLI连接
docker exec -it hkex-clickhouse clickhouse-client
```

## 📚 详细文档

- **完整文档**: `docker/README.clickhouse.md`
- **配置文件**: `docker-compose.clickhouse.yml`
- **初始化脚本**: `docker/clickhouse/init/`

## ⚠️ 注意事项

1. **端口配置**: 使用非默认端口 18168/19168，避免冲突
2. **数据持久化**: 数据存储在 Docker 卷中，删除容器不会丢失数据
3. **安全提示**: 生产环境请修改默认密码
4. **资源限制**: 默认限制 2GB 内存，可在配置文件中调整

## 🔒 安全建议（生产环境）

```bash
# 1. 修改密码
# 编辑 docker/clickhouse/users.xml

# 2. 限制访问
# 配置防火墙规则，不要暴露到公网

# 3. 定期备份
docker run --rm \
  -v hkex_clickhouse_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/clickhouse-$(date +%Y%m%d).tar.gz -C /data .
```

## ❓ 故障排查

```bash
# 检查容器状态
docker ps -a | grep clickhouse

# 查看启动日志
docker-compose -f docker-compose.clickhouse.yml logs

# 测试连接
curl http://localhost:18168/ping

# 检查端口占用
lsof -i :18168
lsof -i :19168
```

## 📂 文件结构

```
hkex-analysis/
├── docker-compose.clickhouse.yml      # Docker Compose 配置
├── CLICKHOUSE_QUICK_START.md          # 本文档
└── docker/
    ├── clickhouse-start.sh            # 启动脚本
    ├── README.clickhouse.md           # 详细文档
    └── clickhouse/
        ├── config.xml                 # ClickHouse 配置
        ├── users.xml                  # 用户配置
        └── init/
            ├── 01-create-database.sql # 创建数据库
            └── 02-create-tables.sql   # 创建表结构
```

---

**开始使用**: `./docker/clickhouse-start.sh` 🎉

