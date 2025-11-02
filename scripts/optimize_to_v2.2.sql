-- ============================================================================
-- ClickHouse V2.2 表结构创建脚本（精简优化版）
-- 用途：全新创建港股公告分析系统的V2.2表结构
-- 创建日期：2025-11-02
-- 说明：不涉及数据迁移，直接创建优化后的表结构
-- ============================================================================

-- 确保使用正确的数据库
USE hkex_analysis;

-- ============================================================================
-- 1. 删除旧表（如果存在）
-- ============================================================================
-- 注意：此操作会删除所有数据，请在执行前确保已备份
-- 如不需要删除旧表，可注释掉此部分

-- DROP TABLE IF EXISTS documents_v2;
-- DROP TABLE IF EXISTS document_sections;

SELECT '⚠️  如需删除旧表，请取消注释DROP TABLE语句' AS warning;

-- ============================================================================
-- 2. 创建 documents_v2 表（文档元信息）
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents_v2 (
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 主键字段
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    doc_id String COMMENT '文档唯一ID，格式：{stock_code}_{timestamp}_{random}，用于全局唯一标识文档',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 基本信息字段
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    announcement_title String DEFAULT '' COMMENT '公告实际标题，从文件名提取，如：ALCO HOLDINGS 供股章程',
    
    stock_code LowCardinality(String) COMMENT '港股股票代码，格式：5位数字（如00328），LowCardinality优化存储',
    
    company_name String DEFAULT '' COMMENT '公司名称，从文件名提取，如：ALCO HOLDINGS（用户要求保留此字段）',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 两级分类系统
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    document_category LowCardinality(String) DEFAULT '' COMMENT '文档主分类（一级目录），如：供股/配售/上市文件/公告及通告/财务报表等',
    
    announcement_category LowCardinality(String) DEFAULT '' COMMENT '公告子分类（二级目录），如：公告及通告/通函/月报表等',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 时间信息
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    announcement_date Date COMMENT '公告发布日期，从文件名提取，格式：YYYY-MM-DD',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 文件信息
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    file_path String COMMENT 'PDF文件的完整路径，用于定位原始文件',
    
    page_count UInt32 DEFAULT 0 COMMENT 'PDF总页数，由PyMuPDF解析得出',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 扩展字段（JSON格式）
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    metadata String DEFAULT '{}' COMMENT 'JSON格式的扩展信息，包含：document_subtype(underwritten/non-underwritten), section_count(章节数), rights_ratio(供股比例), processing_version(处理版本), source_system(来源系统)等',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 时间戳
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    created_at DateTime DEFAULT now() COMMENT '记录创建时间，自动生成'
    
) ENGINE = MergeTree()
ORDER BY (stock_code, announcement_date, doc_id)
PRIMARY KEY (stock_code, announcement_date, doc_id)
COMMENT '文档元信息表V2.2 - 精简优化版，包含11个核心字段，删除冗余字段提升性能';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 索引说明
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. PRIMARY KEY (stock_code, announcement_date, doc_id):
--    - 按股票代码 → 日期 → 文档ID排序，加速常见查询
-- 2. LowCardinality字段 (stock_code, document_category, announcement_category):
--    - 自动优化查询性能，无需额外索引
-- 3. 可选索引 (需通过optimize_indexes.sql添加):
--    - announcement_title: tokenbf_v1全文检索索引
--    - company_name: set精确匹配索引（可选）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SELECT '✅ documents_v2 表创建完成（11个字段）' AS status;

-- ============================================================================
-- 3. 创建 document_sections 表（文档章节切块）
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_sections (
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 主键字段
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    section_id String COMMENT '章节唯一ID（UUID），全局唯一标识每个章节',
    
    doc_id String COMMENT '关联文档ID（外键），指向documents_v2.doc_id',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 分类信息（冗余字段，加速查询，避免JOIN）
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    document_category LowCardinality(String) DEFAULT '' COMMENT '文档主分类（冗余），从documents_v2复制，加速直接查询章节时的分类过滤',
    
    announcement_category LowCardinality(String) DEFAULT '' COMMENT '公告子分类（冗余），从documents_v2复制，加速直接查询章节时的分类过滤',
    
    section_type LowCardinality(String) COMMENT '章节类型，如：introduction(引言)/terms(条款)/procedures(程序)/financial(财务)/risk(风险)/appendix(附录)等（用户要求保留此字段）',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 章节结构信息
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    section_title String COMMENT '章节标题，从PDF提取，如：一、供股详情',
    
    section_index UInt32 COMMENT '章节序号，从0开始，表示章节在文档中的顺序',
    
    page_start UInt32 COMMENT '章节起始页码（从1开始）',
    
    page_end UInt32 COMMENT '章节结束页码（包含）',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 内容字段
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    content String COMMENT '章节文本内容，从PDF提取的纯文本',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 优先级信息
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    priority UInt8 DEFAULT 1 COMMENT '章节优先级：1(最高)-5(最低)，用于标识章节的重要程度',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 扩展字段（JSON格式）
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    metadata String DEFAULT '{}' COMMENT 'JSON格式的扩展信息，包含：section_num(章节编号), has_table(是否包含表格), table_count(表格数量)等',
    
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    -- 时间戳
    -- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    created_at DateTime DEFAULT now() COMMENT '记录创建时间，自动生成'
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_index)
PRIMARY KEY (doc_id, section_index)
COMMENT '文档章节切块表V2.2 - 精简优化版，包含13个核心字段，每个章节对应一条记录';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 索引说明
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. PRIMARY KEY (doc_id, section_index):
--    - 按文档ID → 章节序号排序，加速章节顺序查询
-- 2. LowCardinality字段 (document_category, announcement_category, section_type):
--    - 自动优化查询性能，无需额外索引
-- 3. 冗余字段 (document_category, announcement_category):
--    - 避免频繁JOIN，提升查询性能
-- 4. 可选索引 (需通过optimize_indexes.sql添加):
--    - section_title: tokenbf_v1全文检索索引
--    - content: tokenbf_v1全文检索索引（大字段，谨慎添加）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SELECT '✅ document_sections 表创建完成（13个字段）' AS status;

-- ============================================================================
-- 4. 验证表结构
-- ============================================================================

-- 显示创建的表
SELECT 
    '=== 创建的表列表 ===' AS info
UNION ALL
SELECT 
    name || ' (引擎: ' || engine || ', 行数: ' || toString(total_rows) || ')' AS info
FROM system.tables 
WHERE database = 'hkex_analysis' 
  AND name IN ('documents_v2', 'document_sections')
ORDER BY name
FORMAT Pretty;

-- 显示 documents_v2 字段详情
SELECT 
    '=== documents_v2 字段详情 ===' AS title
UNION ALL
SELECT 
    toString(position) || '. ' || name || ' (' || type || ') - ' || comment AS field_info
FROM system.columns 
WHERE database = 'hkex_analysis' AND table = 'documents_v2'
ORDER BY position
FORMAT Pretty;

-- 显示 document_sections 字段详情
SELECT 
    '=== document_sections 字段详情 ===' AS title
UNION ALL
SELECT 
    toString(position) || '. ' || name || ' (' || type || ') - ' || comment AS field_info
FROM system.columns 
WHERE database = 'hkex_analysis' AND table = 'document_sections'
ORDER BY position
FORMAT Pretty;

-- ============================================================================
-- 5. 优化建议
-- ============================================================================

SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' AS separator;
SELECT '📊 V2.2 表结构优化总结' AS title;
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' AS separator;
SELECT '' AS blank;
SELECT '✅ documents_v2: 11个核心字段' AS info;
SELECT '   - 主键: doc_id' AS info;
SELECT '   - 核心业务字段: announcement_title, stock_code, company_name' AS info;
SELECT '   - 两级分类: document_category, announcement_category' AS info;
SELECT '   - 时间: announcement_date, created_at' AS info;
SELECT '   - 文件信息: file_path, page_count' AS info;
SELECT '   - 扩展: metadata (JSON)' AS info;
SELECT '' AS blank;
SELECT '✅ document_sections: 13个核心字段' AS info;
SELECT '   - 主键: section_id, doc_id' AS info;
SELECT '   - 冗余分类: document_category, announcement_category' AS info;
SELECT '   - 章节信息: section_type, section_title, section_index' AS info;
SELECT '   - 页码: page_start, page_end' AS info;
SELECT '   - 内容: content' AS info;
SELECT '   - 优先级: priority' AS info;
SELECT '   - 扩展: metadata (JSON), created_at' AS info;
SELECT '' AS blank;
SELECT '📈 性能优化效果（相比V2.1）:' AS info;
SELECT '   - documents_v2: 20字段 → 11字段 (⬇️ 45%)' AS info;
SELECT '   - document_sections: 20字段 → 13字段 (⬇️ 35%)' AS info;
SELECT '   - 预计存储空间减少: 30-40%' AS info;
SELECT '   - 预计INSERT性能提升: 20-30%' AS info;
SELECT '   - 预计SELECT性能提升: 15-25%' AS info;
SELECT '' AS blank;
SELECT '🎯 下一步操作:' AS info;
SELECT '   1. 导入数据: python scripts/chunk_pdf_by_sections.py <pdf_path>' AS info;
SELECT '   2. 添加索引: clickhouse-client < scripts/optimize_indexes.sql' AS info;
SELECT '   3. 验证数据: SELECT count() FROM documents_v2;' AS info;
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' AS separator;

-- ============================================================================
-- 6. 常用查询示例
-- ============================================================================

-- 6.1 查询特定股票的所有文档
-- SELECT 
--     doc_id,
--     announcement_title,
--     announcement_date,
--     document_category,
--     announcement_category
-- FROM documents_v2
-- WHERE stock_code = '00328'
-- ORDER BY announcement_date DESC
-- LIMIT 10;

-- 6.2 查询特定分类的文档
-- SELECT 
--     stock_code,
--     company_name,
--     announcement_title,
--     announcement_date
-- FROM documents_v2
-- WHERE document_category = '供股'
--   AND announcement_date >= '2024-01-01'
-- ORDER BY announcement_date DESC;

-- 6.3 查询特定文档的所有章节
-- SELECT 
--     section_title,
--     section_type,
--     priority,
--     LENGTH(content) as content_length
-- FROM document_sections
-- WHERE doc_id = 'xxx'
-- ORDER BY section_index;

-- 6.4 统计各分类的文档数量
-- SELECT 
--     document_category,
--     announcement_category,
--     count() as doc_count,
--     sum(page_count) as total_pages
-- FROM documents_v2
-- GROUP BY document_category, announcement_category
-- ORDER BY doc_count DESC;

-- ============================================================================
-- 完成提示
-- ============================================================================

SELECT '✅ V2.2 表结构创建完成！' AS final_status;
SELECT '📖 详细说明请查看: docs/执行报告/2025-11-02_V2.2表结构精简优化_最终报告.md' AS documentation;
