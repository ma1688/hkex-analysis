-- ============================================================================
-- ClickHouse 数据库初始化脚本
-- 用于港股公告分析系统
-- 创建日期：2025-11-02
-- ============================================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS hkex_analysis;

-- 使用数据库
USE hkex_analysis;

-- 显示数据库信息
SELECT 'Database hkex_analysis created successfully' AS message;

