# 提示词 A/B 测试计划

**创建时间**: 2025-10-25  
**目标**: 通过A/B测试优化系统提示词，提升Agent性能和用户体验  
**测试范围**: Planner、Document Agent、Reflector

---

## 📋 测试目标

### 主要目标
1. **提升任务规划准确性**：优化Planner提示词，提高多步任务分解质量
2. **优化工具选择策略**：改进Document Agent提示词，提高工具调用准确率
3. **提高结果评估精度**：调整Reflector提示词，优化质量评估标准

### 成功指标
- **准确性**: 正确回答率提升 10%+
- **效率**: 平均工具调用次数减少 15%+
- **质量**: 用户满意度提升 20%+

---

## 🧪 测试场景设计

### 场景1: Planner 提示词优化

**测试维度**: 任务分解策略

#### 版本A（当前版本）
```yaml
planner_system_prompt: |
  你是一个任务规划专家，负责将用户查询分解为可执行的步骤。
  
  ## 规划原则
  1. **简单查询**（单一数据源、无需对比）→ 生成单步计划
  2. **复杂查询**（多数据源、需要对比分析）→ 分解为多步
  ...
```

**特点**:
- 强调简单/复杂二分法
- 工具推荐较为笼统
- 依赖Agent自主判断

#### 版本B（优化版本）
```yaml
planner_system_prompt: |
  你是一个任务规划专家，采用渐进式规划策略。
  
  ## 规划策略（升级）
  1. **即时查询**（单一股票单一指标）→ 1步执行
  2. **分析查询**（单一股票多维度）→ 2-3步串行
  3. **对比查询**（多股票对比）→ 3-5步并行+汇总
  4. **深度研究**（趋势+原因分析）→ 5-7步分层执行
  
  ## 智能工具路由
  - 明确查询类型 → 直接推荐精确工具列表
  - 模糊查询 → 先探索后执行的两阶段规划
  - 复杂查询 → 拆分子查询，标注依赖关系
  ...
```

**改进点**:
- 四级分类更细化
- 智能工具路由机制
- 明确并行/串行执行策略

**测试集**:
1. "查询腾讯控股最近的配售公告" → 预期：1步，直接query_placing_data
2. "对比腾讯和阿里的配售条款" → 预期：3步（查询A+查询B+对比）
3. "分析小米集团Q3业绩变化的原因" → 预期：5-7步分层执行

---

### 场景2: Document Agent 提示词优化

**测试维度**: 工具选择准确性

#### 版本A（当前版本）
```yaml
document_agent_system_prompt: |
  你是港股公告文档分析专家...
  
  ## 🔧 工具分层体系（按优先级调用）
  ### Layer 1: 基础检索层（优先使用）
  - query_placing_data: 查询配售数据
  - query_ipo_data: 查询IPO数据
  ...
```

**特点**:
- 四层工具体系（Layer 1-4）
- 决策树提供指引
- Few-Shot 示例辅助

#### 版本B（优化版本）
```yaml
document_agent_system_prompt: |
  你是港股公告文档分析专家，采用**快速路径决策模型**。
  
  ## ⚡ 快速路径（80%常见查询，1-2步完成）
  
  ### 路径1: 结构化数据直达
  **触发条件**: 查询包含"配售|IPO|供股|合股" + 明确stock_code
  **执行**: 直接调用 query_*_data，禁止先search_documents
  **禁止**: ❌ 不要先搜索文档列表
  
  ### 路径2: 关键词快速检索
  **触发条件**: 查询包含明确关键词 + stock_code
  **执行**: retrieve_chunks(keyword="关键词")
  **后续**: 仅在内容不足时才调用synthesize
  
  ## 🔄 复杂路径（20%高级查询，3-5步）
  - 多文档对比 → search → retrieve → compare
  - 趋势分析 → query_*_data(时间范围) → extract → analyze
  
  ## 🚫 禁止模式（减少无效调用）
  1. ❌ 已有doc_id时不要再search_documents
  2. ❌ 结构化查询时不要用retrieve_chunks全文扫描
  3. ❌ 单个chunk时不要调用synthesize_chunks
  ...
```

**改进点**:
- 快速路径优先（减少工具调用次数）
- 明确禁止模式（避免冗余调用）
- 触发条件更明确

**测试集**:
1. "查询00700.hk的配售信息" → 预期：直接query_placing_data，不先search
2. "腾讯有没有提到回购？" → 预期：直接retrieve_chunks(keyword="回购")
3. "对比美团和小米最新财报" → 预期：query → query → compare（3步）

---

### 场景3: Reflector 提示词优化

**测试维度**: 结果质量评估精度

#### 版本A（当前版本）
```yaml
reflector_system_prompt: |
  你是结果质量评估专家...
  
  评估维度：
  1. 完整性（Completeness 0-1）
  2. 准确性（Accuracy 0-1）
  3. 一致性（Consistency 0-1）
  
  综合质量分数 = (完整性 * 0.5 + 准确性 * 0.3 + 一致性 * 0.2)
  
  决策标准：
  - 质量分数 ≥ 0.8: 通过
  - 质量分数 0.5-0.8: 需要补充信息
  - 质量分数 < 0.5: 需要重新执行
```

**特点**:
- 三维度评估
- 静态权重
- 固定阈值

#### 版本B（优化版本）
```yaml
reflector_system_prompt: |
  你是结果质量评估专家，采用**情境感知评估模型**。
  
  ## 📊 动态评估维度（根据查询类型调整权重）
  
  ### 查询类型识别
  1. **事实查询**（如"查询配售价"）
     - 准确性权重: 0.6
     - 完整性权重: 0.3
     - 一致性权重: 0.1
     
  2. **分析查询**（如"分析业绩变化原因"）
     - 逻辑性权重: 0.4
     - 深度权重: 0.3
     - 准确性权重: 0.3
     
  3. **对比查询**（如"对比两家公司"）
     - 对比维度完整性: 0.4
     - 公平性: 0.3
     - 准确性: 0.3
  
  ## 🎯 情境化决策标准
  
  ### 简单查询（1-2步）
  - 质量分数 ≥ 0.85: 通过
  - 质量分数 < 0.85: 重新执行（容错率低）
  
  ### 复杂查询（3-5步）
  - 质量分数 ≥ 0.75: 通过（允许更多探索）
  - 质量分数 0.6-0.75: 补充关键缺失项
  - 质量分数 < 0.6: 重新规划
  
  ### 深度研究（5+步）
  - 质量分数 ≥ 0.70: 通过（鼓励深度探索）
  - 持续优化直到满意或达到最大迭代次数
  ...
```

**改进点**:
- 情境感知（根据查询类型调整）
- 动态权重（不同维度不同重要性）
- 分层决策（简单查询严格，复杂查询宽松）

**测试集**:
1. "查询00700配售价" → 预期：高准确性要求（≥0.85）
2. "分析小米业绩下滑原因" → 预期：高逻辑性要求（≥0.75）
3. "对比腾讯阿里配售条款" → 预期：高对比维度完整性（≥0.75）

---

## 📈 评估指标体系

### 1. 任务成功率
- **定义**: 正确回答用户查询的比例
- **目标**: 版本B相比版本A提升 10%+
- **计算**: 成功回答数 / 总查询数

### 2. 工具调用效率
- **定义**: 平均每个查询的工具调用次数
- **目标**: 版本B减少 15%+（特别是简单查询）
- **计算**: 总工具调用次数 / 总查询数

### 3. 执行时间
- **定义**: 从查询提交到返回结果的时间
- **目标**: 版本B减少 20%+
- **计算**: 平均执行时间（秒）

### 4. 质量评估准确性
- **定义**: Reflector评估结果与人工标注的一致性
- **目标**: 版本B提升 15%+
- **计算**: 一致判断数 / 总评估数

### 5. 用户满意度（可选）
- **定义**: 用户对答案质量的主观评分
- **目标**: 版本B提升 20%+
- **计算**: 5分制平均分

---

## 🔧 实施步骤

### 阶段1: 准备阶段（1天）

**步骤1.1**: 创建提示词版本管理
```bash
# 在 config/prompts/ 目录下创建版本目录
mkdir -p config/prompts/versions/{version-a,version-b}

# 复制当前版本为 version-a（基线）
cp config/prompts/prompts.yaml config/prompts/versions/version-a/prompts.yaml

# 创建 version-b（优化版本）
cp config/prompts/prompts.yaml config/prompts/versions/version-b/prompts.yaml
# 手动编辑 version-b 文件，应用上述优化
```

**步骤1.2**: 准备测试数据集
```python
# tests/ab_test_dataset.yaml
test_cases:
  # Planner 测试集（30个查询）
  planner:
    - query: "查询腾讯控股最近的配售公告"
      expected_steps: 1
      expected_tools: ["query_placing_data"]
      complexity: "simple"
    
    - query: "对比腾讯和阿里的配售条款"
      expected_steps: 3
      expected_tools: ["query_placing_data", "query_placing_data", "compare_data"]
      complexity: "medium"
    
    # ... 添加更多测试用例
  
  # Document Agent 测试集（50个查询）
  document_agent:
    - query: "查询00700.hk的配售信息"
      expected_tools: ["query_placing_data"]
      expected_tool_calls: 1
      
    # ... 添加更多测试用例
  
  # Reflector 测试集（30个评估场景）
  reflector:
    - query_type: "fact_query"
      expected_threshold: 0.85
      
    # ... 添加更多测试用例
```

**步骤1.3**: 实现AB测试框架
```python
# tests/ab_test_runner.py
import yaml
from pathlib import Path
from src.utils.prompts import PromptLoader

class ABTestRunner:
    """A/B 测试运行器"""
    
    def __init__(self, version: str = "a"):
        """
        Args:
            version: "a" 或 "b"
        """
        self.version = version
        self.prompts_path = f"config/prompts/versions/version-{version}/prompts.yaml"
        
        # 临时替换提示词路径
        self._setup_prompts()
    
    def _setup_prompts(self):
        """设置测试使用的提示词版本"""
        # 保存原配置
        self.original_path = "config/prompts/prompts.yaml"
        
        # 临时替换
        import shutil
        shutil.copy(self.prompts_path, self.original_path)
    
    def run_test_suite(self, test_dataset: dict) -> dict:
        """运行测试套件"""
        results = {
            "version": self.version,
            "metrics": {},
            "test_cases": []
        }
        
        # 运行测试用例
        for category, cases in test_dataset.items():
            category_results = self._run_category(category, cases)
            results["test_cases"].extend(category_results)
        
        # 计算汇总指标
        results["metrics"] = self._calculate_metrics(results["test_cases"])
        
        return results
    
    def _run_category(self, category: str, cases: list) -> list:
        """运行某个类别的测试用例"""
        # 实现测试逻辑
        pass
    
    def _calculate_metrics(self, test_cases: list) -> dict:
        """计算评估指标"""
        return {
            "success_rate": 0.0,
            "avg_tool_calls": 0.0,
            "avg_execution_time": 0.0,
            "quality_accuracy": 0.0
        }
```

---

### 阶段2: 执行测试（2-3天）

**步骤2.1**: 运行版本A测试
```bash
# 运行版本A测试
python tests/ab_test_runner.py --version a --output results/version_a_results.json

# 收集指标
- 任务成功率
- 平均工具调用次数
- 平均执行时间
- 质量评估准确性
```

**步骤2.2**: 运行版本B测试
```bash
# 运行版本B测试
python tests/ab_test_runner.py --version b --output results/version_b_results.json

# 收集相同指标
```

**步骤2.3**: 统计分析
```python
# tests/analyze_ab_results.py
import json

def compare_versions(results_a: dict, results_b: dict) -> dict:
    """对比两个版本的测试结果"""
    
    comparison = {
        "success_rate": {
            "version_a": results_a["metrics"]["success_rate"],
            "version_b": results_b["metrics"]["success_rate"],
            "improvement": (results_b["metrics"]["success_rate"] - results_a["metrics"]["success_rate"]) / results_a["metrics"]["success_rate"] * 100
        },
        # ... 其他指标
    }
    
    return comparison

# 运行对比
with open("results/version_a_results.json") as f:
    results_a = json.load(f)

with open("results/version_b_results.json") as f:
    results_b = json.load(f)

comparison = compare_versions(results_a, results_b)
print(json.dumps(comparison, indent=2, ensure_ascii=False))
```

---

### 阶段3: 分析决策（1天）

**决策标准**:

| 指标 | 版本B相对版本A | 决策 |
|------|---------------|------|
| 所有指标均提升 ≥10% | 采用版本B | ✅ 全面升级 |
| 3/4指标提升 ≥10% | 采用版本B，优化劣势指标 | ⚠️ 部分采用 |
| 2/4指标提升 ≥10% | 混合方案（不同Agent用不同版本） | 🔀 混合部署 |
| 少于2个指标提升 | 保留版本A，重新设计版本B | ❌ 保持现状 |

**统计显著性检验**:
```python
from scipy import stats

def is_significant(data_a: list, data_b: list, alpha: float = 0.05) -> bool:
    """检验两组数据是否有统计显著性差异"""
    t_stat, p_value = stats.ttest_ind(data_a, data_b)
    return p_value < alpha
```

---

## 📋 测试用例示例

### Planner 测试集（精选10个）

```yaml
planner_test_cases:
  # 简单查询（1步）
  - id: P001
    query: "查询腾讯控股最近的配售公告"
    expected_steps: 1
    expected_tools: ["query_placing_data"]
    
  - id: P002
    query: "00700.hk最近有IPO吗？"
    expected_steps: 1
    expected_tools: ["query_ipo_data"]
  
  # 中等查询（2-3步）
  - id: P003
    query: "小米集团最新公告说了什么？"
    expected_steps: 2-3
    expected_tools: ["search_documents", "retrieve_chunks", "synthesize_chunks"]
  
  - id: P004
    query: "对比腾讯和阿里的配售条款"
    expected_steps: 3
    expected_tools: ["query_placing_data", "query_placing_data", "compare_data"]
  
  # 复杂查询（4-5步）
  - id: P005
    query: "分析美团2024年配售相比2023年的变化趋势"
    expected_steps: 4-5
    expected_tools: ["query_placing_data", "query_placing_data", "compare_data", "extract_key_info"]
```

### Document Agent 测试集（精选10个）

```yaml
document_agent_test_cases:
  # 结构化查询（应直接query_*_data）
  - id: D001
    query: "查询00700.hk的配售信息"
    expected_tools: ["query_placing_data"]
    expected_tool_calls: 1
    should_not_use: ["search_documents"]
  
  - id: D002
    query: "2024年有哪些公司IPO？"
    expected_tools: ["query_ipo_data"]
    expected_tool_calls: 1
  
  # 关键词检索（应直接retrieve_chunks）
  - id: D003
    query: "腾讯有没有提到回购？"
    expected_tools: ["retrieve_chunks"]
    expected_tool_calls: 1-2
    should_not_use: ["search_documents"]
  
  # 完整内容查询（需要多步）
  - id: D004
    query: "阿里巴巴最新财报详细内容"
    expected_tools: ["search_documents", "retrieve_chunks", "synthesize_chunks"]
    expected_tool_calls: 3-4
```

### Reflector 测试集（精选10个）

```yaml
reflector_test_cases:
  # 事实查询（高准确性要求）
  - id: R001
    query_type: "fact_query"
    query: "查询00700配售价"
    expected_threshold: 0.85
    key_dimensions: ["accuracy"]
  
  # 分析查询（高逻辑性要求）
  - id: R002
    query_type: "analysis_query"
    query: "分析小米业绩下滑原因"
    expected_threshold: 0.75
    key_dimensions: ["logic", "depth"]
  
  # 对比查询（高完整性要求）
  - id: R003
    query_type: "comparison_query"
    query: "对比腾讯阿里配售条款"
    expected_threshold: 0.75
    key_dimensions: ["completeness", "fairness"]
```

---

## 🔄 持续优化流程

### 每周A/B测试循环

```
Week 1: 设计版本B优化 → 实施测试 → 分析结果
Week 2: 根据结果调整 → 运行版本C测试 → 对比A/B/C
Week 3: 选择最优版本 → 部署生产 → 收集反馈
Week 4: 根据反馈设计新优化 → 开始新循环
```

### 版本管理策略

```bash
config/prompts/
├── prompts.yaml            # 当前生产版本
├── versions/
│   ├── v1.0-baseline/      # 基线版本
│   ├── v1.1-fast-path/     # 快速路径优化
│   ├── v1.2-context-aware/ # 情境感知优化
│   └── v1.3-hybrid/        # 混合优化
└── experiments/
    ├── exp-001-planner/    # Planner专项实验
    ├── exp-002-tool-selection/ # 工具选择实验
    └── exp-003-quality-eval/   # 质量评估实验
```

---

## 📊 预期收益

### 短期收益（1-2周）
- ✅ 简单查询响应速度提升 30%+
- ✅ 工具调用冗余减少 20%+
- ✅ 明显错误减少 15%+

### 中期收益（1-2月）
- ✅ 任务成功率稳定在 90%+
- ✅ 平均执行时间减少 25%+
- ✅ 用户满意度提升 20%+

### 长期收益（3-6月）
- ✅ 建立持续优化机制
- ✅ 积累提示词最佳实践库
- ✅ 形成数据驱动的优化文化

---

## 🚀 快速启动指南

### 1. 准备版本B配置
```bash
# 复制当前配置
cp config/prompts/prompts.yaml config/prompts/prompts-version-b.yaml

# 编辑优化版本（应用本文档中的优化建议）
vim config/prompts/prompts-version-b.yaml
```

### 2. 运行简化测试
```bash
# 创建简化测试脚本
cat > tests/quick_ab_test.py << 'EOF'
"""快速A/B测试脚本"""
import time
from src.agent.planner import get_planner
from src.agent.document_agent import get_document_agent

# 测试查询列表
test_queries = [
    "查询腾讯控股最近的配售公告",
    "对比腾讯和阿里的配售条款",
    "小米集团最新公告说了什么？"
]

# 测试版本A
print("=== 测试版本A ===")
for query in test_queries:
    start = time.time()
    planner = get_planner()
    plan = planner.create_plan(query)
    elapsed = time.time() - start
    print(f"{query}: {len(plan.steps)}步, {elapsed:.2f}秒")

# 切换到版本B
import shutil
shutil.copy("config/prompts/prompts-version-b.yaml", "config/prompts/prompts.yaml")

# 重新加载（需要重启Python）
print("\n请重启脚本以使用版本B进行测试")
EOF

# 运行测试
python tests/quick_ab_test.py
```

### 3. 分析结果
```bash
# 查看对比报告
cat results/ab_comparison_report.txt
```

---

## 📝 总结

本AB测试计划提供了：
1. ✅ **3个优化版本**（Planner、Document Agent、Reflector）
2. ✅ **5大评估指标**（成功率、效率、时间、准确性、满意度）
3. ✅ **完整测试流程**（准备→执行→分析→决策）
4. ✅ **30+测试用例**（覆盖简单、中等、复杂查询）
5. ✅ **持续优化机制**（每周循环，版本管理）

**下一步行动**:
1. 创建版本B配置文件
2. 准备测试数据集
3. 实施AB测试框架
4. 运行测试并分析结果
5. 根据数据做出决策

---

**文档维护**: 根据实际测试结果持续更新  
**联系人**: 项目负责人  
**最后更新**: 2025-10-25

