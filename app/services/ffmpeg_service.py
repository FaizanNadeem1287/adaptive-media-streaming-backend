import os
import subprocess
import uuid


class FFmpegService:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def convert_to_hls(self, input_path: str):

        video_id = str(uuid.uuid4()).replace("-", "")[:16]

        base_dir = os.path.join(self.output_dir, video_id)
        os.makedirs(base_dir, exist_ok=True)

        renditions = [
            ("360p", "640:360", "800k"),
            ("720p", "1280:720", "2500k"),
            ("1080p", "1920:1080", "5000k"),
        ]

        # --- Build filter_complex dynamically ---
        num = len(renditions)
        split_labels = " ".join(f"[v{i}]" for i in range(num))
        filter_parts = [f"[0:v]split={num}{split_labels}"]
        for i, (_, scale, _) in enumerate(renditions):
            filter_parts.append(f"[v{i}]scale={scale}[v{i}out]")
        filter_complex = ";".join(filter_parts)

        cmd = ["ffmpeg", "-y", "-i", input_path]

        cmd += ["-filter_complex", filter_complex]

        # --- Map each scaled video stream + a copy of the audio for each ---
        for i in range(num):
            cmd += ["-map", f"[v{i}out]"]
        for _ in range(num):
            cmd += ["-map", "0:a"]

        # --- Per-stream encoding settings ---
        for i, (_, _, bitrate) in enumerate(renditions):
            cmd += [f"-b:v:{i}", bitrate]

        cmd += [
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
        ]

        # --- var_stream_map: tells FFmpeg to name variants by resolution ---
        # Uses per-type indices: v:0,a:0 / v:1,a:1 / v:2,a:2
        stream_map = " ".join(
            f"v:{i},a:{i},name:{name}"
            for i, (name, _, _) in enumerate(renditions)
        )

        cmd += [
            "-f", "hls",
            "-hls_time", "4",
            "-hls_playlist_type", "vod",
            "-hls_flags", "independent_segments",
            "-master_pl_name", "master.m3u8",
            "-var_stream_map", stream_map,
            "-hls_segment_filename", os.path.join(base_dir, "%v", "segment_%03d.ts"),
            os.path.join(base_dir, "%v", "prog_index.m3u8"),
        ]

        # Create resolution folders before ffmpeg runs
        for name, _, _ in renditions:
            os.makedirs(os.path.join(base_dir, name), exist_ok=True)

        subprocess.run(cmd, check=True)

        return {
            "video_id": video_id,
            "master_playlist": f"{video_id}/master.m3u8",
        }