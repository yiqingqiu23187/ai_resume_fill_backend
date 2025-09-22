-- ====================================
-- 修复时区问题 - 将所有TIMESTAMPTZ字段改为TIMESTAMP
-- 这样可以避免Python中offset-naive和offset-aware datetime比较错误
-- ====================================

BEGIN;

-- 修改users表
ALTER TABLE users
ALTER COLUMN created_at TYPE TIMESTAMP,
ALTER COLUMN updated_at TYPE TIMESTAMP;

-- 修改activation_codes表
ALTER TABLE activation_codes
ALTER COLUMN created_at TYPE TIMESTAMP,
ALTER COLUMN expires_at TYPE TIMESTAMP;

-- 修改user_activations表
ALTER TABLE user_activations
ALTER COLUMN activated_at TYPE TIMESTAMP;

-- 修改resumes表
ALTER TABLE resumes
ALTER COLUMN created_at TYPE TIMESTAMP,
ALTER COLUMN updated_at TYPE TIMESTAMP;

-- 修改usage_logs表
ALTER TABLE usage_logs
ALTER COLUMN used_at TYPE TIMESTAMP;

COMMIT;

-- ====================================
-- 迁移完成
-- ====================================

DO $$
BEGIN
    RAISE NOTICE '🎉 时区问题修复完成！';
    RAISE NOTICE '📋 已将所有TIMESTAMPTZ字段改为TIMESTAMP';
    RAISE NOTICE '🔧 现在可以使用datetime.utcnow()进行比较';
END $$;
