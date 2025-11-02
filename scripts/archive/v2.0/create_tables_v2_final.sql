-- ============================================================================
-- ClickHouse V2.0 表结构（完全移除向量版本）
-- 用于港股公告文档按章节切块存储
-- 创建日期：2025-10-29
-- ============================================================================

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
    metadata String DEFAULT '{}',                   -- JSON格式的扩展信息，存储：
                                                    -- {
                                                    --   "rights_ratio": "1:4",        # 供股比例
                                                    --   "processing_version": "2.0",  # 处理版本
                                                    --   "source_system": "hkex",     # 数据来源
                                                    --   "file_hash": "md5_xxx",      # 文件哈希（可选）
                                                    --   "custom_tags": ["tag1"]      # 自定义标签（可选）
                                                    -- }
    
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
    section_type LowCardinality(String),            -- 章节类型，见下方注释
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
    priority UInt8 DEFAULT 1,                       -- 优先级：1-5（1=最高，对应section_level）
    importance LowCardinality(String) DEFAULT 'normal', -- 重要性：critical/high/normal/low
    confidence Float32 DEFAULT 1.0,                 -- 识别置信度（0-1）
    identification_method LowCardinality(String) DEFAULT 'unknown', -- 识别方法：regex/rule/manual
    
    -- 扩展字段
    metadata String DEFAULT '{}',                   -- JSON格式的扩展信息，存储：
                                                    -- {
                                                    --   "section_num": "一",         # 章节编号
                                                    --   "has_table": true,          # 是否包含表格
                                                    --   "table_count": 2,           # 表格数量
                                                    --   "key_entities": [...],      # 关键实体
                                                    --   "parent_section": "xxx"     # 父章节（多级结构时）
                                                    -- }
    
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
    entity_type LowCardinality(String),             -- 实体类型，见下方注释
    entity_value String,                            -- 实体值
    entity_unit String DEFAULT '',                  -- 单位（如：HKD, %, 股）
    
    -- 上下文信息
    context String DEFAULT '',                      -- 实体上下文（前后文）
    position UInt32 DEFAULT 0,                      -- 在章节中的位置（字符偏移量）
    
    -- 置信度信息
    confidence Float32 DEFAULT 1.0,                 -- 提取置信度（0-1）
    extraction_method LowCardinality(String) DEFAULT 'regex', -- 提取方法：regex/ner/rule
    
    -- 时间戳
    created_at DateTime DEFAULT now()
    
) ENGINE = MergeTree()
ORDER BY (doc_id, section_id, entity_type)
PRIMARY KEY (doc_id, section_id, entity_type)
COMMENT '章节实体提取表 - 存储从章节中提取的关键实体（价格、日期、金额等）';

-- ============================================================================
-- 枚举值参考 (Enum Reference)
-- ============================================================================

-- document_type（文档类型）：
--   'rights'          - 供股
--   'placing'         - 配售
--   'ipo'             - 首次公开募股
--   'consolidation'   - 合股
--   'subscription'    - 认购

-- document_subtype（文档子类型）：
--   'underwritten'     - 包销
--   'non-underwritten' - 非包销

-- processing_status（处理状态）：
--   'pending'     - 待处理
--   'processing'  - 处理中
--   'completed'   - 已完成
--   'failed'      - 失败

-- section_type（章节类型）：
--   'terms'           - 供股条款
--   'timetable'       - 时间表
--   'underwriting'    - 包销安排
--   'financials'      - 财务信息
--   'risk_factors'    - 风险因素
--   'suspension'      - 暂停办理过户
--   'use_of_proceeds' - 募集资金用途
--   'management'      - 董事/高级管理层
--   'company_info'    - 公司资料
--   'legal'           - 法律/责任声明
--   'contracts'       - 重大合约
--   'disclosure'      - 权益披露
--   'market'          - 市场价格
--   'interests'       - 竞争权益
--   'documents'       - 展示文件
--   'appendix'        - 附录
--   'misc'            - 其他杂项
--   'other'           - 未分类

-- importance（重要性）：
--   'critical' - 关键章节（如：供股条款、财务数据）
--   'high'     - 高重要性（如：风险因素、时间表）
--   'normal'   - 普通（大部分章节）
--   'low'      - 低重要性（如：附录、其他）

-- identification_method（识别方法）：
--   'regex'   - 正则表达式
--   'rule'    - 规则引擎
--   'manual'  - 人工标注
--   'unknown' - 未知

-- entity_type（实体类型）：
--   'price'       - 价格（认购价）
--   'ratio'       - 比例（供股比例）
--   'date'        - 日期（关键日期）
--   'money'       - 金额（募集金额）
--   'percentage'  - 百分比（折让率）
--   'quantity'    - 数量（股份数）
--   'company'     - 公司名
--   'person'      - 人名（董事、承销商）
--   'address'     - 地址
--   'contact'     - 联系方式

-- extraction_method（提取方法）：
--   'regex'   - 正则表达式
--   'ner'     - 命名实体识别
--   'rule'    - 规则引擎
--   'llm'     - 大模型提取

-- ============================================================================
-- 表关系说明
-- ============================================================================
-- documents_v2 (1) ─────< document_sections (N)
--                              │
--                              └───< section_entities (N)
--
-- 一个文档包含多个章节，一个章节可以提取多个实体
-- ============================================================================

