#!/usr/bin/env python3
"""
数据库迁移初始化脚本
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command: str, cwd: str = None):
    """执行命令"""
    print(f"执行命令: {command}")
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd or str(project_root),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    else:
        print(f"成功: {result.stdout}")
        return True

def init_alembic():
    """初始化Alembic迁移"""
    print("=== 初始化Alembic迁移 ===")

    # 创建版本目录
    versions_dir = project_root / "alembic" / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    # 生成初始迁移
    success = run_command("alembic revision --autogenerate -m 'Initial migration'")
    if success:
        print("✅ Alembic迁移初始化成功")
        return True
    else:
        print("❌ Alembic迁移初始化失败")
        return False

def create_env_file():
    """创建.env文件（如果不存在）"""
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists() and env_example.exists():
        print("=== 创建.env文件 ===")
        env_file.write_text(env_example.read_text())
        print("✅ .env文件已创建，请根据实际情况修改配置")

if __name__ == "__main__":
    print("🚀 开始初始化数据库迁移...")

    # 创建环境文件
    create_env_file()

    # 初始化Alembic
    if init_alembic():
        print("\n🎉 数据库迁移初始化完成！")
        print("\n接下来的步骤：")
        print("1. 修改.env文件中的数据库配置")
        print("2. 运行 'alembic upgrade head' 执行迁移")
        print("3. 运行 'python -m uvicorn app.main:app --reload' 启动服务")
    else:
        print("\n❌ 初始化失败，请检查错误信息")
        sys.exit(1)
