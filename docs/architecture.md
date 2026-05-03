# Architecture Overview

This document outlines the high-level architecture of the **Nexus Stream** platform. The system is designed to handle video uploads efficiently, process them asynchronously to avoid blocking the main server, and serve them using adaptive bitrate streaming (HLS).

## System Components

### 1. FastAPI Web Server (The Interface)
- **Role:** Handles incoming HTTP requests, authenticates clients, and accepts video uploads.
- **Why FastAPI?** Built on ASGI, it provides extremely high performance for async I/O operations (like writing file uploads to disk).
- **Responsibilities:**
  - File Validation (delegating to the `ffmpeg_service`).
  - Saving the raw source video to `storage/uploads/`.
  - Dispatching a background processing task to Celery.

### 2. Celery & Redis (Task Queue & Message Broker)
- **Role:** Orchestrates long-running background tasks.
- **Redis Broker:** When FastAPI receives an upload, it pushes a task message to a Redis queue.
- **Celery Worker(s):** Background processes that listen to the Redis queue. They pick up the task and execute the heavy video processing logic asynchronously.
- **Benefit:** Decouples the upload process from the transcoding process. Users don't have to wait 10 minutes for FFmpeg to finish before getting an HTTP response.

### 3. FFmpeg Service (The Core Engine)
- **Role:** Handles the actual video decoding, scaling, and encoding.
- **Workflow:** 
  - Splits the source video into 3 resolution tiers (1080p, 720p, 360p) while preserving the original aspect ratio.
  - Encodes the video using `libx264` and the audio using `aac`.
  - Segments the video into small `.ts` chunks (e.g., 4 seconds each).
  - Generates the `.m3u8` variant playlists and the `master.m3u8` playlist for adaptive streaming.

### 4. Nginx (Streaming Server)
- **Role:** Highly efficient static file server.
- **Why Nginx?** FastAPI/Uvicorn is not designed to serve large, static video chunks concurrently to thousands of users. Nginx is purpose-built for this.
- **Responsibilities:**
  - Serving the `storage/hls` directory.
  - Handling CORS (Cross-Origin Resource Sharing) so web-based video players can fetch the streams.
  - Managing Cache-Control headers (ensuring `.m3u8` files aren't cached indefinitely).

## Data Flow Diagram
1. **Client** -> `POST /api/upload` -> **FastAPI**
2. **FastAPI** -> Reads Magic Bytes -> Saves to Disk
3. **FastAPI** -> Dispatches Task -> **Redis**
4. **Celery Worker** -> Pulls Task from Redis -> Triggers **FFmpeg**
5. **FFmpeg** -> Transcodes -> Writes to `storage/hls/<video-id>/`
6. **Client Player** -> Requests `master.m3u8` -> **Nginx**
7. **Nginx** -> Streams chunks to Client.
