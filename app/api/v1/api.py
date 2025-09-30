from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, activation, admin, resumes, matching, visual_analysis

api_router = APIRouter()

# 包含各模块的路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(activation.router, prefix="/activation", tags=["激活码管理"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["简历管理"])
api_router.include_router(matching.router, prefix="/matching", tags=["智能匹配"])
api_router.include_router(visual_analysis.router, prefix="/matching", tags=["视觉分析"])

@api_router.get("/status")
async def api_status():
    return {"status": "API v1 is running"}