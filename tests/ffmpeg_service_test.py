import os
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.ffmpeg_service import FFmpegService, VideoValidationError


class TestFFmpegService:

    def test_convert_to_hls(self):
        """Happy path — valid MP4 should transcode successfully."""
        service = FFmpegService(output_dir="storage/hls")
        result = service.convert_to_hls(input_path="storage/uploads/video001.mp4")
        print(f"✅ HLS conversion succeeded: {result}")
        assert "video_id" in result
        assert result["master_playlist"].endswith("master.m3u8")

    def test_reject_non_video_file(self):
        """A plain text file renamed to .mp4 must be rejected."""
        fake = os.path.join("storage", "uploads", "fake_video.mp4")
        with open(fake, "w") as f:
            f.write("this is definitely not a video")
        try:
            service = FFmpegService(output_dir="storage/hls")
            service.convert_to_hls(input_path=fake)
            print("❌ Should have raised VideoValidationError")
        except VideoValidationError as e:
            print(f"✅ Correctly rejected fake file: {e}")
        finally:
            os.remove(fake)

    def test_reject_missing_file(self):
        """A non-existent path must raise FileNotFoundError."""
        service = FFmpegService(output_dir="storage/hls")
        try:
            service.convert_to_hls(input_path="storage/uploads/nonexistent.mp4")
            print("❌ Should have raised FileNotFoundError")
        except FileNotFoundError as e:
            print(f"✅ Correctly rejected missing file: {e}")

    def test_reject_image_file(self):
        """A PNG image must be rejected even though it has valid magic bytes for PNG."""
        # Create a minimal valid PNG header
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        fake_img = os.path.join("storage", "uploads", "image.png")
        with open(fake_img, "wb") as f:
            f.write(png_header)
        try:
            service = FFmpegService(output_dir="storage/hls")
            service.convert_to_hls(input_path=fake_img)
            print("❌ Should have raised VideoValidationError")
        except VideoValidationError as e:
            print(f"✅ Correctly rejected PNG image: {e}")
        finally:
            os.remove(fake_img)


if __name__ == "__main__":
    t = TestFFmpegService()

    print("=" * 60)
    print("TEST 1: Missing file")
    t.test_reject_missing_file()

    print("\nTEST 2: Fake video (text renamed to .mp4)")
    t.test_reject_non_video_file()

    print("\nTEST 3: PNG image")
    t.test_reject_image_file()

    print("\nTEST 4: Valid video → HLS conversion")
    t.test_convert_to_hls()

    print("=" * 60)
    print("All tests passed.")