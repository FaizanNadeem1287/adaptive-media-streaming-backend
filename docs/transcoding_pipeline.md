# Transcoding & Video Processing Pipeline

The core functionality of this platform relies on the FFmpeg service, encapsulated within `app/services/ffmpeg_service/`. This document explains how the pipeline validates, scales, and transcodes video files.

## 1. Magic-Byte Validation (`validator.py`)
Relying on file extensions (like `.mp4` or `.avi`) is insecure; a malicious user can rename an `.exe` or a malicious script to `.mp4`. 

To prevent this, the system reads the **magic bytes** (the file signature at the very beginning of the binary file) before attempting to save the file.
- We read the first `20` bytes of the incoming `UploadFile` stream.
- We match the byte sequences against known video container formats (e.g., `\x1a\x45\xdf\xa3` for MKV/WebM, or `ftyp` at offset 4 for MP4).
- If it fails to match a known video signature, the upload is aborted immediately.

## 2. Adaptive Bitrate Streaming (ABR)
We use HLS (HTTP Live Streaming) to deliver video. Instead of delivering one massive file, the video is chunked and provided in multiple resolutions.

### Default Renditions
| Name | Resolution | Bitrate |
|---|---|---|
| 360p | Auto x 360 | 800k |
| 720p | Auto x 720 | 2500k |
| 1080p | Auto x 1080 | 5000k |

### Aspect Ratio Preservation
In the `command_builder.py`, we use the FFmpeg scale filter `scale=-2:720`. 
- The `720` enforces the height.
- The `-2` tells FFmpeg to automatically calculate the width based on the original video's aspect ratio, while ensuring the resulting integer is even (a requirement for the `x264` encoder).
- This prevents videos (like 9:16 vertical shorts) from being horizontally stretched into 16:9 widescreen boxes.

## 3. Command Orchestration (`converter.py`)
The `HLSConverter` class acts as the orchestrator:
1. **Directory Setup**: It creates a unique UUID folder in `storage/hls/`. It then creates subfolders for each resolution (e.g., `360p`, `720p`).
2. **Subprocess Execution**: It launches the `ffmpeg` CLI using Python's `subprocess.run()`.
3. **Error Handling**: Standard error output from FFmpeg is parsed to catch `FFmpegExecutionError`s, ensuring we can log precisely why a transcoding job failed.
