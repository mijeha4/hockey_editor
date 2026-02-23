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

    Marker contract:
        start_frame inclusive, end_frame exclusive
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
        padding_before: float = 0.0,
        padding_after: float = 0.0,
        file_template: Optional[str] = None,
        progress_callback: ProgressCallback = None,
        cancel_check: CancelCheck = None,
    ) -> bool:
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if fps <= 0:
                fps = 30.0

            markers = sorted(markers, key=lambda m: (m.start_frame, m.end_frame))

            if not markers:
                return VideoExporter._export_empty_clip(video_path, fps, output_path)

            # ══════════════════════════════════════════════════════════
            # ★ ВАЛИДАЦИЯ output_path
            # ══════════════════════════════════════════════════════════

            output_path = VideoExporter._normalize_output_path(
                output_path, merge_segments
            )

            # Убедиться что директория существует
            out_dir = os.path.dirname(output_path) if merge_segments else output_path
            if not out_dir:
                out_dir = "."
            os.makedirs(out_dir, exist_ok=True)

            if cancel_check and cancel_check():
                return False

            # Общие kwargs
            kwargs = dict(
                video_path=video_path,
                markers=markers,
                fps=fps,
                output_path=output_path,
                include_audio=include_audio,
                merge_segments=merge_segments,
                padding_before=max(0.0, padding_before),
                padding_after=max(0.0, padding_after),
                file_template=file_template,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

            if codec.lower() == "copy":
                return VideoExporter._export_stream_copy(**kwargs)

            return VideoExporter._export_with_reencode(
                codec=codec, quality=quality, resolution=resolution,
                **kwargs
            )

        except Exception as e:
            print(f"Export error: {e}")
            raise

    # ──────────────────────────────────────────────────────────────────────
    # ★ Path normalization
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_output_path(output_path: str, merge_segments: bool) -> str:
        """Нормализовать output_path в зависимости от режима.

        merge_segments=True  → нужен ФАЙЛ с расширением
        merge_segments=False → нужна ДИРЕКТОРИЯ, но для _export_separate_files
                               нам всё равно нужен базовый файл-шаблон
        """
        output_path = output_path.strip()

        if merge_segments:
            # Нужен файл с расширением .mp4
            if os.path.isdir(output_path):
                # Путь — директория, добавляем имя файла
                output_path = os.path.join(output_path, "export.mp4")

            _base, ext = os.path.splitext(output_path)
            if not ext:
                # Нет расширения — добавляем .mp4
                output_path = output_path + ".mp4"
        else:
            # Нужна директория
            if os.path.isdir(output_path):
                # Для _export_separate_files нужен "файл-шаблон" внутри директории
                output_path = os.path.join(output_path, "segment.mp4")
            else:
                # Проверить — это файл или путь без расширения?
                _base, ext = os.path.splitext(output_path)
                if not ext:
                    # Путь без расширения — считаем директорией
                    os.makedirs(output_path, exist_ok=True)
                    output_path = os.path.join(output_path, "segment.mp4")
                # Если есть расширение — ОК, будет использован как шаблон

        return output_path

    # ──────────────────────────────────────────────────────────────────────
    # Stream copy
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _export_stream_copy(
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        include_audio: bool,
        merge_segments: bool,
        padding_before: float,
        padding_after: float,
        file_template: Optional[str],
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files: List[str] = []

            for i, marker in enumerate(markers):
                if cancel_check and cancel_check():
                    return False

                start_time = max(0.0, marker.start_frame / fps - padding_before)
                end_time = marker.end_frame / fps + padding_after
                duration = max(0.0, end_time - start_time)

                seg_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                cmd = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(duration),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                ]
                if not include_audio:
                    cmd += ["-an"]
                cmd += ["-y", seg_path]

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
                VideoExporter._export_separate_files(
                    segment_files, markers, output_path, fps, file_template
                )
                if progress_callback:
                    progress_callback(100)

        return True

    @staticmethod
    def _concat_segments_copy(segment_files: List[str], output_path: str) -> None:
        """Concat segments using ffmpeg concat demuxer."""
        # ★ Файл списка создаём во временной директории, не рядом с output
        import tempfile as _tmp
        concat_fd, concat_file = _tmp.mkstemp(suffix=".txt", prefix="ffconcat_")
        try:
            with os.fdopen(concat_fd, "w", encoding="utf-8") as f:
                for seg in segment_files:
                    # Используем абсолютные пути и экранируем одинарные кавычки
                    safe_path = os.path.abspath(seg).replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy", "-y", output_path,
            ]
            VideoExporter._run_ffmpeg(cmd, "ffmpeg concat failed")
        finally:
            try:
                os.remove(concat_file)
            except OSError:
                pass

    # ──────────────────────────────────────────────────────────────────────
    # Re-encode
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
        padding_before: float,
        padding_after: float,
        file_template: Optional[str],
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> bool:
        codec_norm = codec.lower()
        if codec_norm in ("h264", "libx264"):
            vcodec = "libx264"
        elif codec_norm in ("h265", "libx265"):
            vcodec = "libx265"
        else:
            vcodec = codec

        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files: List[str] = []

            for i, marker in enumerate(markers):
                if cancel_check and cancel_check():
                    return False

                start_time = max(0.0, marker.start_frame / fps - padding_before)
                end_time = marker.end_frame / fps + padding_after
                duration = max(0.0, end_time - start_time)

                seg_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                cmd = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(duration),
                    "-c:v", vcodec,
                    "-crf", str(int(quality)),
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                ]

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
                    VideoExporter._concat_segments_copy(segment_files, output_path)
                if progress_callback:
                    progress_callback(100)
            else:
                VideoExporter._export_separate_files(
                    segment_files, markers, output_path, fps, file_template
                )
                if progress_callback:
                    progress_callback(100)

        return True

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _run_ffmpeg(cmd: List[str], context: str) -> None:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"{context}: {stderr}")

    @staticmethod
    def _resolution_vf(resolution: Optional[str]) -> Optional[str]:
        if not resolution or resolution == "source":
            return None
        height_map = {
            "2160p": 2160, "1080p": 1080, "720p": 720,
            "480p": 480, "360p": 360,
        }
        h = height_map.get(resolution)
        return f"scale=-2:{h}" if h else None

    @staticmethod
    def _sanitize_filename(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "event"
        text = re.sub(r'[\\/:*?"<>|]+', "_", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:80]

    @staticmethod
    def _export_separate_files(
        segment_files: List[str],
        markers: List[Marker],
        output_path: str,
        fps: float = 30.0,
        file_template: Optional[str] = None,
    ) -> None:
        """Сохранить сегменты как отдельные файлы.

        output_path используется для определения директории и базового имени.
        """
        # ★ Определить директорию и базовое имя
        if os.path.isdir(output_path):
            output_dir = output_path
            base_name = "segment"
        else:
            output_dir = os.path.dirname(output_path) or "."
            base_name = os.path.splitext(os.path.basename(output_path))[0]

        os.makedirs(output_dir, exist_ok=True)

        for i, (seg_file, marker) in enumerate(zip(segment_files, markers)):
            safe_event = VideoExporter._sanitize_filename(marker.event_name)

            if file_template:
                start_secs = marker.start_frame / fps if fps > 0 else 0
                dur_secs = (marker.end_frame - marker.start_frame) / fps if fps > 0 else 0
                try:
                    filename = file_template.format_map({
                        "event": safe_event,
                        "index": f"{i + 1:03d}",
                        "time": f"{int(start_secs) // 60:02d}-{int(start_secs) % 60:02d}",
                        "duration": f"{dur_secs:.0f}",
                        "project": base_name,
                    })
                except (KeyError, ValueError, IndexError):
                    filename = f"{base_name}_{i + 1:03d}_{safe_event}"
            else:
                filename = f"{base_name}_{i + 1:03d}_{safe_event}"

            filename = VideoExporter._sanitize_filename(filename)
            seg_out = os.path.join(output_dir, f"{filename}.mp4")

            # ★ Не перезаписывать существующие — добавить суффикс
            if os.path.exists(seg_out):
                counter = 1
                while os.path.exists(seg_out):
                    seg_out = os.path.join(
                        output_dir, f"{filename}_{counter}.mp4"
                    )
                    counter += 1

            shutil.copy2(seg_file, seg_out)

    # ──────────────────────────────────────────────────────────────────────
    # Legacy compatibility
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def export(video_path, markers, total_frames, fps, output_path, **kwargs):
        return VideoExporter.export_segments(
            video_path=video_path, markers=markers,
            fps=fps, output_path=output_path, **kwargs
        )

    @staticmethod
    def _export_empty_clip(video_path: str, fps: float, output_path: str) -> bool:
        # Нормализовать путь
        if os.path.isdir(output_path) or not os.path.splitext(output_path)[1]:
            if os.path.isdir(output_path):
                output_path = os.path.join(output_path, "empty.mp4")
            else:
                output_path = output_path + ".mp4"

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", video_path, "-t", "0.1",
            "-c:v", "libx264", "-crf", "23",
            "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-y", output_path,
        ]
        VideoExporter._run_ffmpeg(cmd, "empty clip export failed")
        return True