# 港股公告智能问答系统

基于LangGraph的港股公告智能分析Agent系统，支持多种查询方式，提供API和CLI双接口。

## ✨ 特性

- 🤖 **基于LangGraph**: 使用LangGraph ReAct Agent架构
- 🔧 **工具化设计**: 支持数据库查询、文档检索、内容合成等多种工具
- 🎯 **配置驱动**: 所有配置从文件读取，零硬编码
- 🚀 **双接口**: 提供FastAPI REST API和CLI命令行工具
- 🔌 **可扩展**: 支持自定义工具扩展，插件化架构
- 🌐 **多LLM支持**: 支持硅基流动和OpenAI，自动主备切换
- ⏰ **时间感知**: 内置时间工具集，支持实时时间和市场状态查询
- 📊 **数据增强**: Layer 3智能数据增强，支持AkShare和Yahoo Finance双数据源，提供实时市场数据和质量评估

## 📋 前置要求

- Python 3.11+
- ClickHouse数据库（已有港股公告数据）
- 硅基流动API密钥（或OpenAI API密钥）

## 🚀 快速开始

### 💡 最快方式（推荐）

如果环境已配置好，直接使用便捷脚本：

```bash
cd /Users/ericp/new-langgraph/hkex-analysis

# CLI交互式对话
./run_cli.sh chat

# CLI单次问答
./run_cli.sh ask "查询腾讯控股最近的配售公告"

# 启动API服务
./run_api.sh

# 查看帮助
./run_cli.sh --help
```

> 📘 详细说明请查看 [QUICK_START.md](QUICK_START.md)

### 1. 安装依赖

```bash
# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装项目
pip install -e ".[dev]"
```

### 2. 配置环境变量

复制`.env.example`并填写配置：

```bash
cp .env.example .env
# 编辑 .env 文件，填写以下关键配置：
# - SILICONFLOW_API_KEY: 你的硅基流动API密钥
# - CLICKHOUSE_* : ClickHouse连接信息（如需修改）
```

### 3. 启用Document Agent

编辑 `config/agents.yaml`，确保`document.enabled = true`

```yaml
sub_agents:
  document:
    enabled: true  # 必须设置为true
    model: "deepseek-ai/DeepSeek-V3"
```

### 4. 启动服务

#### 方式一：启动API服务

```bash
uvicorn src.api.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看API文档

#### 方式二：使用CLI

```bash
# 单次问答（默认显示思考过程）✨
hkex-agent ask "查询腾讯控股最近的配售公告"

# 交互式对话（默认显示思考过程）✨
hkex-agent chat

# 不显示思考过程
hkex-agent chat --no-thoughts
hkex-agent ask "查询00700配售数据" --no-thoughts

# 列出工具
hkex-agent tools-list

# 查看配置
hkex-agent config
```

> ✨ **新功能**: CLI默认实时展示Agent思考过程（思考步骤、工具调用、执行结果），让您清楚看到推理过程！

## 📚 使用示例

### CLI示例

```bash
# 查询配售数据
hkex-agent ask "查询00700.hk的配售公告"

# 对比分析
hkex-agent ask "对比腾讯和阿里最近的配售公告"

# 提取关键信息
hkex-agent ask "腾讯最近配售的折让率是多少？"

# 时间相关查询
hkex-agent ask "现在几点了？"
hkex-agent ask "港股市场现在开盘了吗？"
hkex-agent ask "今天是交易日吗？"
```

### API示例（Python）

```python
import httpx

# 同步请求
response = httpx.post(
    "http://localhost:8000/api/v1/query",
    json={
        "question": "查询腾讯控股最近的配售公告",
        "user_id": "user_123"
    }
)
result = response.json()
print(result["answer"])

# 健康检查
health = httpx.get("http://localhost:8000/api/v1/health").json()
print(health)
```

### API示例（curl）

```bash
# 查询（同步）
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "查询腾讯控股最近的配售公告"}'

# 流式查询（SSE）
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "查询腾讯控股最近的配售公告"}' \
  -N

# 获取会话历史
curl "http://localhost:8000/api/v1/sessions/{session_id}/history?limit=20"

# 健康检查
curl http://localhost:8000/api/v1/health

# 列出工具
curl http://localhost:8000/api/v1/tools
```

## 🔧 架构说明

### 目录结构

```
hkex-analysis/
├── config/              # 配置文件
│   ├── agents.yaml      # Agent配置
│   └── tools.yaml       # 工具配置
├── src/
│   ├── agent/           # Agent模块
│   │   ├── document_agent.py  # 文档分析Agent
│   │   ├── state.py           # 状态定义
│   │   └── schemas.py         # 数据模型
│   ├── api/             # API模块
│   │   ├── main.py      # FastAPI应用
│   │   └── schemas.py   # API数据模型
│   ├── cli/             # CLI模块
│   │   └── commands.py  # CLI命令
│   ├── config/          # 配置管理
│   │   └── settings.py  # Settings类
│   ├── llm/             # LLM管理
│   │   └── manager.py   # 多LLM管理器
│   ├── tools/           # 工具集
│   │   ├── structured_data.py    # 数据库工具
│   │   ├── document_retrieval.py # 文档检索工具
│   │   ├── synthesis.py          # 合成分析工具
│   │   ├── loader.py             # 工具加载器
│   │   └── custom/               # 自定义工具目录
│   └── utils/           # 工具模块
│       ├── clickhouse.py  # ClickHouse客户端
│       └── prompts.py     # 提示词模板
├── .env.example         # 环境变量模板
├── pyproject.toml       # 项目配置
└── README.md            # 本文档
```

### 核心组件

1. **Document Agent**: 基于`create_react_agent`构建的公告分析Agent
2. **工具集**:
    - 结构化数据查询（IPO、配售、供股、合股）
    - 文档检索（search_documents、retrieve_chunks）
    - 内容合成（synthesize_chunks、extract_key_info）
3. **LLM Manager**: 支持多模型切换和主备策略
4. **Layer 2 - 上下文注入**: 智能识别查询需求，自动注入时间、市场状态等上下文
5. **Layer 3 - 数据增强**: 实时市场数据获取、数据质量评估和智能增强
6. **配置系统**: 所有配置从YAML和环境变量读取

## 🛠️ 自定义扩展

### 添加自定义工具

1. 在`src/tools/custom/`目录创建新的Python文件：

```python
# src/tools/custom/my_tool.py
from langchain_core.tools import tool

@tool
def calculate_pe_ratio(price: float, eps: float) -> str:
    """计算市盈率
    
    Args:
        price: 股价
        eps: 每股收益
    
    Returns:
        计算结果
    """
    if eps == 0:
        return "无法计算（EPS为0）"
    pe = price / eps
    return f"PE Ratio: {pe:.2f}"
```

2. 在`config/agents.yaml`中添加到工具列表：

```yaml
sub_agents:
  document:
    tools:
      - calculate_pe_ratio  # 添加新工具
      - query_placing_data
      # ...
```

3. 重启服务即可自动加载

## 🔍 可用工具

| 工具名                        | 功能       | 参数                                           |
|----------------------------|----------|----------------------------------------------|
| **数据查询工具**                 |
| `query_placing_data`       | 查询配售数据   | stock_code, start_date, end_date, limit      |
| `query_ipo_data`           | 查询IPO数据  | stock_code, start_date, end_date, limit      |
| `query_rights_data`        | 查询供股数据   | stock_code, start_date, end_date, limit      |
| `query_consolidation_data` | 查询合股数据   | stock_code, start_date, end_date, limit      |
| **文档检索工具**                 |
| `search_documents`         | 搜索公告文档   | stock_code, document_type, start_date, limit |
| `retrieve_chunks`          | 检索文档切块   | doc_id, stock_code, keyword, limit           |
| **内容分析工具**                 |
| `synthesize_chunks`        | 合成多个切块   | chunks_json                                  |
| `extract_key_info`         | 提取关键信息   | text, info_type                              |
| `compare_data`             | 对比两组数据   | data1_json, data2_json, dimensions           |
| **时间感知工具**                 |
| `get_current_time`         | 获取当前时间   | 无                                            |
| `get_market_time`          | 获取市场状态   | 无                                            |
| `calculate_time_diff`      | 计算时间差    | date_str, format_type                        |
| `format_time_period`       | 格式化时间段   | start_date, end_date                         |
| `get_date_info`            | 获取日期信息   | date_str                                     |
| **Layer 3数据增强工具**          |
| `assess_data_quality`      | 评估数据质量   | data_json                                    |
| `enhance_market_data`      | 增强市场数据   | query, stock_data                            |
| `get_real_time_stock_info` | 获取实时股票信息 | symbol                                       |
| **辅助工具**                   |
| `get_document_metadata`    | 获取文档元信息  | doc_id                                       |

## ⚙️ 配置说明

### 环境变量（.env）

| 变量名                        | 说明           | 默认值                       |
|----------------------------|--------------|---------------------------|
| `SILICONFLOW_API_KEY`      | 硅基流动API密钥    | 必填                        |
| `SILICONFLOW_FAST_MODEL`   | 快速模型         | deepseek-ai/DeepSeek-V3   |
| `SILICONFLOW_STRONG_MODEL` | 强模型          | Qwen/Qwen2.5-72B-Instruct |
| `CLICKHOUSE_HOST`          | ClickHouse主机 | 1.14.239.79               |
| `CLICKHOUSE_PORT`          | ClickHouse端口 | 8868                      |
| `CLICKHOUSE_DATABASE`      | 数据库名         | hkex_analysis             |
| `APP_PORT`                 | API服务端口      | 8000                      |

### Agent配置（config/agents.yaml）

控制Agent行为、模型选择、工具列表等

### 工具配置（config/tools.yaml）

控制工具执行超时、重试、并发等

## 🧪 测试

```bash
# 测试健康检查
curl http://localhost:8000/api/v1/health

# 测试简单查询
hkex-agent ask "腾讯的股票代码是什么？"

# 测试工具调用
hkex-agent ask "查询00700.hk最近的配售数据"
```

## 📊 数据库表结构

系统使用以下ClickHouse表：

- `pdf_documents`: 公告文档元信息
- `pdf_chunks`: 公告切块内容
- `ipo_data`: IPO数据
- `placing_data`: 配售数据
- `rights_data`: 供股数据
- `consolidation_data`: 合股数据

## 🚧 未来扩展（预留）

当前实现为**Phase 1-3分层架构**，包含：

**Phase 1 - 基础版本**：

- ✅ Document Agent
- ✅ 数据库工具集
- ✅ 文档检索工具
- ✅ API和CLI接口

**Phase 2 - 上下文注入**（已实现）：

- ✅ 智能查询分析
- ✅ 时间上下文自动注入
- ✅ 市场状态感知
- ✅ 业务数据时效性标注

**Phase 3 - 数据增强**（已完成）：

- ✅ 实时市场数据获取（AkShare + Yahoo Finance双数据源）
- ✅ 数据质量评估（完整性、准确性、时效性、一致性四维度）
- ✅ 智能数据增强（自动降级策略，优雅失败处理）

**Phase 4-5扩展功能**（架构已预留）：

- ⏳ Planner模块（任务规划）
- ⏳ Supervisor协调器（多Agent调度）
- ⏳ Reflector模块（结果验证）
- ⏳ Memory Manager（长短期记忆）
- ⏳ Market Agent（行情分析）
- ⏳ Financial Agent（财报分析）

扩展方式参见文档 `hk-stock-analysis-agent.plan.md`

## 📝 License

MIT

## 👥 维护者

Development Team

---

**版本**: 0.1.0 (Phase 1-3 完成)

**最后更新**: 2025-10-25

