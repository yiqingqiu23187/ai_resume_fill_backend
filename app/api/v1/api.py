from fastapi import APIRouter

api_router = APIRouter()

# Placeholder for future route imports
# from app.api.v1.endpoints import auth, users, resumes, activation, matching

@api_router.get("/status")
async def api_status():
    return {"status": "API v1 is running"}