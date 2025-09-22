-- ====================================
-- 简历表结构迁移脚本 - 简化版
-- 从固定字段结构迁移到灵活的key-value结构
-- 生成时间: 2024-12-22
-- ====================================

-- 开始事务
BEGIN;

-- 添加新字段
ALTER TABLE resumes
ADD COLUMN title VARCHAR(200) NULL,
ADD COLUMN fields JSONB NOT NULL DEFAULT '{}';

-- 更新字段注释
COMMENT ON COLUMN resumes.title IS '简历标题';
COMMENT ON COLUMN resumes.fields IS '简历字段数据JSON - 灵活的key-value结构';

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_resumes_fields_gin ON resumes USING gin (fields);
CREATE INDEX IF NOT EXISTS idx_resumes_title ON resumes (title);

-- 删除旧字段
ALTER TABLE resumes
DROP COLUMN personal_info,
DROP COLUMN education,
DROP COLUMN experience,
DROP COLUMN skills;

-- 提交事务
COMMIT;

-- ====================================
-- 迁移完成
-- ====================================

DO $$
BEGIN
    RAISE NOTICE '🎉 简历表结构迁移完成！';
    RAISE NOTICE '📋 已将固定字段结构迁移到灵活的key-value结构';
    RAISE NOTICE '🔑 已创建新的索引以提高查询性能';
END $$;
