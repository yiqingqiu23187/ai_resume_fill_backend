-- AI简历自动填写系统 - 数据库初始化SQL脚本
-- 生成时间: 2024-12-22
-- PostgreSQL版本: 12+

-- ====================================
-- 1. 创建数据库扩展
-- ====================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================
-- 2. 创建枚举类型
-- ====================================

-- 用户状态枚举
DO $$ BEGIN
    CREATE TYPE userstatus AS ENUM ('ACTIVE', 'INACTIVE', 'BANNED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 激活码状态枚举
DO $$ BEGIN
    CREATE TYPE activationcodestatus AS ENUM ('ACTIVE', 'USED', 'EXPIRED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ====================================
-- 3. 创建核心表
-- ====================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status userstatus DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 为表和字段添加注释
COMMENT ON TABLE users IS '用户信息表';
COMMENT ON COLUMN users.id IS '用户唯一标识';
COMMENT ON COLUMN users.email IS '用户邮箱';
COMMENT ON COLUMN users.password_hash IS '密码哈希值';
COMMENT ON COLUMN users.status IS '用户状态';
COMMENT ON COLUMN users.created_at IS '创建时间';
COMMENT ON COLUMN users.updated_at IS '更新时间';

-- 激活码表
CREATE TABLE IF NOT EXISTS activation_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(32) UNIQUE NOT NULL,
    total_uses INTEGER DEFAULT 5,
    used_count INTEGER DEFAULT 0,
    status activationcodestatus DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL
);

-- 为表和字段添加注释
COMMENT ON TABLE activation_codes IS '激活码管理表';
COMMENT ON COLUMN activation_codes.id IS '激活码唯一标识';
COMMENT ON COLUMN activation_codes.code IS '激活码字符串';
COMMENT ON COLUMN activation_codes.total_uses IS '总使用次数';
COMMENT ON COLUMN activation_codes.used_count IS '已使用次数';
COMMENT ON COLUMN activation_codes.status IS '激活码状态';
COMMENT ON COLUMN activation_codes.created_at IS '创建时间';
COMMENT ON COLUMN activation_codes.expires_at IS '过期时间';

-- 简历表
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    personal_info JSONB NOT NULL DEFAULT '{}',
    education JSONB NOT NULL DEFAULT '{}',
    experience JSONB NOT NULL DEFAULT '{}',
    skills JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_resumes_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- 为表和字段添加注释
COMMENT ON TABLE resumes IS '用户简历信息表';
COMMENT ON COLUMN resumes.id IS '简历唯一标识';
COMMENT ON COLUMN resumes.user_id IS '关联用户ID';
COMMENT ON COLUMN resumes.personal_info IS '个人基本信息JSON';
COMMENT ON COLUMN resumes.education IS '教育经历JSON';
COMMENT ON COLUMN resumes.experience IS '工作经验JSON';
COMMENT ON COLUMN resumes.skills IS '技能信息JSON';
COMMENT ON COLUMN resumes.created_at IS '创建时间';
COMMENT ON COLUMN resumes.updated_at IS '更新时间';

-- 用户激活记录表
CREATE TABLE IF NOT EXISTS user_activations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    activation_code_id UUID NOT NULL,
    remaining_uses INTEGER DEFAULT 5,
    activated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_user_activations_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_activations_activation_code_id
        FOREIGN KEY (activation_code_id)
        REFERENCES activation_codes(id)
        ON DELETE CASCADE
);

-- 为表和字段添加注释
COMMENT ON TABLE user_activations IS '用户激活码绑定记录表';
COMMENT ON COLUMN user_activations.id IS '记录唯一标识';
COMMENT ON COLUMN user_activations.user_id IS '关联用户ID';
COMMENT ON COLUMN user_activations.activation_code_id IS '关联激活码ID';
COMMENT ON COLUMN user_activations.remaining_uses IS '剩余使用次数';
COMMENT ON COLUMN user_activations.activated_at IS '激活时间';

-- 使用日志表
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    fields_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    used_at TIMESTAMPTZ DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_usage_logs_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- 为表和字段添加注释
COMMENT ON TABLE usage_logs IS '系统使用日志表';
COMMENT ON COLUMN usage_logs.id IS '日志唯一标识';
COMMENT ON COLUMN usage_logs.user_id IS '关联用户ID';
COMMENT ON COLUMN usage_logs.website_url IS '使用的网站URL';
COMMENT ON COLUMN usage_logs.fields_count IS '检测到的字段数量';
COMMENT ON COLUMN usage_logs.success_count IS '成功填写的字段数量';
COMMENT ON COLUMN usage_logs.used_at IS '使用时间';

-- ====================================
-- 4. 创建索引
-- ====================================

-- 用户表索引
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_status ON users(status);
CREATE INDEX IF NOT EXISTS ix_users_created_at ON users(created_at);

-- 激活码表索引
CREATE UNIQUE INDEX IF NOT EXISTS ix_activation_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS ix_activation_codes_status ON activation_codes(status);
CREATE INDEX IF NOT EXISTS ix_activation_codes_expires_at ON activation_codes(expires_at);

-- 简历表索引
CREATE INDEX IF NOT EXISTS ix_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS ix_resumes_created_at ON resumes(created_at);

-- 用户激活记录表索引
CREATE INDEX IF NOT EXISTS ix_user_activations_user_id ON user_activations(user_id);
CREATE INDEX IF NOT EXISTS ix_user_activations_activation_code_id ON user_activations(activation_code_id);
CREATE INDEX IF NOT EXISTS ix_user_activations_activated_at ON user_activations(activated_at);

-- 使用日志表索引
CREATE INDEX IF NOT EXISTS ix_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_usage_logs_used_at ON usage_logs(used_at);
CREATE INDEX IF NOT EXISTS ix_usage_logs_website_url ON usage_logs(website_url);

-- ====================================
-- 5. 创建更新时间触发器
-- ====================================

-- 创建更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建更新时间触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_resumes_updated_at ON resumes;
CREATE TRIGGER update_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 6. 创建Alembic版本表（可选）
-- ====================================

-- 如果需要与Alembic兼容，创建版本表
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- 插入当前迁移版本（与Alembic保持同步）
INSERT INTO alembic_version (version_num)
VALUES ('abcd14f8fbc6')
ON CONFLICT (version_num) DO NOTHING;

-- ====================================
-- 7. 创建示例数据（可选）
-- ====================================

-- 插入默认管理员用户（密码为：admin123）
INSERT INTO users (id, email, password_hash, status, created_at, updated_at)
VALUES (
    uuid_generate_v4(),
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeSwV4TlH4mBuUm6i',
    'ACTIVE',
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- 插入测试激活码
INSERT INTO activation_codes (id, code, total_uses, used_count, status, created_at, expires_at)
VALUES (
    uuid_generate_v4(),
    'TEST2024DEMO1234',
    10,
    0,
    'ACTIVE',
    NOW(),
    NOW() + INTERVAL '365 days'
) ON CONFLICT (code) DO NOTHING;

-- ====================================
-- 8. 权限设置（生产环境使用）
-- ====================================

-- 创建应用专用用户（生产环境建议使用）
-- DO $$ BEGIN
--     CREATE USER ai_resume_app WITH ENCRYPTED PASSWORD 'your_secure_password_here';
-- EXCEPTION
--     WHEN duplicate_object THEN null;
-- END $$;

-- 授予应用用户权限
-- GRANT CONNECT ON DATABASE ai_resume_autofill TO ai_resume_app;
-- GRANT USAGE ON SCHEMA public TO ai_resume_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ai_resume_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_resume_app;

-- ====================================
-- 初始化完成
-- ====================================

-- 查看创建的表
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 输出完成信息
DO $$
BEGIN
    RAISE NOTICE '🎉 AI简历自动填写系统数据库初始化完成！';
    RAISE NOTICE '📋 已创建表: users, activation_codes, resumes, user_activations, usage_logs';
    RAISE NOTICE '🔑 已创建索引和约束';
    RAISE NOTICE '⚡ 已设置自动更新时间戳触发器';
    RAISE NOTICE '🚀 系统准备就绪！';
END $$;
