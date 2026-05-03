import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.ffmpeg_service import FFmpegService


class TestFFmpegService:
    def test_convert_to_hls(self):
        service = FFmpegService(output_dir="storage/hls")
        result = service.convert_to_hls(input_path="storage/uploads/video001.mp4")
        print(result)


if __name__ == "__main__":
    test_service = TestFFmpegService()
    test_service.test_convert_to_hls()