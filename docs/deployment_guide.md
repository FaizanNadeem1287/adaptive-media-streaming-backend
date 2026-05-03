# Deployment & Infrastructure Guide

This guide outlines how the platform should be deployed in a production environment. Currently, the application is run locally in separate terminals, but production requires process managers and containerization.

## Nginx Streaming Server
Nginx is absolutely critical for the HLS platform. The provided `nginx/nginx.conf` handles:
1. **MIME Types:** Browsers will refuse to play `.m3u8` and `.ts` files if they are served as `text/plain`. Nginx forces the correct MIME types.
2. **CORS Headers:** Modern web players (Video.js, HLS.js) use XHR/Fetch to download video chunks. If Nginx doesn't return `Access-Control-Allow-Origin: *`, the browser will block the stream.
3. **No-Cache:** Playlist files (`.m3u8`) update frequently (especially in live streaming). We explicitly set `Cache-Control no-cache` for these to prevent clients from stalling.

## Worker Process Management
In a production environment, the Celery worker must be managed by a system supervisor (like `systemd` or `Supervisor`) to ensure it restarts upon failure. 

Example `systemd` configuration for Celery:
```ini
[Unit]
Description=Celery Worker for Video Processing
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/hls-streaming
ExecStart=/path/to/.venv/bin/celery -A worker.celery_app worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

## Future Step: Dockerization
To ensure environment parity across dev, staging, and production, the system should be dockerized. 
A standard `docker-compose.yml` would include:
- `api`: The FastAPI web server.
- `worker`: The Celery background processor (with FFmpeg installed in the Docker image).
- `redis`: The message broker container.
- `nginx`: The web server container mounting the `storage/hls` volume.

*Note: `storage/hls` must be mounted as a shared volume between the `worker` (which writes the chunks) and `nginx` (which reads the chunks).*
