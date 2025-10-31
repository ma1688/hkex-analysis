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

### 启动服务（推荐）

```bash
# 方式一：使用便捷脚本（最快）
./run_cli.sh chat                         # 交互式对话
./run_cli.sh ask "查询问题"                # 单次问答
./run_api.sh                              # 启动API服务

# 方式二：手动启动
source .venv/bin/activate
hkex-agent chat                         # 交互式对话（带历史记录）
hkex-agent ask "查询问题"                # 单次问答
hkex-agent ask "问题" --no-thoughts     # 不显示思考过程
hkex-agent ask "问题" -d                # 详细模式
uvicorn src.api.main:app --reload --port 8000

# 旧CLI（如需回退）
hkex-agent-old chat
```

### 测试与调试

```bash
# 运行所有测试
pytest

# 代码格式化
black src/ tests/
ruff check src/ tests/

# 单个测试文件
pytest tests/test_document_agent.py -v

# API健康检查
curl http://localhost:8000/api/v1/health
```

## 核心架构概览

这是一个基于 **LangGraph** 的港股公告智能问答系统，采用分层多Agent架构（Phase 1-3已实现）：

### 主要组件

- **Supervisor**: LangGraph状态机，协调整个工作流（`src/agent/supervisor.py`）
- **Planner**: 任务规划Agent（`src/agent/planner.py`）
- **Document Agent**: ReAct模式的公告分析Agent（`src/agent/document_agent.py`）
- **Reflector**: 结果验证Agent（`src/agent/reflector.py`）
- **Memory Manager**: 记忆管理（`src/agent/memory.py`）
- **Context Manager**: 上下文管理（`src/agent/context.py`）
- **Context Injector**: 上下文注入器（`src/agent/context_injector.py`）
- **Data Enhancer**: 数据增强（`src/agent/data_enhancer.py`）
- **Web管理界面**: FastAPI构建的现代化界面，支持文件上传、任务管理、数据管理、统计分析（`src/web/`）
- **工具系统**: 20+个工具，支持数据库查询、文档检索、内容合成、时间感知、数据增强
- **LLM管理器**: 支持硅基流动和OpenAI，自动主备切换（`src/llm/manager.py`）

### LangGraph工作流程

```
用户查询
   ↓
build_context (构建上下文)
   ↓
plan (生成执行计划)
   ↓
route (路由决策)
   ↓
┌──────────────────────┐
│ execute_document     │ ← Document Agent执行
│ (Document Agent)     │
└──────────┬───────────┘
           ↓
reflect (反思评估)
   ↓
┌──────────────────────┐
│ continue? → route    │ ← 循环优化
│ finalize → finalize  │ ← 输出结果
└──────────────────────┘
           ↓
finalize (最终答案)
```

### 关键目录结构

```
src/
├── agent/               # Agent模块
│   ├── supervisor.py      # 主协调器（LangGraph状态机）
│   ├── document_agent.py  # 文档分析Agent
│   ├── planner.py         # 任务规划Agent
│   ├── reflector.py       # 结果验证Agent
│   ├── memory.py          # 记忆管理
│   ├── context.py         # 上下文管理
│   ├── data_enhancer.py   # 数据增强
│   └── state.py           # 状态定义
├── api/                 # FastAPI REST API
│   ├── main.py            # 应用入口
│   └── schemas.py         # API数据模型
├── cli/                 # CLI命令行工具
│   ├── v2/                # CLI v2 - 全新架构（推荐）
│   │   ├── app.py            # 主入口（Click组）
│   │   ├── commands/         # 命令模块
│   │   │   ├── ask.py         # ask命令
│   │   │   ├── chat.py        # chat命令
│   │   │   ├── tools.py       # tools命令
│   │   │   └── config.py      # config命令
│   │   ├── services/          # 服务层
│   │   │   ├── agent_service.py   # Agent服务
│   │   │   └── context_service.py # 上下文服务
│   │   └── presenters/        # 展示层
│   │       ├── stream_presenter.py # 流式展示
│   │       └── table_presenter.py  # 表格展示
│   └── commands.py        # CLI v1 - 旧实现（已备份）
├── web/                  # Web管理界面（FastAPI）
│   ├── main.py             # Web应用入口
│   ├── routes/             # 路由模块
│   │   ├── upload.py         # 文件上传
│   │   ├── tasks.py          # 任务管理
│   │   ├── data.py           # 数据管理
│   │   └── stats.py          # 统计信息
│   ├── services/           # 服务层
│   ├── models/             # 数据模型
│   ├── templates/          # HTML模板
│   └── static/             # 静态资源
├── tools/               # 工具集
│   ├── structured_data.py    # 数据库查询工具
│   ├── document_retrieval.py # 文档检索工具
│   ├── synthesis.py          # 内容合成工具
│   ├── time_utils.py         # 时间感知工具
│   ├── data_enhancement.py   # 数据增强工具
│   └── custom/               # 自定义工具目录
├── llm/                 # LLM管理
│   └── manager.py           # 多LLM管理器
├── config/              # 配置管理
│   └── settings.py           # Settings类（Pydantic）
└── utils/               # 工具模块
    ├── clickhouse.py         # ClickHouse客户端
    └── text_cleaner.py       # 文本清洗
```

### 核心文件索引

| 功能模块 | 关键文件 | 说明 |
|---------|---------|------|
| **入口文件** | `src/cli/v2/app.py` | CLI v2主入口（hkex-agent命令） |
| | `src/api/main.py` | API服务入口 |
| | `src/web/main.py` | Web管理界面入口 |
| **Agent核心** | `src/agent/supervisor.py` | LangGraph状态机 |
| | `src/agent/document_agent.py` | 文档分析Agent |
| | `src/agent/state.py` | 状态定义 |
| | `src/agent/context_injector.py` | 上下文注入器 |
| **配置** | `src/config/settings.py` | 配置管理 |
| | `config/agents.yaml` | Agent配置 |
| | `config/prompts/prompts.yaml` | 提示词配置 |
| **工具** | `src/tools/loader.py` | 工具加载器 |
| | `src/tools/structured_data.py` | 数据查询工具 |
| | `src/tools/data_enhancement.py` | 数据增强工具（Layer 3） |

### 配置文件

- `config/agents.yaml`: Agent行为、模型选择、工具列表配置
- `config/tools.yaml`: 工具执行超时、重试、并发配置
- `config/prompts/prompts.yaml`: **系统提示词配置（新增）**
- `.env`: API密钥、数据库连接等环境变量

### 数据库表结构

系统使用ClickHouse存储港股数据：

- `pdf_documents`: 公告文档元信息
- `pdf_chunks`: 公告切块内容
- `*_data`: IPO、配售、供股、合股等结构化数据表

### 核心工具列表

| 工具类型 | 工具名 | 功能说明 | 主要参数 |
|---------|--------|----------|----------|
| **数据查询工具** |
| | `query_ipo_data` | 查询IPO数据 | stock_code, start_date, end_date, limit |
| | `query_placing_data` | 查询配售数据 | stock_code, start_date, end_date, limit |
| | `query_rights_data` | 查询供股数据 | stock_code, start_date, end_date, limit |
| | `query_consolidation_data` | 查询合股数据 | stock_code, start_date, end_date, limit |
| **文档检索工具** |
| | `search_documents` | 搜索公告文档 | stock_code, document_type, start_date, limit |
| | `retrieve_chunks` | 检索文档切块 | doc_id, stock_code, keyword, limit |
| **内容分析工具** |
| | `synthesize_chunks` | 合成多个切块 | chunks_json |
| | `extract_key_info` | 提取关键信息 | text, info_type |
| | `compare_data` | 对比两组数据 | data1_json, data2_json, dimensions |
| **时间感知工具** |
| | `get_current_time` | 获取当前时间 | 无 |
| | `get_market_time` | 获取市场状态 | 无 |
| | `calculate_time_diff` | 计算时间差 | date_str, format_type |
| | `format_time_period` | 格式化时间段 | start_date, end_date |
| | `get_date_info` | 获取日期信息 | date_str |
| **Layer 3数据增强工具** |
| | `assess_data_quality` | 评估数据质量 | data_json |
| | `enhance_market_data` | 增强市场数据 | query, stock_data |
| | `get_real_time_stock_info` | 获取实时股票信息 | symbol |
| **辅助工具** |
| | `get_document_metadata` | 获取文档元信息 | doc_id |

**Layer 3 数据增强特性**：
- ✅ 实时市场数据获取（AkShare + Yahoo Finance双数据源）
- ✅ 数据质量评估（完整性、准确性、时效性、一致性四维度）
- ✅ 智能数据增强（自动降级策略，优雅失败处理）
- ✅ 市场状态感知和时间上下文自动注入

## 开发注意事项

### 配置驱动设计

- **所有配置从YAML文件和环境变量读取，零硬编码**
- 修改Agent行为或工具列表只需编辑配置文件
- **提示词完全配置化**：在 `config/prompts/prompts.yaml` 中修改系统提示词，无需修改代码
- 新工具会自动加载（支持`src/tools/custom/`目录）
- 配置热更新：修改提示词配置后，重启服务即可生效

### Agent扩展点

- 新Agent类型可在`config/agents.yaml`的`sub_agents`中配置
- 支持planned、market、financial、news等多种Agent类型
- Supervisor会自动路由到enabled的Agent

### 测试和调试

- CLI默认显示Agent思考过程，便于调试
- 使用`--no-thoughts`参数可隐藏思考过程
- CLI详细模式：`hkex-agent ask "问题" -d` 显示完整执行流程
- API提供健康检查端点：`GET /api/v1/health`
- Web界面提供可视化任务管理和数据查看
- 工具列表查看：`hkex-agent tools-list`
- 配置查看：`hkex-agent config`

**思考过程展示示例**：
```bash
$ hkex-agent ask "查询00700配售数据"

💭 思考: 需要查询00700的配售数据...
🔧 调用工具: query_placing_data
✅ 工具返回: [{"stock_code": "00700", ...}]
💭 思考: 根据查询结果，配售信息为...
```

### 常见修改场景

1. **添加新工具**:
   ```python
   # 在 src/tools/custom/ 创建工具文件
   # 修改 config/agents.yaml 中的 tools 列表
   ```

2. **调整Agent行为**:
   ```yaml
   # 修改 config/agents.yaml
   sub_agents:
     document:
       enabled: true
       temperature: 0.1
       max_iterations: 10
   ```

3. **更换LLM模型**:
   ```bash
   # 修改 .env 文件
   SILICONFLOW_FAST_MODEL=deepseek-ai/DeepSeek-V3
   SILICONFLOW_STRONG_MODEL=Qwen/Qwen2.5-72B-Instruct
   OPENAI_API_KEY=your_openai_key  # 可选：OpenAI作为备选
   ```

4. **启用Web管理界面**:
   ```bash
   # 启动Web服务
   ./run_web.sh
   # 或指定端口
   ./run_web.sh 9000

   # 访问 http://localhost:8080
   ```

5. **自定义文档过滤规则**:
   ```python
   # 编辑 scripts/document_filter_configurable.py
   # 修改 FILTER_PATTERNS 来自定义过滤规则
   ```

4. **自定义提示词**:
   ```yaml
   # 编辑 config/prompts/prompts.yaml
   planner_system_prompt: "...自定义Planner提示词..."
   document_agent_system_prompt: "...自定义Document Agent提示词..."
   planner_few_shot_examples:
     - question: "..."
       answer: "..."
   ```

### 调试与故障排查

1. **查看Agent思考过程**:
   ```bash
   hkex-agent ask "查询00700" -d  # 详细模式显示思考步骤
   ```

2. **API调试**:
   ```bash
   curl http://localhost:8000/api/v1/tools  # 列出可用工具
   curl http://localhost:8000/api/v1/health  # 健康检查
   ```

3. **Web界面调试**:
   ```bash
   # 检查Web服务状态
   curl http://localhost:8000/
   # 查看Web API文档
   http://localhost:8000/api/docs
   ```

4. **常见问题**:
   - **Document Agent未启用**: 检查`config/agents.yaml`中`document.enabled=true`
   - **API密钥错误**: 确认`.env`中`SILICONFLOW_API_KEY`正确
   - **工具未加载**: 检查`src/tools/custom/`中的工具文件格式
   - **Web界面无法访问**: 确认端口未被占用，检查`run_web.sh`输出日志
   - **上传失败**: 检查`src/web/static/uploads`目录权限和大小限制

4. **日志查看**:
   ```bash
   # CLI默认显示详细日志，包括工具调用和思考过程
   # API日志查看 uvicorn 输出
   ```

### 配置优先级

配置加载顺序（后者覆盖前者）：
1. `src/config/settings.py` 默认值
2. `.env` 环境变量
3. `config/agents.yaml` Agent配置
4. `config/tools.yaml` 工具配置
5. `config/prompts/prompts.yaml` 提示词配置

**注意**: 提示词完全配置化，所有系统提示词从`config/prompts/prompts.yaml`加载，代码中无硬编码提示词。

## 🎯 项目特性总结

### 三层架构（Phase 1-3已实现）

**Phase 1 - 基础版本**（✅已完成）：
- Document Agent（ReAct模式）
- 数据库工具集（IPO、配售、供股、合股）
- 文档检索工具
- API和CLI接口

**Phase 2 - 上下文注入**（✅已完成）：
- 智能查询分析
- 时间上下文自动注入
- 市场状态感知
- 业务数据时效性标注

**Phase 3 - 数据增强**（✅已完成）：
- 实时市场数据获取（AkShare + Yahoo Finance双数据源）
- 数据质量评估（完整性、准确性、时效性、一致性四维度）
- 智能数据增强（自动降级策略，优雅失败处理）

### 三种接口

1. **CLI命令行**：支持交互式对话和单次问答，默认展示思考过程
2. **FastAPI REST API**：提供同步和流式查询，支持会话管理
3. **Web管理界面**：现代化UI，支持文件上传、任务管理、数据查看、统计分析

### 配置驱动

- **零硬编码**：所有配置从YAML文件和环境变量读取
- **提示词配置化**：所有系统提示词在`config/prompts/prompts.yaml`中管理
- **Agent可配置**：在`config/agents.yaml`中调整模型、温度、工具列表
- **工具可扩展**：支持自定义工具，自动加载`src/tools/custom/`目录