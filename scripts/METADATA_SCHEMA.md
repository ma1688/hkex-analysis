# Metadata字段说明文档

## 概述

`documents_v2` 和 `document_sections` 表中的 `metadata` 字段采用**JSON格式**存储扩展信息，支持灵活的数据扩展而不改变表结构。

---

## 1. documents_v2.metadata

### 字段定义
```sql
metadata String DEFAULT '{}'  -- JSON格式的扩展信息
```

### JSON Schema

```json
{
  "rights_ratio": "1:4",              // 供股比例（必填）
  "processing_version": "2.0",        // 处理版本（必填）
  "source_system": "hkex",            // 数据来源（必填）
  "file_hash": "md5_abc123...",       // 文件MD5哈希（可选）
  "custom_tags": ["urgent", "重要"],   // 自定义标签（可选）
  "processor": "chunk_v2.0",          // 处理器版本（可选）
  "notes": "手动审核通过"              // 备注信息（可选）
}
```

### 字段说明

| 字段名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `rights_ratio` | String | ✅ | 供股比例，格式：`持有数:获发数` | `"1:4"` |
| `processing_version` | String | ✅ | 数据处理版本 | `"2.0"` |
| `source_system` | String | ✅ | 数据来源系统 | `"hkex"` |
| `file_hash` | String | ❌ | 文件MD5/SHA256哈希（用于重复检测） | `"md5_abc123..."` |
| `custom_tags` | Array | ❌ | 自定义标签（用于分类、标记） | `["urgent", "高优先级"]` |
| `processor` | String | ❌ | 处理器标识 | `"chunk_v2.0"` |
| `notes` | String | ❌ | 人工备注 | `"已人工审核"` |

### 实际示例

#### 示例1：基本供股文档

```json
{
  "rights_ratio": "1:4",
  "processing_version": "2.0",
  "source_system": "hkex"
}
```

#### 示例2：包含哈希和标签

```json
{
  "rights_ratio": "2:1",
  "processing_version": "2.0",
  "source_system": "hkex",
  "file_hash": "md5_7d8f3c2a...",
  "custom_tags": ["urgent", "重要", "需审核"]
}
```

#### 示例3：完整信息

```json
{
  "rights_ratio": "1:3",
  "processing_version": "2.0",
  "source_system": "hkex",
  "file_hash": "sha256_abc123...",
  "custom_tags": ["2025Q1", "科技股"],
  "processor": "chunk_v2.0_beta",
  "notes": "文档包含附表，需额外处理"
}
```

### ClickHouse查询示例

```sql
-- 1. 提取供股比例
SELECT 
    doc_id,
    stock_code,
    JSONExtractString(metadata, 'rights_ratio') AS ratio
FROM documents_v2
WHERE document_type = 'rights';

-- 2. 按处理版本统计
SELECT 
    JSONExtractString(metadata, 'processing_version') AS version,
    count() AS cnt
FROM documents_v2
GROUP BY version;

-- 3. 查找带特定标签的文档
SELECT doc_id, title
FROM documents_v2
WHERE has(JSONExtractArrayRaw(metadata, 'custom_tags'), '"urgent"');

-- 4. 查找有备注的文档
SELECT 
    doc_id,
    JSONExtractString(metadata, 'notes') AS notes
FROM documents_v2
WHERE JSONHas(metadata, 'notes');
```

---

## 2. document_sections.metadata

### 字段定义
```sql
metadata String DEFAULT '{}'  -- JSON格式的扩展信息
```

### JSON Schema

```json
{
  "section_num": "一",                // 章节编号（必填）
  "has_table": true,                 // 是否包含表格（必填）
  "table_count": 2,                  // 表格数量（必填）
  "key_entities": [                  // 关键实体（可选）
    {"type": "price", "value": "HKD 1.50"},
    {"type": "date", "value": "2025-11-15"}
  ],
  "parent_section": "section_id_xxx", // 父章节ID（可选，多级结构时）
  "language": "zh-HK",               // 语言（可选）
  "has_formula": false,              // 是否包含公式（可选）
  "complexity": "high"               // 复杂度（可选：low/medium/high）
}
```

### 字段说明

| 字段名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `section_num` | String | ✅ | 章节编号（如：一、二、（一）） | `"一"` |
| `has_table` | Boolean | ✅ | 是否包含表格 | `true` |
| `table_count` | Int | ✅ | 表格数量 | `2` |
| `key_entities` | Array | ❌ | 关键实体列表 | `[{"type":"price","value":"1.50"}]` |
| `parent_section` | String | ❌ | 父章节ID（多级结构） | `"section_id_parent"` |
| `language` | String | ❌ | 语言代码 | `"zh-HK"`, `"en-US"` |
| `has_formula` | Boolean | ❌ | 是否包含数学公式 | `false` |
| `complexity` | String | ❌ | 复杂度评级 | `"low"`, `"medium"`, `"high"` |

### 实际示例

#### 示例1：基本章节

```json
{
  "section_num": "一",
  "has_table": false,
  "table_count": 0
}
```

#### 示例2：包含表格的财务章节

```json
{
  "section_num": "四",
  "has_table": true,
  "table_count": 3,
  "key_entities": [
    {"type": "money", "value": "HKD 50,000,000"},
    {"type": "percentage", "value": "15.5%"}
  ],
  "language": "zh-HK",
  "complexity": "high"
}
```

#### 示例3：多级章节结构

```json
{
  "section_num": "（一）",
  "has_table": false,
  "table_count": 0,
  "parent_section": "section_id_main_chapter",
  "language": "zh-HK",
  "complexity": "medium"
}
```

### ClickHouse查询示例

```sql
-- 1. 统计包含表格的章节
SELECT 
    section_type,
    countIf(JSONExtractBool(metadata, 'has_table') = true) AS with_table,
    count() AS total
FROM document_sections
GROUP BY section_type;

-- 2. 查找高复杂度章节
SELECT 
    section_id,
    section_title,
    JSONExtractString(metadata, 'complexity') AS complexity
FROM document_sections
WHERE JSONExtractString(metadata, 'complexity') = 'high';

-- 3. 提取章节编号
SELECT 
    section_id,
    JSONExtractString(metadata, 'section_num') AS section_num,
    section_title
FROM document_sections
WHERE doc_id = '00328_xxx'
ORDER BY section_index;

-- 4. 查找包含价格实体的章节
SELECT section_id, section_title
FROM document_sections
WHERE JSONHas(metadata, 'key_entities')
  AND JSONExtractString(metadata, 'key_entities') LIKE '%price%';
```

---

## 3. 最佳实践

### 3.1 数据插入

#### Python示例

```python
import json

# documents_v2
metadata = {
    'rights_ratio': '1:4',
    'processing_version': '2.0',
    'source_system': 'hkex',
    'custom_tags': ['urgent']
}
metadata_json = json.dumps(metadata, ensure_ascii=False)

# document_sections
section_metadata = {
    'section_num': '一',
    'has_table': True,
    'table_count': 2,
    'key_entities': [
        {'type': 'price', 'value': 'HKD 1.50'}
    ]
}
section_metadata_json = json.dumps(section_metadata, ensure_ascii=False)
```

### 3.2 数据验证

```python
def validate_document_metadata(metadata_str: str) -> bool:
    """验证文档metadata格式"""
    try:
        data = json.loads(metadata_str)
        
        # 必填字段检查
        required = ['rights_ratio', 'processing_version', 'source_system']
        if not all(k in data for k in required):
            return False
        
        # 类型检查
        if not isinstance(data['rights_ratio'], str):
            return False
        
        return True
    except Exception:
        return False

def validate_section_metadata(metadata_str: str) -> bool:
    """验证章节metadata格式"""
    try:
        data = json.loads(metadata_str)
        
        # 必填字段检查
        required = ['section_num', 'has_table', 'table_count']
        if not all(k in data for k in required):
            return False
        
        # 类型检查
        if not isinstance(data['has_table'], bool):
            return False
        if not isinstance(data['table_count'], int):
            return False
        
        return True
    except Exception:
        return False
```

### 3.3 性能优化

```sql
-- 为常用JSON字段创建物化列（可选）
ALTER TABLE documents_v2 
ADD COLUMN rights_ratio String MATERIALIZED JSONExtractString(metadata, 'rights_ratio');

ALTER TABLE documents_v2 
ADD COLUMN processing_version String MATERIALIZED JSONExtractString(metadata, 'processing_version');

-- 为物化列创建索引
ALTER TABLE documents_v2 
ADD INDEX idx_rights_ratio rights_ratio TYPE set GRANULARITY 4;
```

---

## 4. 常见问题

### Q1: metadata为空怎么办？

**A**: 默认值是 `'{}'`（空JSON对象），不会是NULL。如果需要检查：

```sql
SELECT * FROM documents_v2 WHERE metadata = '{}';
```

### Q2: 如何更新metadata？

**A**: 使用ALTER UPDATE：

```sql
ALTER TABLE documents_v2 UPDATE 
    metadata = JSONSet(metadata, 'custom_tags', '["updated"]')
WHERE doc_id = 'xxx';
```

### Q3: JSON嵌套层级限制？

**A**: ClickHouse支持深度嵌套，但建议不超过3层，以保持查询性能。

### Q4: 如何批量导出metadata？

**A**: 

```sql
SELECT 
    doc_id,
    metadata
FROM documents_v2
FORMAT JSONEachRow;
```

---

## 5. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 2.0 | 2025-10-29 | 初始版本，移除向量字段，完善metadata定义 |

---

## 6. 参考资料

- [ClickHouse JSON Functions](https://clickhouse.com/docs/en/sql-reference/functions/json-functions)
- [ClickHouse Data Types](https://clickhouse.com/docs/en/sql-reference/data-types/)

