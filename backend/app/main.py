from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.routes import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FormaX AI - Member 2: AI Pipeline & Security Backend",
    version="1.0.0",
)

# CORS middleware for seamless integration with Member 1 React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes under /api and root
app.include_router(router, prefix="/api")
app.include_router(router)  # Direct /health access

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
