from fastapi import APIRouter, status, File, UploadFile
from app.api.upload.service import UploadService

router = APIRouter(prefix="/api", tags=["Media Upload APIs"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...)):
    """
    Uploads a video file.
    """
    service = UploadService()
    response = await service.upload_video(file)

    return response