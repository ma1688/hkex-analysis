-- ============================================================================
-- 数据库迁移脚本：从V2.0（带向量）迁移到V2.0 Final（无向量）
-- 执行日期：2025-10-29
-- 警告：此脚本会删除并重建表，请先备份数据！
-- ============================================================================

-- ============================================================================
-- 使用说明
-- ============================================================================
-- 1. 备份现有数据（重要！）
--    clickhouse-client --query="SELECT * FROM documents_v2 FORMAT Native" > documents_v2_backup.native
--    clickhouse-client --query="SELECT * FROM document_sections FORMAT Native" > document_sections_backup.native
--
-- 2. 执行迁移
--    clickhouse-client --host 1.14.239.79 --port 9000 -d hkex_analysis < migrate_to_v2_final.sql
--
-- 3. 验证数据（见底部查询）
-- ============================================================================

USE hkex_analysis;

-- ============================================================================
-- 步骤1：删除旧表（谨慎操作！）
-- ============================================================================
-- 注意：如果有数据，建议先导出备份

-- 删除实体表
DROP TABLE IF EXISTS section_entities;

-- 删除章节表
DROP TABLE IF EXISTS document_sections;

-- 删除文档表
DROP TABLE IF EXISTS documents_v2;

-- ============================================================================
-- 步骤2：创建新表（无向量版本）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 文档元信息表
-- ----------------------------------------------------------------------------
CREATE TABLE documents_v2 (
    -- 主键字段
    doc_id String COMMENT '文档唯一ID，格式：{stock_code}_{timestamp}_{random}',
    
    -- 基本信息
    title String COMMENT '文档标题（通常是文件名）',
    stock_code LowCardinality(String) COMMENT '股票代码（如：00328）',
    company_name String DEFAULT '' COMMENT '公司名称（从文件名提取）',
    
    -- 分类信息
    document_type LowCardinality(String) COMMENT '文档类型：rights/placing/ipo/consolidation',
    document_subtype LowCardinality(String) DEFAULT '' COMMENT '子类型：underwritten/non-underwritten',
    
    -- 时间信息
    announcement_date Date COMMENT '公告发布日期（从文件名提取）',
    processing_date DateTime DEFAULT now() COMMENT '处理时间',
    
    -- 文件信息
    file_path String COMMENT '文件路径',
    file_size UInt64 DEFAULT 0 COMMENT '文件大小（字节）',
    page_count UInt32 DEFAULT 0 COMMENT 'PDF总页数',
    
    -- 处理状态
    processing_status LowCardinality(String) DEFAULT 'pending' COMMENT '处理状态：pending/processing/completed/failed',
    error_message String DEFAULT '' COMMENT '错误信息（失败时记录）',
    
    -- 统计信息
    section_count UInt32 DEFAULT 0 COMMENT '章节总数',
    total_chars UInt64 DEFAULT 0 COMMENT '总字符数',
    
    -- 扩展字段（JSON格式）
    -- 示例：{"rights_ratio":"1:4","processing_version":"2.0","source_system":"hkex"}
    metadata String DEFAULT '{}' COMMENT 'JSON扩展信息（见METADATA_SCHEMA.md）',
    
    -- 时间戳
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
    
) ENGINE = MergeTree()
ORDER BY (stock_code, announcement_date, doc_id)
PRIMARY KEY (stock_code, announcement_date, doc_id)
COMMENT '文档元信息表V2.0 Final - 无向量版本';

-- 添加索引
ALTER TABLE documents_v2 ADD INDEX idx_document_type document_type TYPE set GRANULARITY 4;
ALTER TABLE documents_v2 ADD INDEX idx_status processing_status TYPE set GRANULARITY 4;
ALTER TABLE documents_v2 ADD INDEX idx_company_name company_name TYPE bloom_filter GRANULARITY 4;

-- ----------------------------------------------------------------------------
-- 2. 文档章节表
-- ----------------------------------------------------------------------------
CREATE TABLE document_sections (
    -- 主键字段
    section_id String COMMENT '章节唯一ID（UUID）',
    doc_id String COMMENT '关联文档ID（外键）',
    
    -- 分类信息
    document_type LowCardinality(String) COMMENT '文档类型（冗余字段，加速查询）',
    section_type LowCardinality(String) COMMENT '章节类型：terms/timetable/financials等',
    section_subtype LowCardinality(String) DEFAULT '' COMMENT '章节子类型（预留）',
    
    -- 章节结构
    section_title String COMMENT '章节标题',
    section_index UInt32 COMMENT '章节序号（从0开始）',
    page_start UInt32 COMMENT '起始页码',
    page_end UInt32 COMMENT '结束页码',
    
    -- 内容字段
    content String COMMENT '章节文本内容',
    content_hash String DEFAULT '' COMMENT '内容哈希（用于去重检测）',
    
    -- 统计信息
    char_count UInt32 COMMENT '字符数',
    word_count UInt32 DEFAULT 0 COMMENT '词数（可选）',
    
    -- 优先级信息
    priority UInt8 DEFAULT 1 COMMENT '优先级：1-5（1=最高，对应section_level）',
    importance LowCardinality(String) DEFAULT 'normal' COMMENT '重要性：critical/high/normal/low',
    confidence Float32 DEFAULT 1.0 COMMENT '识别置信度（0-1）',
    identification_method LowCardinality(String) DEFAULT 'unknown' COMMENT '识别方法：regex/rule/manual',
    
    -- 扩展字段（JSON格式）
    -- 示例：{"section_num":"一","has_table":false,"table_count":0}
    metadata String DEFAULT '{}' COMMENT 'JSON扩展信息（见METADATA_SCHEMA.md）',
    
    -- 时间戳
    created_at DateTime DEFAULT now() COMMENT '创建时间'
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_index)
PRIMARY KEY (doc_id, section_index)
COMMENT '文档章节表V2.0 Final - 无向量版本';

-- 添加索引（性能优化）
ALTER TABLE document_sections ADD INDEX idx_section_type section_type TYPE set GRANULARITY 4;
ALTER TABLE document_sections ADD INDEX idx_title section_title TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 4;
ALTER TABLE document_sections ADD INDEX idx_importance importance TYPE set GRANULARITY 4;

-- 添加投影（加速聚合查询）
ALTER TABLE document_sections ADD PROJECTION section_stats (
    SELECT 
        section_type,
        importance,
        count() AS cnt,
        sum(char_count) AS total_chars
    GROUP BY section_type, importance
);

-- ----------------------------------------------------------------------------
-- 3. 章节实体提取表
-- ----------------------------------------------------------------------------
CREATE TABLE section_entities (
    -- 主键字段
    entity_id String COMMENT '实体唯一ID（UUID）',
    section_id String COMMENT '关联章节ID（外键）',
    doc_id String COMMENT '关联文档ID（冗余，加速查询）',
    
    -- 实体信息
    entity_type LowCardinality(String) COMMENT '实体类型：price/ratio/date/money等',
    entity_value String COMMENT '实体值',
    entity_unit String DEFAULT '' COMMENT '单位（如：HKD, %, 股）',
    
    -- 上下文信息
    context String DEFAULT '' COMMENT '实体上下文（前后文）',
    position UInt32 DEFAULT 0 COMMENT '在章节中的位置（字符偏移量）',
    
    -- 置信度信息
    confidence Float32 DEFAULT 1.0 COMMENT '提取置信度（0-1）',
    extraction_method LowCardinality(String) DEFAULT 'regex' COMMENT '提取方法：regex/ner/rule',
    
    -- 时间戳
    created_at DateTime DEFAULT now() COMMENT '创建时间'
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_id, entity_type)
PRIMARY KEY (doc_id, section_id, entity_type)
COMMENT '章节实体提取表V2.0 Final';

-- 添加索引
ALTER TABLE section_entities ADD INDEX idx_entity_type entity_type TYPE set GRANULARITY 4;
ALTER TABLE section_entities ADD INDEX idx_entity_value entity_value TYPE bloom_filter GRANULARITY 4;

-- ============================================================================
-- 步骤3：验证表结构
-- ============================================================================

-- 查看表列表
SHOW TABLES;

-- 查看表结构
DESCRIBE documents_v2;
DESCRIBE document_sections;
DESCRIBE section_entities;

-- 查看索引
SELECT 
    table,
    name,
    type,
    expr
FROM system.data_skipping_indices
WHERE database = 'hkex_analysis'
  AND table IN ('documents_v2', 'document_sections', 'section_entities')
ORDER BY table, name;

-- ============================================================================
-- 步骤4：测试查询（迁移后执行）
-- ============================================================================

-- 测试1：查看表数据量
SELECT 
    'documents_v2' AS table_name,
    count() AS row_count,
    formatReadableSize(sum(bytes)) AS size
FROM documents_v2
UNION ALL
SELECT 
    'document_sections' AS table_name,
    count() AS row_count,
    formatReadableSize(sum(bytes)) AS size
FROM document_sections
UNION ALL
SELECT 
    'section_entities' AS table_name,
    count() AS row_count,
    formatReadableSize(sum(bytes)) AS size
FROM section_entities;

-- 测试2：验证metadata字段
SELECT 
    doc_id,
    metadata,
    JSONExtractString(metadata, 'rights_ratio') AS rights_ratio,
    JSONExtractString(metadata, 'processing_version') AS version
FROM documents_v2
LIMIT 5;

-- 测试3：章节类型分布
SELECT 
    section_type,
    count() AS cnt,
    round(avg(char_count), 0) AS avg_chars
FROM document_sections
GROUP BY section_type
ORDER BY cnt DESC;

-- ============================================================================
-- 迁移完成检查清单
-- ============================================================================
-- ✅ 1. 表已创建（documents_v2, document_sections, section_entities）
-- ✅ 2. 索引已添加（见system.data_skipping_indices）
-- ✅ 3. 投影已创建（section_stats）
-- ✅ 4. metadata字段可正常查询
-- ✅ 5. 无embedding相关字段
-- ============================================================================

