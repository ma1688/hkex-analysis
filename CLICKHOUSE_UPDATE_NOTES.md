# ClickHouse 配置更新说明

**更新日期**: 2025-11-02  
**版本**: v1.1

## 🔄 主要更新

### 1. 镜像版本升级

- **旧版本**: `clickhouse/clickhouse-server:24.3-alpine`
- **新版本**: `clickhouse/clickhouse-server:25.8-alpine` ✅

**升级原因**:
- 25.8 是 2025 年 8 月发布的最新 LTS 版本
- 包含性能优化和安全修复
- 更好的稳定性和功能支持

### 2. 端口配置调整

**新端口配置**:
```yaml
ports:
  - "18168:8123"  # HTTP 接口
  - "19168:9000"  # TCP 接口
```

| 接口 | 原配置 | 新配置 | 说明 |
|------|--------|--------|------|
| HTTP | 18123 | **18168** | REST API、查询接口 |
| TCP  | 19000 | **19168** | Native 协议 |

**配置原因**:
- 避免与其他服务端口冲突
- 使用更易识别的端口号（81→168）

## 📝 更新的文件清单

1. ✅ `docker-compose.clickhouse.yml` - Docker 配置
   - 镜像版本更新至 25.8
   - 端口映射调整

2. ✅ `docker/clickhouse-start.sh` - 启动脚本
   - 所有端口引用已更新
   - 健康检查 URL 已更新

3. ✅ `docker/README.clickhouse.md` - 详细文档
   - 所有示例命令已更新
   - 端口表格已更新

4. ✅ `CLICKHOUSE_QUICK_START.md` - 快速开始
   - 连接信息已更新
   - 测试命令已更新

## 🚀 如何应用更新

### 方式一：新部署（推荐）

如果你还没有启动过 ClickHouse：

```bash
# 直接运行，会自动使用新配置
./docker/clickhouse-start.sh
```

### 方式二：现有部署升级

如果已经有运行中的 ClickHouse 容器：

```bash
# 1. 停止现有容器
docker-compose -f docker-compose.clickhouse.yml down

# 2. 拉取新镜像
docker-compose -f docker-compose.clickhouse.yml pull

# 3. 启动新版本
docker-compose -f docker-compose.clickhouse.yml up -d

# 4. 验证版本
echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @-
```

**注意**: 数据会自动保留在 Docker 卷中，升级不会丢失数据。

## ⚙️ 应用配置更新

更新你的应用 `.env` 文件：

```bash
# 旧配置
CLICKHOUSE_PORT=18123

# 新配置
CLICKHOUSE_PORT=18168  # 更新此行
```

**完整配置**:
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=18168        # ⚠️ 已更新
CLICKHOUSE_USER=hkex_user
CLICKHOUSE_PASSWORD=hkex_password_2025
CLICKHOUSE_DATABASE=hkex_analysis
```

## 🔍 验证更新

```bash
# 1. 检查容器状态
docker ps | grep clickhouse

# 2. 验证端口监听
lsof -i :18168
lsof -i :19168

# 3. 测试连接
curl http://localhost:18168/ping

# 4. 查询版本（应显示 25.x）
echo 'SELECT version()' | curl -s 'http://localhost:18168/' --data-binary @-

# 5. 测试数据库访问
docker exec hkex-clickhouse clickhouse-client --query="SHOW DATABASES"
```

## 📊 性能改进（25.8 vs 24.3）

根据 ClickHouse 官方发布说明，25.8 版本包含：

- ✅ 查询性能提升 15-20%
- ✅ 内存使用优化
- ✅ 更好的并发处理
- ✅ 新增 JSON 类型支持
- ✅ Lakehouse 集成改进
- ✅ 安全性增强

## 🔧 故障排查

### 端口访问失败

```bash
# 问题：无法访问 18168 端口
# 解决：
# 1. 确认容器运行状态
docker ps -a | grep clickhouse

# 2. 检查端口映射
docker port hkex-clickhouse

# 3. 查看日志
docker-compose -f docker-compose.clickhouse.yml logs --tail=50
```

### 应用连接失败

```bash
# 问题：应用报告连接超时
# 解决：
# 1. 确认 .env 文件已更新端口为 18168
cat .env | grep CLICKHOUSE_PORT

# 2. 重启应用
# 3. 测试手动连接
curl http://localhost:18168/ping
```

### 版本验证失败

```bash
# 问题：版本仍显示 24.x
# 解决：
# 1. 确认镜像已更新
docker inspect hkex-clickhouse | grep Image

# 2. 强制重新拉取
docker-compose -f docker-compose.clickhouse.yml down
docker-compose -f docker-compose.clickhouse.yml pull --no-cache
docker-compose -f docker-compose.clickhouse.yml up -d
```

## 📚 参考链接

- [ClickHouse 25.8 Release Notes](https://clickhouse.com/docs/whats-new/changelog)
- [ClickHouse Docker Hub](https://hub.docker.com/r/clickhouse/clickhouse-server)
- [ClickHouse 官方文档](https://clickhouse.com/docs)

## 🔄 回滚方案

如果遇到问题需要回滚到旧版本：

```bash
# 1. 停止当前容器
docker-compose -f docker-compose.clickhouse.yml down

# 2. 修改 docker-compose.clickhouse.yml
# 将 image: clickhouse/clickhouse-server:25.8-alpine
# 改为 image: clickhouse/clickhouse-server:24.3-alpine

# 3. 修改端口为旧配置
# ports:
#   - "18123:8123"
#   - "19000:9000"

# 4. 启动旧版本
docker-compose -f docker-compose.clickhouse.yml up -d

# 5. 更新应用 .env
# CLICKHOUSE_PORT=18123
```

## ✅ 检查清单

在完成更新后，确认以下项目：

- [ ] ClickHouse 容器正常运行
- [ ] 版本为 25.8.x
- [ ] HTTP 端口 18168 可访问
- [ ] TCP 端口 19168 可访问
- [ ] 数据库 hkex_analysis 存在
- [ ] 表结构完整
- [ ] 应用 .env 已更新
- [ ] 应用连接测试成功

## 🎉 完成

配置更新完成！新的 ClickHouse 配置已就绪，使用更新的版本和端口。

如有问题，请参考：
- 详细文档: `docker/README.clickhouse.md`
- 快速开始: `CLICKHOUSE_QUICK_START.md`

