import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging
from app.services.ffmpeg_service import HLSConverter, InvalidVideoFileError

# Activate logging before anything else
setup_logging(level="INFO")


class TestFFmpegService:
    def test_convert_to_hls(self):
        converter = HLSConverter(output_dir="storage/hls")
        result = converter.convert(input_path="storage/uploads/video001.mp4")
        print("\n✅ Conversion succeeded:", result)

    def test_invalid_file_rejected(self):
        """Pass a non-video file and confirm it raises InvalidVideoFileError."""
        converter = HLSConverter(output_dir="storage/hls")
        dummy = Path("storage/uploads/_dummy.txt")
        dummy.write_text("this is not a video")
        try:
            converter.convert(input_path=str(dummy))
            print("\n❌ Should have raised InvalidVideoFileError")
        except InvalidVideoFileError as exc:
            print(f"\n✅ Correctly rejected: {exc}")
        finally:
            dummy.unlink(missing_ok=True)


if __name__ == "__main__":
    t = TestFFmpegService()
    t.test_invalid_file_rejected()
    t.test_convert_to_hls()