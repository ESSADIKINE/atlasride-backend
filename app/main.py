from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.services.simulation import simulation_engine
import asyncio

app = FastAPI(
    title="AtlasRide AI",
    description="Autonomous Car Circulation Simulation Platform",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://atlasride-frontend-git-main-essadikines-projects.vercel.app/","https://atlasride-frontend.vercel.app/","https://atlasride-backend.vercel.app/api"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Start simulation engine on application startup"""
    print("🚀 Starting AtlasRide AI backend...")
    # Start simulation in background
    asyncio.create_task(simulation_engine.start())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop simulation engine on application shutdown"""
    print("🛑 Shutting down AtlasRide AI backend...")
    simulation_engine.stop()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AtlasRide AI - Autonomous Car Simulation Platform",
        "version": "1.0.0",
        "docs": "/docs"
    }
