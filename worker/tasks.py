import logging
from celery import Celery
from app.core.config import settings
from app.services.ffmpeg_service import HLSConverter

logger = logging.getLogger(__name__)

app = Celery(
    "video_processor",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_BACKEND_URL,
)

@app.task
def process_video(file_path: str, output_path: str):
    try:
        logger.info(f"Processing video: {file_path}")
        hls_converter = HLSConverter(output_dir=output_path)
        hls_converter.convert(input_path=file_path)
        return True
    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        return False