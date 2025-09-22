# AI Resume Autofill Backend

AI简历自动填写系统的后端API服务，基于FastAPI构建。

## 功能特性

- 用户认证和授权
- 简历信息管理
- 激活码管理系统
- AI智能字段匹配
- RESTful API接口

## 技术栈

- **框架**: FastAPI
- **数据库**: PgSQL
- **ORM**: SQLAlchemy
- **认证**: JWT
- **AI服务**: OpenAI API
- **部署**: Uvicorn

## 快速开始

### 安装依赖

1. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者 venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 环境配置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置数据库和API密钥

### 运行应用

```bash
python -m app.main
```

应用将在 http://localhost:8000 启动

### API文档

启动应用后，访问以下地址查看API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/           # API路由
│   ├── core/          # 核心配置
│   ├── db/            # 数据库配置
│   ├── models/        # 数据模型
│   ├── schemas/       # Pydantic模式
│   ├── services/      # 业务逻辑
│   └── main.py        # 应用入口
├── requirements.txt   # 依赖列表
├── .env.example      # 环境变量模板
└── README.md         # 项目说明
```

## 开发指南

### 启动开发服务器

在虚拟环境中运行：
```bash
python -m app.main
```

### 测试

```bash
pytest
```

### 代码规范

项目使用以下工具保证代码质量：
- Black: 代码格式化
- isort: 导入排序
- flake8: 代码检查