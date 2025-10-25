# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用开发命令

### 安装与配置
```bash
# 安装项目依赖
pip install -e ".[dev]"

# 配置环境变量（必须）
cp .env.example .env
# 编辑 .env 文件，至少设置 SILICONFLOW_API_KEY
```

### 启动服务
```bash
# 启动API服务
uvicorn src.api.main:app --reload --port 8000

# 使用CLI（推荐方式）
source .venv/bin/activate  # 或使用完整路径
hkex-agent chat            # 交互式对话
hkex-agent ask "查询问题"  # 单次问答
```

### 测试命令
```bash
# 运行所有测试
pytest

# 代码格式化
black src/ tests/
ruff check src/ tests/
```

## 核心架构概览

这是一个基于 **LangGraph** 的港股公告智能问答系统，采用分层多Agent架构：

### 主要组件
- **Supervisor**: LangGraph状态机，负责任务规划、路由和协调
- **Document Agent**: ReAct模式的公告分析Agent
- **工具系统**: 10+个工具，支持数据库查询、文档检索、内容合成
- **LLM管理器**: 支持硅基流动和OpenAI，自动主备切换

### 关键目录结构
```
src/
├── agent/           # Agent模块（supervisor, document_agent, planner等）
├── api/             # FastAPI REST API
├── cli/             # CLI命令行工具
├── tools/           # 工具集（structured_data, document_retrieval等）
├── llm/             # LLM多提供商管理
├── config/          # 配置管理
└── utils/           # 工具模块（ClickHouse客户端等）
```

### 配置文件
- `config/agents.yaml`: Agent行为、模型选择、工具列表配置
- `config/tools.yaml`: 工具执行超时、重试、并发配置
- `.env`: API密钥、数据库连接等环境变量

### 数据库表结构
系统使用ClickHouse存储港股数据：
- `pdf_documents`: 公告文档元信息
- `pdf_chunks`: 公告切块内容
- `*_data`: IPO、配售、供股、合股等结构化数据表

### 核心工具列表
- 数据查询: `query_ipo_data`, `query_placing_data`, `query_rights_data`, `query_consolidation_data`
- 文档检索: `search_documents`, `retrieve_chunks`
- 内容分析: `synthesize_chunks`, `extract_key_info`, `compare_data`

## 开发注意事项

### 配置驱动设计
- 所有配置从YAML文件和环境变量读取，零硬编码
- 修改Agent行为或工具列表只需编辑配置文件
- 新工具会自动加载（支持`src/tools/custom/`目录）

### Agent扩展点
- 新Agent类型可在`config/agents.yaml`的`sub_agents`中配置
- 支持planned、market、financial、news等多种Agent类型
- Supervisor会自动路由到enabled的Agent

### 测试和调试
- CLI默认显示Agent思考过程，便于调试
- 使用`--no-thoughts`参数可隐藏思考过程
- API提供健康检查端点：`GET /api/v1/health`

### 常见修改场景
1. **添加新工具**: 在`src/tools/custom/`创建工具文件，配置会自动加载
2. **调整Agent行为**: 修改`config/agents.yaml`中的相关参数
3. **更换LLM模型**: 修改配置文件中的model名称，支持多提供商切换