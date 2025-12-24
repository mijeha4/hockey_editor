from typing import List, Optional
import os
import tempfile
import subprocess

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.domain.marker import Marker


class VideoExporter:
    """Сервис для экспорта видео сегментов."""

    def export_segments(
        self,
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        codec: str = "libx264",
        quality: int = 23,
        resolution: Optional[str] = None,
        include_audio: bool = True,
        merge_segments: bool = True
    ) -> bool:
        """
        Экспорт видео сегментов.

        Args:
            video_path: Путь к исходному видео
            markers: Список маркеров для экспорта
            fps: FPS видео
            output_path: Путь для сохранения результата
            codec: Кодек видео ("libx264", "copy", etc.)
            quality: Качество (CRF для h264/h265, 0-51)
            resolution: Разрешение ("source", "2160p", "1080p", "720p", etc.)
            include_audio: Включать ли аудио
            merge_segments: Объединять ли сегменты в один файл

        Returns:
            True если экспорт успешен
        """
        try:
            # Проверяем входные данные
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if not markers:
                raise ValueError("No markers to export")

            # Выбираем метод экспорта
            if codec.lower() == "copy":
                return self._export_with_copy(video_path, markers, fps, output_path, merge_segments)
            else:
                return self._export_with_moviepy(
                    video_path, markers, fps, output_path,
                    codec, quality, resolution, include_audio, merge_segments
                )

        except ImportError as e:
            raise ImportError(f"moviepy is required for video export. Install it with: pip install moviepy. Error: {e}")
        except Exception as e:
            print(f"Export error: {e}")
            raise

    def _export_with_copy(
        self,
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        merge_segments: bool = True
    ) -> bool:
        """
        Быстрый экспорт с использованием ffmpeg ultrafast preset.
        """
        print(f"Fast export using ultrafast encoding: {len(markers)} segments, merge_segments={merge_segments}")

        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files = []

            # Извлекаем каждый сегмент
            for i, marker in enumerate(markers):
                start_time = marker.start_frame / fps
                end_time = marker.end_frame / fps
                duration = end_time - start_time

                segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                print(f"  Extracting segment {i+1}: {marker.event_name} ({start_time:.2f}s - {end_time:.2f}s)")

                # FFmpeg команда для извлечения сегмента
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_time),
                    '-i', video_path,
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-avoid_negative_ts', 'make_zero',
                    '-y',
                    segment_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg segment extraction failed: {result.stderr}")

                segment_files.append(segment_path)

            # Объединяем или сохраняем отдельно
            if merge_segments:
                if len(segment_files) == 1:
                    import shutil
                    shutil.copy2(segment_files[0], output_path)
                else:
                    self._concatenate_segments(segment_files, output_path)
                print(f"Fast export completed successfully: {output_path}")
            else:
                self._export_separate_files(segment_files, markers, output_path)
                output_dir = os.path.dirname(output_path)
                print(f"Fast export completed successfully: {len(segment_files)} separate files in {output_dir}")

        return True

    def _concatenate_segments(self, segment_files: List[str], output_path: str) -> None:
        """Конкатенирует сегменты с помощью ffmpeg."""
        concat_file = output_path + ".txt"
        try:
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-c:a', 'copy',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr}")

        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)

    def _export_separate_files(
        self,
        segment_files: List[str],
        markers: List[Marker],
        output_path: str
    ) -> None:
        """Экспортирует каждый сегмент как отдельный файл."""
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        for i, (segment_file, marker) in enumerate(zip(segment_files, markers)):
            segment_output_path = os.path.join(
                output_dir,
                f"{base_name}_segment_{i+1:03d}_{marker.event_name}.mp4"
            )

            import shutil
            shutil.copy2(segment_file, segment_output_path)
            print(f"  Exported segment {i+1}: {segment_output_path}")

    def _export_with_moviepy(
        self,
        video_path: str,
        markers: List[Marker],
        fps: float,
        output_path: str,
        codec: str,
        quality: int,
        resolution: Optional[str],
        include_audio: bool,
        merge_segments: bool
    ) -> bool:
        """Экспорт с перекодированием через moviepy."""
        import moviepy as mp

        video = mp.VideoFileClip(video_path)

        # Настраиваем параметры экспорта
        export_params = self._prepare_export_params(codec, quality, include_audio)

        print(f"Exporting {len(markers)} segments with re-encoding, merge_segments={merge_segments}")

        clips = []
        for marker in markers:
            start_time = marker.start_frame / fps
            end_time = marker.end_frame / fps

            subclip = video.subclipped(start_time, end_time)
            clips.append(subclip)

            print(f"  Segment: {marker.event_name} ({start_time:.2f}s - {end_time:.2f}s)")

        if merge_segments:
            # Объединяем в один файл
            final_clip = mp.concatenate_videoclips(clips) if len(clips) > 1 else clips[0]
            final_clip = self._apply_resolution(final_clip, resolution)

            final_clip.write_videofile(
                output_path,
                fps=fps,
                threads=4,
                logger=None,
                **export_params
            )

            final_clip.close()
            print(f"Re-encoding export completed successfully: {output_path}")
        else:
            # Экспортируем отдельно
            self._export_separate_clips(clips, markers, output_path, fps, export_params, resolution)

        video.close()
        return True

    def _prepare_export_params(self, codec: str, quality: int, include_audio: bool) -> dict:
        """Подготавливает параметры экспорта для moviepy."""
        params = {}

        # Кодек
        if codec.lower() in ["h264", "libx264"]:
            params["codec"] = "libx264"
        elif codec.lower() in ["h265", "libx265"]:
            params["codec"] = "libx265"
        else:
            params["codec"] = codec

        # Аудио
        params["audio_codec"] = "aac" if include_audio else None

        # Качество
        if 0 <= quality <= 51:
            if quality <= 18:
                params["preset"] = "slow"
            elif quality <= 23:
                params["preset"] = "medium"
            else:
                params["preset"] = "fast"

        return params

    def _apply_resolution(self, clip, resolution: Optional[str]):
        """Применяет разрешение к клипу."""
        if not resolution or resolution == "source":
            return clip

        height_map = {
            "2160p": 2160,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360
        }

        if resolution in height_map:
            return clip.resized(height=height_map[resolution])

        return clip

    def _export_separate_clips(
        self,
        clips: list,
        markers: List[Marker],
        output_path: str,
        fps: float,
        export_params: dict,
        resolution: Optional[str]
    ) -> None:
        """Экспортирует клипы как отдельные файлы."""
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        for i, (clip, marker) in enumerate(zip(clips, markers)):
            segment_clip = self._apply_resolution(clip, resolution)

            segment_output_path = os.path.join(
                output_dir,
                f"{base_name}_segment_{i+1:03d}_{marker.event_name}.mp4"
            )

            segment_clip.write_videofile(
                segment_output_path,
                fps=fps,
                threads=4,
                logger=None,
                **export_params
            )

            if segment_clip is not clip:
                segment_clip.close()

            print(f"  Exported segment {i+1}: {segment_output_path}")

        print(f"Re-encoding export completed successfully: {len(clips)} separate files in {output_dir}")
