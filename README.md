# Nexus Stream - Adaptive HLS Video Platform 🎬

A professional-grade backend architecture for Adaptive HTTP Live Streaming (HLS). This project takes uploaded video files, securely validates them, processes them asynchronously into multiple quality tiers (1080p, 720p, 360p) using FFmpeg, and streams them smoothly to clients via an Nginx server.

## 🌟 Key Features

- **Adaptive Bitrate Streaming (ABR):** Automatically transcodes videos into multiple resolutions (1080p, 720p, 360p) to adapt to the user's internet speed.
- **Smart Aspect Ratio Preservation:** FFmpeg intelligently scales videos without stretching or distorting non-standard aspect ratios (like vertical phone videos).
- **Asynchronous Processing:** Heavy FFmpeg transcoding is offloaded to a background Celery worker to ensure the FastAPI server remains blazing fast.
- **Robust Security (Magic-Byte Validation):** Uploads are validated by reading file headers (magic bytes) rather than relying on easily-spoofed file extensions.
- **Test UI:** Includes a premium, glassmorphism frontend player built with HTML, CSS, and HLS.js.

---

## 🏗️ Architecture

1. **FastAPI (Backend):** Handles HTTP requests, accepts multipart file uploads, validates file signatures, and queues processing tasks.
2. **Celery & Redis (Task Queue):** Orchestrates the background video conversion jobs.
3. **FFmpeg (Transcoder):** Performs the heavy lifting, splitting the video and audio streams, encoding them with `libx264`, and generating `.m3u8` playlists and `.ts` segments.
4. **Nginx (Streaming Server):** Highly optimized web server serving the `.m3u8` and `.ts` files with proper CORS configuration and MIME types.
5. **Frontend (HLS.js):** A lightweight web client to test the HLS adaptive streams.

---

## 📋 Prerequisites

Before running the project, ensure you have the following installed on your system:
- **Python 3.10+**
- **FFmpeg** (`sudo apt install ffmpeg`)
- **Redis Server** (`sudo apt install redis-server`)
- **Nginx** (`sudo apt install nginx`)

---

## 🚀 Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <your-repo-url>
   cd hls-streaming
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   A `.env` file should be present in the root directory with the following variables:
   ```env
   FILE_UPLOAD_PATH=storage/uploads
   REDIS_BROKER_URL=redis://localhost:6379/0
   REDIS_BACKEND_URL=redis://localhost:6379/0
   HLS_OUTPUT_PATH=storage/hls
   ```

---

## 🏃‍♂️ Running the Platform

You need to run 4 separate components to get the full pipeline working. Open 4 separate terminal windows.

### 1. Start Redis
Ensure your Redis server is running in the background to handle Celery queues.
```bash
sudo systemctl start redis-server
# Or simply: redis-server
```

### 2. Start the Celery Worker
This worker listens for upload events and processes videos using FFmpeg.
```bash
source .venv/bin/activate
celery -A worker.celery_app worker --loglevel=info -E
```

### 3. Start the FastAPI Server
Runs the main web API.
```bash
source .venv/bin/activate
fastapi dev app/main.py
```
*API will be available at: http://localhost:8000*

### 4. Start the Nginx Streaming Server
Start Nginx using the custom configuration file provided in the repository to serve the HLS chunks.
```bash
sudo nginx -c /path/to/your/hls-streaming/nginx/nginx.conf
```
*Make sure to replace `/path/to/your/` with the absolute path to this project.*

### 5. Play the Video (Frontend)
1. Upload a video via the FastAPI Swagger Docs (`http://localhost:8000/docs`).
2. Wait for the Celery worker to finish transcoding.
3. Open `frontend/index.html` in your web browser.
4. Paste your stream URL (e.g., `http://localhost:8080/hls/<video-id>/master.m3u8`) and click "Play Stream".

---

## 📡 API Endpoints

### Health Check
- **`GET /api/health`**
- Returns the health status of the API.

### Upload Video
- **`POST /api/upload`**
- **Content-Type:** `multipart/form-data`
- **Payload:** `file` (The video file to be uploaded).
- **Behavior:** Validates the magic bytes. If valid, saves the file to `storage/uploads/` and dispatches a background task to convert it to HLS in `storage/hls/<video-id>/`.
- **Response:**
  ```json
  {
    "status": "ok",
    "message": "Video uploaded successfully (format: MP4/MOV/M4V)",
    "data": {
      "file_location": "./storage/uploads/video.mp4",
      "format": "MP4/MOV/M4V"
    }
  }
  ```

---

## 🛠️ Built With

- **[FastAPI](https://fastapi.tiangolo.com/)** - High performance web framework
- **[Celery](https://docs.celeryq.dev/)** - Distributed task queue
- **[FFmpeg](https://ffmpeg.org/)** - The industry standard for video/audio processing
- **[Nginx](https://nginx.org/)** - High performance HTTP server
- **[HLS.js](https://github.com/video-dev/hls.js)** - JavaScript HLS client using Media Source Extension
