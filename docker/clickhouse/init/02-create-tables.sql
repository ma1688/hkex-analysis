-- ============================================================================
-- ClickHouse V2.0 表结构（完全移除向量版本）
-- 用于港股公告文档按章节切块存储
-- 创建日期：2025-11-02
-- ============================================================================

USE hkex_analysis;

-- ============================================================================
-- 1. 文档元信息表 (documents_v2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents_v2 (
    -- 主键字段
    doc_id String,                                  -- 文档唯一ID，格式：{stock_code}_{timestamp}_{random}
    
    -- 基本信息
    title String,                                   -- 文档标题（通常是文件名）
    stock_code LowCardinality(String),              -- 股票代码（如：00328）
    company_name String DEFAULT '',                 -- 公司名称（从文件名提取）
    
    -- 分类信息
    document_type LowCardinality(String),           -- 文档类型：rights/placing/ipo/consolidation
    document_subtype LowCardinality(String) DEFAULT '', -- 子类型：underwritten/non-underwritten
    
    -- 时间信息
    announcement_date Date,                         -- 公告发布日期（从文件名提取）
    processing_date DateTime DEFAULT now(),         -- 处理时间
    
    -- 文件信息
    file_path String,                               -- 文件路径
    file_size UInt64 DEFAULT 0,                     -- 文件大小（字节）
    page_count UInt32 DEFAULT 0,                    -- PDF总页数
    
    -- 处理状态
    processing_status LowCardinality(String) DEFAULT 'pending',  -- 处理状态：pending/processing/completed/failed
    error_message String DEFAULT '',                -- 错误信息（失败时记录）
    
    -- 统计信息
    section_count UInt32 DEFAULT 0,                 -- 章节总数
    total_chars UInt64 DEFAULT 0,                   -- 总字符数
    
    -- 扩展字段
    metadata String DEFAULT '{}',                   -- JSON格式的扩展信息
    
    -- 时间戳
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
    
) ENGINE = MergeTree()
ORDER BY (stock_code, announcement_date, doc_id)
PRIMARY KEY (stock_code, announcement_date, doc_id)
COMMENT '文档元信息表V2.0 - 存储PDF文档的元数据，一个PDF对应一条记录';

-- ============================================================================
-- 2. 文档章节表 (document_sections)
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_sections (
    -- 主键字段
    section_id String,                              -- 章节唯一ID（UUID）
    doc_id String,                                  -- 关联文档ID（外键）
    
    -- 分类信息
    document_type LowCardinality(String),           -- 文档类型（冗余字段，加速查询）
    section_type LowCardinality(String),            -- 章节类型
    section_subtype LowCardinality(String) DEFAULT '', -- 章节子类型（预留）
    
    -- 章节结构
    section_title String,                           -- 章节标题
    section_index UInt32,                           -- 章节序号（从0开始）
    page_start UInt32,                              -- 起始页码
    page_end UInt32,                                -- 结束页码
    
    -- 内容字段
    content String,                                 -- 章节文本内容
    content_hash String DEFAULT '',                 -- 内容哈希（用于去重检测）
    
    -- 统计信息
    char_count UInt32,                              -- 字符数
    word_count UInt32 DEFAULT 0,                    -- 词数（可选）
    
    -- 优先级信息
    priority UInt8 DEFAULT 1,                       -- 优先级：1-5（1=最高）
    importance LowCardinality(String) DEFAULT 'normal', -- 重要性：critical/high/normal/low
    confidence Float32 DEFAULT 1.0,                 -- 识别置信度（0-1）
    identification_method LowCardinality(String) DEFAULT 'unknown', -- 识别方法
    
    -- 扩展字段
    metadata String DEFAULT '{}',                   -- JSON格式的扩展信息
    
    -- 时间戳
    created_at DateTime DEFAULT now()
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_index)
PRIMARY KEY (doc_id, section_index)
COMMENT '文档章节切块表 - 存储每个PDF的章节内容，一个章节对应一条记录';

-- ============================================================================
-- 3. 章节实体提取表 (section_entities)
-- ============================================================================
CREATE TABLE IF NOT EXISTS section_entities (
    -- 主键字段
    entity_id String,                               -- 实体唯一ID（UUID）
    section_id String,                              -- 关联章节ID（外键）
    doc_id String,                                  -- 关联文档ID（冗余，加速查询）
    
    -- 实体信息
    entity_type LowCardinality(String),             -- 实体类型
    entity_value String,                            -- 实体值
    entity_unit String DEFAULT '',                  -- 单位（如：HKD, %, 股）
    
    -- 上下文信息
    context String DEFAULT '',                      -- 实体上下文（前后文）
    position UInt32 DEFAULT 0,                      -- 在章节中的位置（字符偏移量）
    
    -- 置信度信息
    confidence Float32 DEFAULT 1.0,                 -- 提取置信度（0-1）
    extraction_method LowCardinality(String) DEFAULT 'regex', -- 提取方法
    
    -- 时间戳
    created_at DateTime DEFAULT now()
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_id, entity_type)
PRIMARY KEY (doc_id, section_id, entity_type)
COMMENT '章节实体提取表 - 存储从章节中提取的关键实体（价格、日期、金额等）';

-- ============================================================================
-- 显示创建结果
-- ============================================================================
SELECT 'Tables created successfully' AS message;
SELECT name, engine, total_rows 
FROM system.tables 
WHERE database = 'hkex_analysis' 
ORDER BY name;

