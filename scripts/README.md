# Scripts 目录说明

**最后更新**: 2025-11-02  
**当前版本**: V2.2  

---

## 📁 目录结构

```
scripts/
├── README.md                          # 本文件
├── chunk_pdf_by_sections.py           # 【核心】PDF切块导入脚本 (V2.2)
├── document_filter_configurable.py    # 【配置化】文档过滤工具
├── cleanup_duplicates.py              # 【工具】去重清理脚本
├── optimize_to_v2.2.sql               # 【迁移】V2.1→V2.2优化脚本
├── optimize_indexes.sql               # 【优化】索引优化脚本
├── test_interrupt_*.py                # 【测试】中断响应测试
└── archive/                           # 归档目录
    ├── v2.0/                          # V2.0版本归档
    ├── v2.1/                          # V2.1版本归档
    └── old_docs/                      # 旧文档归档
```

---

## 🚀 核心脚本

### 1. chunk_pdf_by_sections.py
**功能**: PDF文档切块导入ClickHouse  
**版本**: V2.2（精简优化版）  
**用途**: 将PDF文档按章节切块，提取元数据和内容，导入到 `documents_v2` 和 `document_sections` 表

**使用方法**:
```bash
# 单个文件
python chunk_pdf_by_sections.py /path/to/file.pdf

# 批量处理目录
python chunk_pdf_by_sections.py /path/to/directory/
```

**特性**:
- ✅ 自动提取分类字段（`document_category`, `announcement_category`）
- ✅ 从文件名提取公告标题、股票代码、公司名称
- ✅ 支持断点续传（跳过已处理文档）
- ✅ 匹配V2.2精简表结构（11+13字段）

**配置**:
- ClickHouse连接: 读取环境变量 `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`
- 默认连接: `localhost:9000`

---

### 2. document_filter_configurable.py
**功能**: 可配置的文档过滤工具  
**版本**: 配置驱动版  
**用途**: 根据配置规则过滤和清理文档数据

**使用方法**:
```bash
python document_filter_configurable.py
```

**特性**:
- ✅ 从 `config/document_filter.yaml` 读取过滤规则
- ✅ 支持多种过滤条件（文件类型、大小、关键词等）
- ✅ 批量处理，性能优化

**配置文件**: `config/document_filter.yaml`

---

## 🛠️ 工具脚本

### 3. cleanup_duplicates.py
**功能**: 清理重复数据  
**用途**: 检测并删除 `documents_v2` 和 `document_sections` 表中的重复记录

**使用方法**:
```bash
python cleanup_duplicates.py
```

**特性**:
- ✅ 基于 `file_path` 检测重复文档
- ✅ 基于 `content_hash` 检测重复章节
- ✅ 安全删除，保留最新记录

---

## 📊 SQL脚本

### 4. optimize_to_v2.2.sql
**功能**: V2.1 → V2.2 优化迁移脚本  
**用途**: 将现有V2.1数据库升级到V2.2精简版

**使用方法**:
```bash
docker exec clickhouse_hkex clickhouse-client < scripts/optimize_to_v2.2.sql
```

**操作**:
1. 备份现有表（`documents_v2_backup`, `document_sections_backup`）
2. 删除9个冗余字段（`documents_v2`）
3. 删除7个冗余字段（`document_sections`）

**优化效果**:
- documents_v2: 20字段 → 11字段 (⬇️ 45%)
- document_sections: 20字段 → 13字段 (⬇️ 35%)

---

### 5. optimize_indexes.sql
**功能**: 索引优化脚本  
**用途**: 为高频查询字段添加或优化索引

**使用方法**:
```bash
docker exec clickhouse_hkex clickhouse-client < scripts/optimize_indexes.sql
```

**索引类型**:
- `set`: 用于精确匹配（如 `stock_code`, `document_category`）
- `tokenbf_v1`: 用于全文检索（如 `announcement_title`, `content`）

---

## 🧪 测试脚本

### 6. test_interrupt_*.py
**功能**: CLI中断响应测试  
**用途**: 验证Ctrl+C和ESC键的快速响应

**使用方法**:
```bash
# 单元测试
python test_interrupt_unit.py

# 集成测试
python test_interrupt_integration.py

# Shell脚本测试
bash test_interrupt_response.sh
```

---

## 📦 归档目录

### archive/v2.0/
**内容**: V2.0版本相关文件
- `create_tables_v2_final.sql` - V2.0表结构定义
- `migrate_to_v2_final.sql` - V2.0迁移脚本

### archive/v2.1/
**内容**: V2.1版本相关文件
- `migrate_v2.0_to_v2.1.sql` - V2.0→V2.1迁移脚本

### archive/old_docs/
**内容**: 旧文档和废弃脚本
- `document_filter.py` - 旧版过滤脚本（已被配置化版本替代）
- `FINAL_REPORT.md` - 旧项目报告
- `INDEX.md` - 旧索引文件
- `METADATA_SCHEMA.md` - 旧元数据模式文档

---

## 🎯 快速开始

### 新用户（从头开始）
1. 启动ClickHouse: `cd ../docker && ./docker-up.sh`
2. 创建表结构: 自动创建（通过 `docker/clickhouse/init/02-create-tables-v2.2-final.sql`）
3. 导入PDF: `python chunk_pdf_by_sections.py /path/to/pdf`

### 现有V2.1用户（升级到V2.2）
1. 备份数据: 执行 `optimize_to_v2.2.sql` 会自动备份
2. 执行优化: `docker exec clickhouse_hkex clickhouse-client < scripts/optimize_to_v2.2.sql`
3. 验证表结构: `docker exec clickhouse_hkex clickhouse-client --query "DESC hkex_analysis.documents_v2"`

---

## 📖 相关文档

- **V2.2完整报告**: `docs/执行报告/2025-11-02_V2.2表结构精简优化_最终报告.md`
- **V2.2快速指南**: `QUICKSTART_V2.2.md`
- **ClickHouse快速启动**: `CLICKHOUSE_QUICK_START.md`
- **表结构定义**: `docker/clickhouse/init/02-create-tables-v2.2-final.sql`

---

## ⚠️ 注意事项

1. **备份**: 执行优化脚本前，会自动创建备份表
2. **兼容性**: V2.2脚本仅适用于V2.2表结构，使用前请确认版本
3. **性能**: 大批量导入建议在低峰期执行
4. **测试**: 生产环境前请在测试环境验证

---

## 🔧 故障排查

### 问题1: ClickHouse连接失败
```bash
# 检查ClickHouse状态
docker exec clickhouse_hkex clickhouse-client --query "SELECT 1"

# 重启ClickHouse
cd ../docker && ./docker-down.sh && ./docker-up.sh
```

### 问题2: 导入失败（表结构不匹配）
```bash
# 检查表结构
docker exec clickhouse_hkex clickhouse-client --query "DESC hkex_analysis.documents_v2"

# 如需重建表
docker exec clickhouse_hkex clickhouse-client < ../docker/clickhouse/init/02-create-tables-v2.2-final.sql
```

### 问题3: 如何回滚到V2.1？
```sql
-- 从备份恢复
DROP TABLE documents_v2;
CREATE TABLE documents_v2 AS documents_v2_backup;

DROP TABLE document_sections;
CREATE TABLE document_sections AS document_sections_backup;
```

---

**维护者**: AI Assistant  
**项目**: HKEX Analysis System  
**版本**: V2.2  
**最后更新**: 2025-11-02

