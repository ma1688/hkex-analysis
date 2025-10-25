# Agent工具调用优化 - 测试用例

**测试目标**: 验证P0+P1优化后的工具选择准确率和Agent执行效率

**优化前基线**: 工具选择准确率~60%，平均迭代5次  
**优化后目标**: 工具选择准确率85%，平均迭代4次

---

## 测试场景1: 简单配售查询

### 测试用例1.1
**查询**: `查询腾讯控股最近的配售公告`

**预期行为**:
- ✅ Planner生成单步计划
- ✅ recommended_tools: `["query_placing_data"]`
- ✅ Agent直接调用`query_placing_data(stock_code="00700.hk")`
- ✅ 无其他工具尝试

**成功标准**:
- 工具选择正确率: 100%
- 迭代次数: 1次
- 参数格式正确（stock_code为"00700.hk"）

**测试命令**:
```bash
cd /Users/ericp/hkex-analysis
python -m src.cli.commands ask "查询腾讯控股最近的配售公告"
```

**预期输出示例**:
```
[Planner] 生成计划: 1步
[Planner建议] 优先使用工具: query_placing_data
[Agent] 调用工具: query_placing_data
[结果] 返回腾讯控股的配售数据...
```

---

### 测试用例1.2
**查询**: `小米集团有配售吗？`

**预期行为**:
- ✅ Planner识别"配售"关键词
- ✅ recommended_tools: `["query_placing_data"]`
- ✅ Agent提取stock_code为"01810.hk"
- ✅ 调用`query_placing_data(stock_code="01810.hk")`

**成功标准**:
- 自动识别小米集团代码（01810）
- 工具选择正确
- 参数格式正确

**测试命令**:
```bash
python -m src.cli.commands ask "小米集团有配售吗？"
```

---

## 测试场景2: IPO查询

### 测试用例2.1
**查询**: `2024年有哪些公司IPO？`

**预期行为**:
- ✅ Planner生成单步计划
- ✅ recommended_tools: `["query_ipo_data"]`
- ✅ Agent调用`query_ipo_data(start_date="2024-01-01", end_date="2024-12-31")`
- ✅ 无需stock_code参数

**成功标准**:
- 正确识别时间范围查询
- 工具选择正确
- 日期参数格式正确（YYYY-MM-DD）
- 不传递不必要的stock_code

**测试命令**:
```bash
python -m src.cli.commands ask "2024年有哪些公司IPO？"
```

---

### 测试用例2.2
**查询**: `查询比亚迪的IPO信息`

**预期行为**:
- ✅ Planner推荐`query_ipo_data`
- ✅ Agent识别比亚迪代码为"01211.hk"
- ✅ 调用`query_ipo_data(stock_code="01211.hk")`

**测试命令**:
```bash
python -m src.cli.commands ask "查询比亚迪的IPO信息"
```

---

## 测试场景3: 完整内容检索

### 测试用例3.1
**查询**: `阿里巴巴最新公告说了什么重要内容？`

**预期行为**:
- ✅ Planner生成多步计划（2-3步）
- ✅ 步骤1推荐: `["search_documents"]`
- ✅ 步骤2推荐: `["retrieve_chunks", "synthesize_chunks"]`
- ✅ Agent按顺序调用工具链

**成功标准**:
- 正确识别需要完整内容而非结构化数据
- 工具链完整：search → retrieve → synthesize
- 步骤依赖关系正确

**测试命令**:
```bash
python -m src.cli.commands ask "阿里巴巴最新公告说了什么重要内容？"
```

**预期工具调用序列**:
1. `search_documents(stock_code="09988.hk", limit=1)`
2. `retrieve_chunks(doc_id="<从步骤1获取>", limit=30)`
3. `synthesize_chunks(chunks_json="<从步骤2获取>")`

---

### 测试用例3.2
**查询**: `腾讯控股有没有提到回购的公告？`

**预期行为**:
- ✅ Planner生成关键词搜索计划
- ✅ 推荐: `["search_documents", "retrieve_chunks"]`
- ✅ Agent使用keyword参数

**成功标准**:
- 正确识别关键词搜索场景
- retrieve_chunks使用keyword="回购"参数

**测试命令**:
```bash
python -m src.cli.commands ask "腾讯控股有没有提到回购的公告？"
```

---

## 测试场景4: 对比分析

### 测试用例4.1
**查询**: `对比腾讯和阿里的配售条款，哪个更有利？`

**预期行为**:
- ✅ Planner生成3步计划
- ✅ 步骤1推荐: `["query_placing_data"]` (腾讯)
- ✅ 步骤2推荐: `["query_placing_data"]` (阿里)
- ✅ 步骤3推荐: `["compare_data"]`
- ✅ 依赖关系: 步骤3依赖步骤1和2

**成功标准**:
- 正确分解为多步任务
- 每步工具推荐准确
- 对比维度包含：配售价、折让率、配售比例

**测试命令**:
```bash
python -m src.cli.commands ask "对比腾讯和阿里的配售条款，哪个更有利？"
```

**预期工具调用序列**:
1. `query_placing_data(stock_code="00700.hk", limit=3)`
2. `query_placing_data(stock_code="09988.hk", limit=3)`
3. `compare_data(data1_json=..., data2_json=..., comparison_dimensions="配售价,折让率,配售比例")`

---

### 测试用例4.2
**查询**: `对比小米和比亚迪的IPO发行价`

**预期行为**:
- ✅ Planner识别对比任务
- ✅ 推荐: `query_ipo_data` (两次) + `compare_data`
- ✅ 对比维度聚焦：发行价

**测试命令**:
```bash
python -m src.cli.commands ask "对比小米和比亚迪的IPO发行价"
```

---

## 测试场景5: 混合场景（测试决策树）

### 测试用例5.1
**查询**: `查询腾讯控股的配售，并分析详细条款`

**预期行为**:
- ✅ Planner生成2步计划
- ✅ 步骤1: `query_placing_data` (获取概要)
- ✅ 步骤2: `search_documents` + `retrieve_chunks` (获取详细条款)

**成功标准**:
- 正确识别需要两种数据源
- 先结构化数据，后文档详情

**测试命令**:
```bash
python -m src.cli.commands ask "查询腾讯控股的配售，并分析详细条款"
```

---

### 测试用例5.2
**查询**: `最近有什么配售公告值得关注？`

**预期行为**:
- ✅ Planner识别时间维度（"最近"）
- ✅ 可能推荐: `query_placing_data` (不指定stock_code，按时间排序)
- ✅ 或推荐: `search_documents` (document_type="配售")

**成功标准**:
- 正确处理开放性查询
- 时间参数合理（如最近30天）

**测试命令**:
```bash
python -m src.cli.commands ask "最近有什么配售公告值得关注？"
```

---

## 错误场景测试（参数验证）

### 测试用例6.1
**查询**: `查询700的配售` (错误的stock_code格式)

**预期行为**:
- ✅ Agent自动修正为"00700.hk"
- ✅ 或Prompt中的错误避免指导生效
- ✅ 最终调用`query_placing_data(stock_code="00700.hk")`

**成功标准**:
- 参数格式自动修正
- 无错误重试

**测试命令**:
```bash
python -m src.cli.commands ask "查询700的配售"
```

---

## 测试执行表格

| 测试ID | 场景 | 查询 | 预期工具 | 实际工具 | 准确率 | 迭代次数 | 通过 |
|--------|------|------|----------|----------|--------|----------|------|
| 1.1 | 简单配售 | 腾讯配售 | query_placing_data | - | - | - | ⬜ |
| 1.2 | 简单配售 | 小米配售 | query_placing_data | - | - | - | ⬜ |
| 2.1 | IPO查询 | 2024年IPO | query_ipo_data | - | - | - | ⬜ |
| 2.2 | IPO查询 | 比亚迪IPO | query_ipo_data | - | - | - | ⬜ |
| 3.1 | 内容检索 | 阿里最新公告 | search→retrieve→synthesize | - | - | - | ⬜ |
| 3.2 | 关键词搜索 | 腾讯回购 | search→retrieve(keyword) | - | - | - | ⬜ |
| 4.1 | 对比分析 | 腾讯vs阿里配售 | query×2→compare | - | - | - | ⬜ |
| 4.2 | 对比分析 | 小米vs比亚迪IPO | query×2→compare | - | - | - | ⬜ |
| 5.1 | 混合场景 | 配售+详细条款 | query→search→retrieve | - | - | - | ⬜ |
| 5.2 | 开放查询 | 最近配售 | query或search | - | - | - | ⬜ |
| 6.1 | 错误修正 | 错误代码格式 | 自动修正 | - | - | - | ⬜ |

---

## 评估标准

### 工具选择准确率
```
准确率 = 正确的工具调用次数 / 总工具调用次数 × 100%
```

**目标**: ≥85%

### Agent迭代效率
```
平均迭代次数 = 总迭代次数 / 测试用例数
```

**目标**: ≤4次/查询

### Planner-Agent一致性
```
一致性 = 采纳Planner推荐的次数 / 总推荐次数 × 100%
```

**目标**: ≥80%

---

## 测试脚本（批量执行）

创建`tests/run_optimization_tests.sh`:

```bash
#!/bin/bash

# 批量测试脚本
cd /Users/ericp/hkex-analysis

echo "========================================="
echo "Agent优化效果测试"
echo "========================================="

# 测试1: 简单配售查询
echo "\n[测试1.1] 简单配售查询 - 腾讯"
python -m src.cli.commands ask "查询腾讯控股最近的配售公告" > /tmp/test_1_1.log 2>&1
grep -i "query_placing_data" /tmp/test_1_1.log && echo "✅ 通过" || echo "❌ 失败"

# 测试2: IPO查询
echo "\n[测试2.1] IPO查询 - 2024年"
python -m src.cli.commands ask "2024年有哪些公司IPO？" > /tmp/test_2_1.log 2>&1
grep -i "query_ipo_data" /tmp/test_2_1.log && echo "✅ 通过" || echo "❌ 失败"

# 测试3: 完整内容检索
echo "\n[测试3.1] 内容检索 - 阿里最新公告"
python -m src.cli.commands ask "阿里巴巴最新公告说了什么重要内容？" > /tmp/test_3_1.log 2>&1
grep -i "search_documents" /tmp/test_3_1.log && echo "✅ 通过" || echo "❌ 失败"

# 测试4: 对比分析
echo "\n[测试4.1] 对比分析 - 腾讯vs阿里"
python -m src.cli.commands ask "对比腾讯和阿里的配售条款，哪个更有利？" > /tmp/test_4_1.log 2>&1
grep -i "compare_data" /tmp/test_4_1.log && echo "✅ 通过" || echo "❌ 失败"

echo "\n========================================="
echo "测试完成"
echo "========================================="
```

**使用方法**:
```bash
chmod +x tests/run_optimization_tests.sh
./tests/run_optimization_tests.sh
```

---

## 下一步

1. ✅ 手动执行3-5个测试用例
2. ✅ 记录实际工具调用序列
3. ✅ 计算准确率和迭代次数
4. ✅ 对比优化前后数据
5. ✅ 生成测试报告

**开始测试**: 请从测试用例1.1开始，逐个执行并观察Agent行为。

