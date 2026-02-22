from __future__ import annotations

from typing import List, Optional, Callable
import os
import re
import tempfile
import subprocess
import shutil

from models.domain.marker import Marker


ProgressCallback = Optional[Callable[[int], None]]
CancelCheck = Optional[Callable[[], bool]]


class VideoExporter:
    """Service for exporting video segments.

    Marker contract expected:
        start_frame inclusive
        end_frame exclusive
    """

    @staticmethod
    def export_segments(
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        codec: str = "libx264",
        quality: int = 23,
        resolution: Optional[str] = None,
        include_audio: bool = True,
        merge_segments: bool = True,
        progress_callback: ProgressCallback = None,
        cancel_check: CancelCheck = None,
    ) -> bool:
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if fps <= 0:
                fps = 30.0

            # Normalize & sort markers (playlist order)
            markers = sorted(markers, key=lambda m: (m.start_frame, m.end_frame))

            # Ensure output dir exists
            out_dir = os.path.dirname(output_path) or "."
            os.makedirs(out_dir, exist_ok=True)

            if cancel_check and cancel_check():
                return False

            if not markers:
                return VideoExporter._export_empty_clip(video_path, fps, output_path)

            # true copy mode (stream copy) - fast but can be inaccurate on cuts
            if codec.lower() == "copy":
                return VideoExporter._export_stream_copy(
                    video_path=video_path,
                    markers=markers,
                    fps=fps,
                    output_path=output_path,
                    include_audio=include_audio,
                    merge_segments=merge_segments,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                )

            # re-encode modes
            return VideoExporter._export_with_reencode(
                video_path=video_path,
                markers=markers,
                fps=fps,
                output_path=output_path,
                codec=codec,
                quality=quality,
                resolution=resolution,
                include_audio=include_audio,
                merge_segments=merge_segments,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

        except Exception as e:
            print(f"Export error: {e}")
            raise

    # ──────────────────────────────────────────────────────────────────────
    # Stream copy (ffmpeg)
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _export_stream_copy(
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        include_audio: bool,
        merge_segments: bool,
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> bool:
        """Export using ffmpeg stream copy.

        WARNING:
            Exact frame cuts are not guaranteed with -c copy (cuts on keyframes).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files: List[str] = []

            for i, marker in enumerate(markers):
                if cancel_check and cancel_check():
                    return False

                start_time = marker.start_frame / fps
                end_time = marker.end_frame / fps
                duration = max(0.0, end_time - start_time)

                seg_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                # For stream copy best practice: put -ss BEFORE -i for speed, but accuracy is lower.
                # We'll keep it before -i for speed. If you want more accuracy, put -ss after -i.
                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(duration),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    "-y",
                    seg_path,
                ]

                # optionally drop audio
                if not include_audio:
                    cmd.insert(-2, "-an")

                VideoExporter._run_ffmpeg(cmd, "segment copy extraction failed")
                segment_files.append(seg_path)

                if progress_callback:
                    progress_callback(int((i + 1) / max(1, len(markers)) * 80))

            if merge_segments:
                if len(segment_files) == 1:
                    shutil.copy2(segment_files[0], output_path)
                else:
                    VideoExporter._concat_segments_copy(segment_files, output_path)

                if progress_callback:
                    progress_callback(100)
            else:
                VideoExporter._export_separate_files(segment_files, markers, output_path)
                if progress_callback:
                    progress_callback(100)

        return True

    @staticmethod
    def _concat_segments_copy(segment_files: List[str], output_path: str) -> None:
        """Concat already compatible segments using ffmpeg concat demuxer with -c copy."""
        concat_file = output_path + ".txt"
        try:
            with open(concat_file, "w", encoding="utf-8") as f:
                for seg in segment_files:
                    f.write(f"file '{seg}'\n")

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y",
                output_path,
            ]
            VideoExporter._run_ffmpeg(cmd, "ffmpeg concat failed")
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)

    # ──────────────────────────────────────────────────────────────────────
    # Re-encode (ffmpeg ultrafast or moviepy)
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _export_with_reencode(
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        codec: str,
        quality: int,
        resolution: Optional[str],
        include_audio: bool,
        merge_segments: bool,
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> bool:
        """Re-encode export.

        To keep dependencies minimal and predictable, we use ffmpeg directly
        with libx264/libx265 where possible.
        """
        # If you still want moviepy, keep it behind a flag.
        # Here: ffmpeg-based extraction for every segment, then concat.
        codec_norm = codec.lower()
        if codec_norm in ("h264", "libx264"):
            vcodec = "libx264"
        elif codec_norm in ("h265", "libx265"):
            vcodec = "libx265"
        else:
            vcodec = codec  # assume ffmpeg codec name

        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files: List[str] = []

            for i, marker in enumerate(markers):
                if cancel_check and cancel_check():
                    return False

                start_time = marker.start_frame / fps
                end_time = marker.end_frame / fps
                duration = max(0.0, end_time - start_time)

                seg_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(duration),
                    "-c:v", vcodec,
                    "-crf", str(int(quality)),
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                ]

                # resolution scaling
                vf = VideoExporter._resolution_vf(resolution)
                if vf:
                    cmd += ["-vf", vf]

                if include_audio:
                    cmd += ["-c:a", "aac"]
                else:
                    cmd += ["-an"]

                cmd += ["-avoid_negative_ts", "make_zero", "-y", seg_path]

                VideoExporter._run_ffmpeg(cmd, "segment re-encode extraction failed")
                segment_files.append(seg_path)

                if progress_callback:
                    progress_callback(int((i + 1) / max(1, len(markers)) * 80))

            if merge_segments:
                if len(segment_files) == 1:
                    shutil.copy2(segment_files[0], output_path)
                else:
                    # segments encoded uniformly above -> concat copy
                    VideoExporter._concat_segments_copy(segment_files, output_path)
                if progress_callback:
                    progress_callback(100)
            else:
                VideoExporter._export_separate_files(segment_files, markers, output_path)
                if progress_callback:
                    progress_callback(100)

        return True

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _run_ffmpeg(cmd: List[str], context: str) -> None:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"{context}: {stderr}")

    @staticmethod
    def _resolution_vf(resolution: Optional[str]) -> Optional[str]:
        if not resolution or resolution == "source":
            return None

        height_map = {
            "2160p": 2160,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360,
        }
        h = height_map.get(resolution)
        if not h:
            return None

        # keep aspect ratio, width auto
        return f"scale=-2:{h}"

    @staticmethod
    def _sanitize_filename(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "event"
        # replace invalid path chars with "_"
        text = re.sub(r'[\\/:*?"<>|]+', "_", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:80]

    @staticmethod
    def _export_separate_files(segment_files: List[str], markers: List[Marker], output_path: str) -> None:
        output_dir = os.path.dirname(output_path) or "."
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        for i, (seg_file, marker) in enumerate(zip(segment_files, markers)):
            safe_event = VideoExporter._sanitize_filename(marker.event_name)
            seg_out = os.path.join(output_dir, f"{base_name}_segment_{i+1:03d}_{safe_event}.mp4")
            shutil.copy2(seg_file, seg_out)

    # Legacy compatibility
    @staticmethod
    def export(video_path: str, markers: List[Marker], total_frames: int, fps: float, output_path: str, **kwargs) -> bool:
        return VideoExporter.export_segments(
            video_path=video_path,
            markers=markers,
            fps=fps,
            output_path=output_path,
            **kwargs
        )

    @staticmethod
    def _export_empty_clip(video_path: str, fps: float, output_path: str) -> bool:
        # minimal stub: export first 0.1 sec with re-encode
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", video_path,
            "-t", "0.1",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-y",
            output_path,
        ]
        VideoExporter._run_ffmpeg(cmd, "empty clip export failed")
        return True