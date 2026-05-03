from fastapi import FastAPI
from app.api.health import health
from app.api.upload import upload
from worker.celery_app import celery_app

app = FastAPI()

app.include_router(health.router) # Health Check Route
app.include_router(upload.router)   # Upload Route
