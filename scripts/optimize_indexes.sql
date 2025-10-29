-- ClickHouse索引优化SQL
-- 用于提升查询性能

-- ====== documents_v2表优化 ======

-- 1. 检查当前索引
-- SHOW CREATE TABLE documents_v2;

-- 2. 为document_type创建跳数索引（加速类型过滤）
ALTER TABLE documents_v2 
  ADD INDEX IF NOT EXISTS doc_type_idx document_type TYPE set(10) GRANULARITY 4;

-- 3. 为company_name创建bloom_filter索引（加速公司名搜索）
ALTER TABLE documents_v2 
  ADD INDEX IF NOT EXISTS company_idx company_name TYPE bloom_filter(0.01) GRANULARITY 4;

-- 4. 为processing_status创建set索引
ALTER TABLE documents_v2 
  ADD INDEX IF NOT EXISTS status_idx processing_status TYPE set(5) GRANULARITY 4;


-- ====== document_sections表优化 ======

-- 5. 为section_type创建跳数索引（最常用查询）
ALTER TABLE document_sections 
  ADD INDEX IF NOT EXISTS section_type_idx section_type TYPE set(20) GRANULARITY 4;

-- 6. 为section_title创建tokenbf_v1索引（全文检索）
ALTER TABLE document_sections 
  ADD INDEX IF NOT EXISTS section_title_idx section_title TYPE tokenbf_v1(30720, 2, 0) GRANULARITY 4;

-- 7. 为content创建ngrambf_v1索引（内容搜索）
-- 注意：这个索引可能比较大，谨慎使用
-- ALTER TABLE document_sections 
--   ADD INDEX IF NOT EXISTS content_idx content TYPE ngrambf_v1(3, 30720, 2, 0) GRANULARITY 4;


-- ====== 投影优化（Projection）======

-- 8. 为常用聚合查询创建投影
ALTER TABLE document_sections 
  ADD PROJECTION IF NOT EXISTS section_stats (
    SELECT 
        section_type,
        count() as cnt,
        avg(char_count) as avg_chars
    GROUP BY section_type
  );

-- 9. 物化投影（可选，会增加存储）
-- ALTER TABLE document_sections MATERIALIZE PROJECTION section_stats;


-- ====== 表优化操作 ======

-- 10. 优化表存储（压缩、去重、合并小分区）
OPTIMIZE TABLE documents_v2 FINAL;
OPTIMIZE TABLE document_sections FINAL;

-- 11. 查看表统计信息
SELECT 
    table,
    formatReadableSize(total_bytes) as size,
    total_rows as rows,
    total_rows / total_bytes as compression_ratio
FROM system.tables
WHERE database = 'hkex_analysis' 
  AND table IN ('documents_v2', 'document_sections')
ORDER BY table;

-- 12. 查看索引使用情况
SELECT 
    table,
    name,
    type,
    expr
FROM system.data_skipping_indices
WHERE database = 'hkex_analysis'
  AND table IN ('documents_v2', 'document_sections')
ORDER BY table, name;


-- ====== 查询性能测试 ======

-- 测试1: 按类型查询（应该使用section_type_idx）
EXPLAIN indexes = 1 
SELECT * FROM document_sections WHERE section_type = 'financials';

-- 测试2: 按股票代码查询（应该使用主键）
EXPLAIN indexes = 1
SELECT * FROM documents_v2 WHERE stock_code = '00328';

-- 测试3: 全文搜索（应该使用section_title_idx）
EXPLAIN indexes = 1
SELECT * FROM document_sections WHERE section_title LIKE '%财务%';


-- ====== 性能基准 ======

-- 基准1: 统计各类型章节数量
SELECT 
    section_type,
    count() as cnt
FROM document_sections
GROUP BY section_type
ORDER BY cnt DESC;

-- 基准2: 查询最近处理的文档
SELECT 
    doc_id,
    stock_code,
    company_name,
    section_count
FROM documents_v2
ORDER BY created_at DESC
LIMIT 10;

-- 基准3: 按公司统计文档数
SELECT 
    company_name,
    count() as doc_count,
    sum(section_count) as total_sections
FROM documents_v2
GROUP BY company_name
ORDER BY doc_count DESC;


-- ====== 清理和维护 ======

-- 清理旧数据（示例：删除30天前的测试数据）
-- DELETE FROM documents_v2 WHERE processing_status = 'failed' AND created_at < now() - INTERVAL 30 DAY;

-- 重建表统计信息
-- ANALYZE TABLE documents_v2;
-- ANALYZE TABLE document_sections;


-- ====== 使用建议 ======

/*
1. 索引维护：
   - 定期运行 OPTIMIZE TABLE 压缩数据
   - 监控索引大小和查询性能
   - 根据实际查询模式调整索引

2. 查询优化：
   - 使用EXPLAIN查看执行计划
   - 优先使用主键和排序键过滤
   - 避免SELECT *，只查询需要的列

3. 性能监控：
   - 查看system.query_log分析慢查询
   - 监控磁盘使用和压缩率
   - 定期检查索引使用情况

4. 数据管理：
   - 设置数据保留策略
   - 定期清理失败记录
   - 备份重要数据
*/

