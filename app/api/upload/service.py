import logging
import os

from app.core.config import settings
from fastapi import UploadFile
from .schemas import UploadResponse
from app.core.response import ApiResponse
from app.services.ffmpeg_service.validator import validate_video_header
from app.services.ffmpeg_service.exceptions import InvalidVideoFileError
from worker.tasks import process_video

logger = logging.getLogger(__name__)

class UploadService:
    def __init__(self):
        self.settings = settings
        self.file_upload_path = settings.FILE_UPLOAD_PATH
    
    async def upload_video(self, file: UploadFile) -> ApiResponse:
        """
        Uploads a video file.
        """
        try:
            # Validate the file header (magic bytes)
            header = await file.read(20) # read first 20 bytes
            await file.seek(0) # rewind the file pointer
            
            format_label = validate_video_header(header)
            
            os.makedirs(self.file_upload_path, exist_ok=True)
            file_location = f"./{self.file_upload_path}/{file.filename.split('.')[0]}.{file.filename.split('.')[-1]}"
            with open(file_location, "wb") as buffer:
                buffer.write(await file.read())

            logger.info("Video uploaded successfully (format: %s)", format_label)

            process_video.delay(file_location, self.file_upload_path) # Background Task to start HLS conversion
            
            logger.info("Video processing started in background")

            return ApiResponse(
                status="ok", 
                message=f"Video uploaded successfully (format: {format_label})", 
                data={"file_location": file_location, "format": format_label}
            )
        except InvalidVideoFileError as e:
            return ApiResponse(status="error", message=f"Invalid video file: {e.reason}", data=None)
        except Exception as e:
            return ApiResponse(status="error", message=str(e), data=None)