-- ============================================================================
-- ClickHouse 表结构迁移脚本：V2.0 → V2.1
-- 用途：在现有 documents_v2 表上新增3个分类字段
-- 执行时间：< 1秒（无需迁移数据）
-- 创建日期：2025-11-02
-- ============================================================================

USE hkex_analysis;

-- ============================================================================
-- Step 1: 新增3个分类字段
-- ============================================================================

-- 新增：公告标题
ALTER TABLE documents_v2 ADD COLUMN IF NOT EXISTS 
    announcement_title String DEFAULT '' 
    COMMENT '公告实际标题（从文件名提取）';

-- 新增：文档主分类
ALTER TABLE documents_v2 ADD COLUMN IF NOT EXISTS 
    document_category LowCardinality(String) DEFAULT '' 
    COMMENT '文档主分类：公告及通告/通函/上市文件等';

-- 新增：公告子分类
ALTER TABLE documents_v2 ADD COLUMN IF NOT EXISTS 
    announcement_category LowCardinality(String) DEFAULT '' 
    COMMENT '公告子分类：更換董事/資本重組等';

-- ============================================================================
-- Step 2: 添加索引（提升查询性能）
-- ============================================================================

-- 索引1：文档主分类（set类型，适合枚举值）
ALTER TABLE documents_v2 ADD INDEX IF NOT EXISTS 
    idx_doc_category document_category TYPE set GRANULARITY 4;

-- 索引2：公告子分类（set类型，适合枚举值）
ALTER TABLE documents_v2 ADD INDEX IF NOT EXISTS 
    idx_ann_category announcement_category TYPE set GRANULARITY 4;

-- 索引3：公告标题（tokenbf_v1，支持全文检索）
ALTER TABLE documents_v2 ADD INDEX IF NOT EXISTS 
    idx_ann_title announcement_title TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4;

-- ============================================================================
-- Step 3: 验证修改
-- ============================================================================

-- 查看表结构
SELECT '=== 表结构（新增字段）===' AS message;
SELECT name, type, default_expression, comment
FROM system.columns
WHERE database = 'hkex_analysis' 
  AND table = 'documents_v2'
  AND name IN ('announcement_title', 'document_category', 'announcement_category')
ORDER BY position;

-- 查看索引
SELECT '=== 索引列表（新增索引）===' AS message;
SELECT name, type, expr
FROM system.data_skipping_indices
WHERE database = 'hkex_analysis' 
  AND table = 'documents_v2'
  AND name IN ('idx_doc_category', 'idx_ann_category', 'idx_ann_title')
ORDER BY name;

-- 统计现有数据（新字段应为空）
SELECT '=== 现有数据统计 ===' AS message;
SELECT 
    count() AS total_rows,
    countIf(announcement_title != '') AS filled_title,
    countIf(document_category != '') AS filled_doc_cat,
    countIf(announcement_category != '') AS filled_ann_cat
FROM documents_v2;

-- 显示完成信息
SELECT '=== 迁移完成 ===' AS message;
SELECT 
    'V2.0 → V2.1 迁移完成' AS status,
    '新增3个字段 + 3个索引' AS changes,
    now() AS completed_at;

-- ============================================================================
-- 使用说明
-- ============================================================================
-- 
-- 执行方式1：在ClickHouse客户端中执行
-- clickhouse-client --multiquery < migrate_v2.0_to_v2.1.sql
--
-- 执行方式2：通过Docker执行
-- docker exec -i clickhouse-server clickhouse-client --multiquery < migrate_v2.0_to_v2.1.sql
--
-- 执行方式3：在ClickHouse客户端交互模式
-- clickhouse-client
-- USE hkex_analysis;
-- SOURCE migrate_v2.0_to_v2.1.sql;
--
-- ============================================================================
-- 回滚说明（如需）
-- ============================================================================
--
-- 删除新增字段（慎用！）：
-- ALTER TABLE documents_v2 DROP COLUMN announcement_title;
-- ALTER TABLE documents_v2 DROP COLUMN document_category;
-- ALTER TABLE documents_v2 DROP COLUMN announcement_category;
--
-- 删除新增索引：
-- ALTER TABLE documents_v2 DROP INDEX idx_doc_category;
-- ALTER TABLE documents_v2 DROP INDEX idx_ann_category;
-- ALTER TABLE documents_v2 DROP INDEX idx_ann_title;
--
-- ============================================================================

