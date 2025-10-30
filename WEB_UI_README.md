# 港股公告分析Web管理系统

基于FastAPI构建的现代化Web界面，用于管理港股公告PDF文档的上传、处理和数据管理。

## ✨ 功能特性

### 📤 文件上传
- ✅ 支持单文件和批量PDF上传
- ✅ 自动文档过滤（跳过月报表、年报等）
- ✅ 拖拽式上传界面
- ✅ 实时上传进度反馈

### 📋 任务管理
- ✅ 任务队列和状态跟踪
- ✅ 实时进度监控
- ✅ 任务重试和取消
- ✅ 任务历史记录

### 💾 数据管理
- ✅ 查看所有已处理文档
- ✅ 文档详情和章节内容查看
- ✅ 高级搜索和筛选
- ✅ 重复数据清理工具

### 📊 统计分析
- ✅ 实时统计仪表板
- ✅ 文档类型分布图表
- ✅ 热门公司排行榜
- ✅ 处理进度统计

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装项目依赖
pip install -e ".[dev]"

# 或使用便捷脚本
./install.sh
```

### 2. 配置环境

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，至少配置以下参数：
# - CLICKHOUSE_HOST
# - CLICKHOUSE_PORT
# - CLICKHOUSE_DATABASE
# - CLICKHOUSE_USER
# - CLICKHOUSE_PASSWORD
# - SILICONFLOW_API_KEY
```

### 3. 启动服务

```bash
# 方式一：使用便捷脚本（推荐）
./run_web.sh

# 方式二：指定端口
./run_web.sh 9000

# 方式三：手动启动
source .venv/bin/activate
uvicorn src.web.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. 访问系统

打开浏览器访问：http://localhost:8080

## 📱 界面预览

### 主页 - 系统概览
- 实时统计卡片
- 文档类型分布图
- 热门公司排行榜
- 最近任务列表

### 文件上传页
- 拖拽上传区域
- 批量文件选择
- 自动文档过滤
- 上传历史记录

### 任务管理页
- 任务状态统计
- 实时进度监控
- 任务筛选和搜索
- 任务操作（取消/重试/删除）

### 数据管理页
- 文档列表展示
- 高级搜索筛选
- 文档详情查看
- 章节内容浏览

### 统计分析页
- 多维度统计图表
- 数据可视化展示
- 处理进度分析

## 🔧 技术架构

### 后端
- **FastAPI**: 高性能异步Web框架
- **ClickHouse**: 文档和章节数据存储
- **Pydantic**: 数据验证和序列化

### 前端
- **Bootstrap 5**: 响应式UI框架
- **Chart.js**: 交互式图表库
- **jQuery**: DOM操作和AJAX
- **DataTables**: 高级表格组件

### 核心模块
```
src/web/
├── main.py              # FastAPI主应用
├── models/              # 数据模型
│   └── schemas.py
├── routes/              # 路由模块
│   ├── upload.py        # 文件上传
│   ├── tasks.py         # 任务管理
│   ├── data.py          # 数据管理
│   └── stats.py         # 统计分析
├── services/            # 业务服务
│   ├── task_service.py  # 任务服务
│   └── data_service.py  # 数据服务
├── static/              # 静态文件
│   ├── css/
│   ├── js/
│   └── uploads/         # 上传文件
└── templates/           # Jinja2模板
    ├── base.html
    ├── index.html       # 主页
    ├── upload.html      # 上传页
    ├── tasks.html       # 任务页
    ├── data.html        # 数据页
    └── stats.html       # 统计页
```

## 📊 API接口

### 任务管理
- `GET /tasks/` - 获取任务列表
- `GET /tasks/{task_id}` - 获取任务详情
- `POST /tasks/{task_id}/cancel` - 取消任务
- `POST /tasks/{task_id}/retry` - 重试任务
- `DELETE /tasks/{task_id}` - 删除任务
- `GET /tasks/stats/summary` - 任务统计

### 文件上传
- `POST /upload/` - 单文件上传
- `POST /upload/batch` - 批量文件上传

### 数据管理
- `GET /data/documents` - 获取文档列表
- `GET /data/documents/{doc_id}` - 获取文档详情
- `GET /data/documents/{doc_id}/sections` - 获取章节列表
- `GET /data/search` - 搜索文档
- `POST /data/cleanup/duplicates` - 清理重复数据
- `GET /data/cleanup/duplicates/preview` - 预览重复数据

### 统计分析
- `GET /stats/` - 获取统计数据
- `GET /stats/overview` - 获取概览统计

## 🎨 界面特性

### 响应式设计
- 支持桌面、平板、手机多端访问
- 自适应布局和组件

### 实时更新
- 任务进度实时刷新
- 统计数据定时更新
- WebSocket支持（可选）

### 用户体验
- 友好的加载提示
- 清晰的错误信息
- 优雅的动画效果
- 直观的操作反馈

## ⚙️ 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# ClickHouse数据库
CLICKHOUSE_HOST=1.14.239.79
CLICKHOUSE_PORT=8868
CLICKHOUSE_DATABASE=hkex_analysis
CLICKHOUSE_USER=your_username
CLICKHOUSE_PASSWORD=your_password

# Web服务
APP_HOST=0.0.0.0
APP_PORT=8080
```

### 自定义配置

修改 `src/web/main.py` 来自定义：
- 静态文件路径
- 模板目录
- 中间件配置
- CORS设置

## 🛠️ 开发指南

### 添加新页面

1. 在 `templates/` 创建HTML模板
2. 在 `main.py` 添加路由
3. 在 `routes/` 创建对应路由模块
4. 更新侧边栏导航

### 添加新API

1. 在 `routes/` 创建路由文件
2. 定义Pydantic模型
3. 实现业务逻辑
4. 注册路由到应用

### 自定义样式

修改 `templates/base.html` 中的 `<style>` 标签，或创建独立的CSS文件在 `static/css/` 目录。

## 📝 使用示例

### 示例1：上传单个文档

```bash
curl -X POST "http://localhost:8080/upload/" \
  -F "file=@document.pdf" \
  -F "stock_code=00328" \
  -F "document_type=rights"
```

### 示例2：查看任务状态

```bash
curl "http://localhost:8080/tasks/"
```

### 示例3：搜索文档

```bash
curl "http://localhost:8080/data/search?q=00328"
```

## 🔍 故障排除

### 问题1：端口被占用

```bash
# 查看端口占用
lsof -i :8080

# 使用其他端口
./run_web.sh 9000
```

### 问题2：数据库连接失败

检查 `.env` 文件中的ClickHouse配置：
```bash
# 测试连接
python -c "
from src.web.services.data_service import data_service
print('连接成功' if data_service.client else '连接失败')
"
```

### 问题3：静态文件404

确保目录存在：
```bash
mkdir -p src/web/static/uploads
```

## 📚 更多资源

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [Bootstrap 5文档](https://getbootstrap.com/docs/5.3/)
- [Chart.js文档](https://www.chartjs.org/docs/)
- [ClickHouse文档](https://clickhouse.com/docs/)

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题，请联系开发团队。

---

**版本**: 1.0.0
**更新**: 2025-10-29
**状态**: ✅ 生产就绪
