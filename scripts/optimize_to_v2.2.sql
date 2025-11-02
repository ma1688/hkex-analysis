-- ============================================================================
-- V2.1 → V2.2 表结构精简优化脚本
-- 删除冗余和不必要的字段，提升性能和可维护性
-- 执行日期：2025-11-02
-- ============================================================================

USE hkex_analysis;

-- ============================================================================
-- Step 1: 备份现有表（安全起见）
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents_v2_backup AS documents_v2;
CREATE TABLE IF NOT EXISTS document_sections_backup AS document_sections;

SELECT '备份完成' AS status;

-- ============================================================================
-- Step 2: documents_v2 表 - 删除7个字段
-- ============================================================================

-- 删除1: title（与file_path重复，可从file_path提取）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS title;

-- 删除2: document_subtype（使用频率低，可放metadata）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS document_subtype;

-- 删除3: processing_date（可用created_at替代）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS processing_date;

-- 删除4: file_size（非核心字段，实际查询很少用）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS file_size;

-- 删除5: processing_status（可用created_at判断，或放metadata）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS processing_status;

-- 删除6: error_message（应该在日志中记录，不应在业务表中）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS error_message;

-- 删除7: section_count（可从document_sections表COUNT得出）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS section_count;

-- 删除8: total_chars（可从document_sections表SUM得出）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS total_chars;

-- 删除9: updated_at（很少更新，不必要）
ALTER TABLE documents_v2 DROP COLUMN IF EXISTS updated_at;

-- 注意：保留 company_name 字段（用户要求）

SELECT 'documents_v2 删除9个字段完成' AS status;

-- ============================================================================
-- Step 3: document_sections 表 - 删除7个字段
-- ============================================================================

-- 删除1: document_type（冗余，可通过doc_id关联documents_v2得到）
ALTER TABLE document_sections DROP COLUMN IF EXISTS document_type;

-- 删除2: section_subtype（使用频率极低，可放metadata）
ALTER TABLE document_sections DROP COLUMN IF EXISTS section_subtype;

-- 删除3: content_hash（去重功能可在应用层实现）
ALTER TABLE document_sections DROP COLUMN IF EXISTS content_hash;

-- 删除4: char_count（可实时计算 LENGTH(content)）
ALTER TABLE document_sections DROP COLUMN IF EXISTS char_count;

-- 删除5: word_count（几乎不用，可实时计算）
ALTER TABLE document_sections DROP COLUMN IF EXISTS word_count;

-- 删除6: importance（与priority重复）
ALTER TABLE document_sections DROP COLUMN IF EXISTS importance;

-- 删除7: confidence（识别置信度，实际不用）
ALTER TABLE document_sections DROP COLUMN IF EXISTS confidence;

-- 删除8: identification_method（技术元数据，非业务字段）
ALTER TABLE document_sections DROP COLUMN IF EXISTS identification_method;

SELECT 'document_sections 删除7个字段完成' AS status;

-- ============================================================================
-- Step 4: 验证优化结果
-- ============================================================================

SELECT '=== 优化后表结构 ===' AS info
UNION ALL
SELECT 'documents_v2: ' || toString(count()) || '个字段' AS info 
FROM system.columns 
WHERE database = 'hkex_analysis' AND table = 'documents_v2'
UNION ALL
SELECT 'document_sections: ' || toString(count()) || '个字段' AS info 
FROM system.columns 
WHERE database = 'hkex_analysis' AND table = 'document_sections'
UNION ALL
SELECT '备份表: documents_v2_backup, document_sections_backup' AS info
FORMAT Pretty;

-- ============================================================================
-- 回滚说明（如需恢复）
-- ============================================================================
-- 如果优化后发现问题，可以使用备份表恢复：
-- 
-- DROP TABLE documents_v2;
-- DROP TABLE document_sections;
-- RENAME TABLE documents_v2_backup TO documents_v2;
-- RENAME TABLE document_sections_backup TO document_sections;
--
-- ============================================================================
-- 删除备份表（确认优化无误后执行）
-- ============================================================================
-- DROP TABLE IF EXISTS documents_v2_backup;
-- DROP TABLE IF EXISTS document_sections_backup;
-- ============================================================================

