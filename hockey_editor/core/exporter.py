from typing import List, Optional
import os
import tempfile
import subprocess
from ..models.marker import Marker

class VideoExporter:
    @staticmethod
    def export(
        video_path: str,
        markers: List[Marker],
        total_frames: int,
        fps: float,
        output_path: str,
        codec: str = "libx264",
        quality: int = 23,
        resolution: Optional[str] = None,
        include_audio: bool = True,
        merge_segments: bool = True
    ):
        """
        Экспорт видео сегментов.
        Для codec="copy" использует быстрое перекодирование через ffmpeg (ultrafast preset).
        Для других кодеков использует moviepy с перекодированием.
        """
        try:
            # Проверяем, что входной файл существует
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Если выбран codec "copy", используем прямой вызов ffmpeg
            if codec.lower() == "copy":
                return VideoExporter._export_with_copy(video_path, markers, fps, output_path, merge_segments)

            # Для других кодеков используем moviepy с перекодированием
            return VideoExporter._export_with_moviepy(
                video_path, markers, total_frames, fps, output_path,
                codec, quality, resolution, include_audio, merge_segments
            )

        except ImportError as e:
            raise ImportError(f"moviepy is required for video export. Install it with: pip install moviepy. Error: {e}")
        except Exception as e:
            print(f"Export error: {e}")
            raise

    @staticmethod
    def _export_with_copy(video_path: str, markers: List[Marker], fps: float, output_path: str, merge_segments: bool = True):
        """
        Быстрый экспорт с использованием ffmpeg ultrafast preset для плавных стыков.
        Если merge_segments=True, объединяет сегменты в один файл.
        Если merge_segments=False, экспортирует каждый сегмент как отдельный файл.
        """
        print(f"Fast export using ultrafast encoding: {len(markers)} segments, merge_segments={merge_segments}")

        if not markers:
            # Если нет маркеров, создаем пустой файл (не имеет смысла для copy)
            raise ValueError("Cannot create empty clip with codec='copy'")

        # Создаем временную директорию для сегментов
        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files = []

            # Извлекаем каждый сегмент в отдельный файл
            for i, marker in enumerate(markers):
                start_time = marker.start_frame / fps
                end_time = marker.end_frame / fps
                duration = end_time - start_time

                segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

                print(f"  Extracting segment {i+1}: {marker.event_name} ({start_time:.2f}s - {end_time:.2f}s)")

                # Используем прямой вызов ffmpeg для быстрого извлечения сегмента с перекодированием
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_time),          # Время начала
                    '-i', video_path,                # Входной файл
                    '-t', str(duration),             # Длительность
                    '-c:v', 'libx264',               # Кодек видео
                    '-preset', 'ultrafast',          # Сверхбыстрый preset
                    '-crf', '23',                    # Качество (низкая потеря)
                    '-c:a', 'aac',                   # Перекодируем аудио для плавных стыков
                    '-avoid_negative_ts', 'make_zero', # Сбрасываем временные метки
                    '-y',                            # Перезаписываем выходной файл
                    segment_path                     # Выходной файл
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg segment extraction failed: {result.stderr}")

                segment_files.append(segment_path)

            # Выбор режима экспорта на основе merge_segments
            if merge_segments:
                # Объединяем сегменты в один файл
                if len(segment_files) == 1:
                    # Просто копируем единственный файл
                    import shutil
                    shutil.copy2(segment_files[0], output_path)
                else:
                    # Для нескольких сегментов выполняем конкатенацию через concat demuxer
                    VideoExporter._concatenate_segments(segment_files, output_path)
                print(f"Fast export completed successfully: {output_path}")
            else:
                # Экспортируем каждый сегмент как отдельный файл
                output_dir = os.path.dirname(output_path)
                base_name = os.path.splitext(os.path.basename(output_path))[0]

                exported_files = []
                for i, (segment_file, marker) in enumerate(zip(segment_files, markers)):
                    # Генерируем имя файла для каждого сегмента
                    segment_output_path = os.path.join(
                        output_dir,
                        f"{base_name}_segment_{i+1:03d}_{marker.event_name}.mp4"
                    )

                    # Копируем сегмент в финальное место
                    import shutil
                    shutil.copy2(segment_file, segment_output_path)
                    exported_files.append(segment_output_path)
                    print(f"  Exported segment {i+1}: {segment_output_path}")

                print(f"Fast export completed successfully: {len(exported_files)} separate files in {output_dir}")

        return True

    @staticmethod
    def _concatenate_segments(segment_files: List[str], output_path: str):
        """
        Конкатенирует несколько видео файлов с быстрым перекодированием используя ffmpeg.
        """
        # Создаем файл со списком для конкатенации
        concat_file = output_path + ".txt"
        try:
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")

            # Запускаем ffmpeg для конкатенации с быстрым перекодированием
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',       # Кодек видео
                '-preset', 'ultrafast',  # Сверхбыстрый preset
                '-crf', '23',            # Качество (низкая потеря)
                '-c:a', 'copy',          # Копируем аудио без изменений
                '-y',                    # Перезаписываем выходной файл
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr}")

        finally:
            # Удаляем временный файл
            if os.path.exists(concat_file):
                os.remove(concat_file)

    @staticmethod
    def _export_with_moviepy(
        video_path: str,
        markers: List[Marker],
        total_frames: int,
        fps: float,
        output_path: str,
        codec: str,
        quality: int,
        resolution: Optional[str],
        include_audio: bool,
        merge_segments: bool
    ):
        """
        Экспорт с использованием moviepy (для перекодирования).
        Если merge_segments=True, объединяет сегменты в один файл.
        Если merge_segments=False, экспортирует каждый сегмент как отдельный файл.
        """
        import moviepy as mp

        # Загружаем видео
        video = mp.VideoFileClip(video_path)

        # Настраиваем параметры экспорта
        export_params = {}

        # Кодек
        if codec.lower() in ["h264", "libx264"]:
            export_params["codec"] = "libx264"
        elif codec.lower() in ["h265", "libx265"]:
            export_params["codec"] = "libx265"
        elif codec.lower() == "mpeg4":
            export_params["codec"] = "libx264"  # Fallback to h264
        else:
            export_params["codec"] = codec

        # Аудио
        if include_audio:
            export_params["audio_codec"] = "aac"
        else:
            export_params["audio_codec"] = None

        # Качество (CRF для h264/h265)
        if quality >= 0 and quality <= 51:
            export_params["bitrate"] = None  # Используем CRF
            # Для moviepy CRF устанавливается через preset и quality
            if quality <= 18:
                export_params["preset"] = "slow"
            elif quality <= 23:
                export_params["preset"] = "medium"
            else:
                export_params["preset"] = "fast"

        if markers:
            print(f"Exporting {len(markers)} segments with re-encoding, merge_segments={merge_segments}")

            clips = []
            for marker in markers:
                # Конвертируем кадры в секунды
                start_time = marker.start_frame / fps
                end_time = marker.end_frame / fps

                # Создаем субклип
                subclip = video.subclipped(start_time, end_time)
                clips.append(subclip)

                print(f"  Segment: {marker.event_name} ({start_time:.2f}s - {end_time:.2f}s)")

            if merge_segments:
                # Объединяем сегменты в один файл
                if len(clips) > 1:
                    final_clip = mp.concatenate_videoclips(clips)
                else:
                    final_clip = clips[0]

                # Применяем разрешение к финальному клипу
                if resolution and resolution != "source":
                    if resolution == "2160p":
                        final_clip = final_clip.resized(height=2160)
                    elif resolution == "1080p":
                        final_clip = final_clip.resized(height=1080)
                    elif resolution == "720p":
                        final_clip = final_clip.resized(height=720)
                    elif resolution == "480p":
                        final_clip = final_clip.resized(height=480)
                    elif resolution == "360p":
                        final_clip = final_clip.resized(height=360)

                # Экспортируем объединенный клип
                final_clip.write_videofile(
                    output_path,
                    fps=fps,
                    threads=4,
                    logger=None,  # Отключаем verbose вывод
                    **export_params
                )

                # Освобождаем финальный клип
                final_clip.close()

                print(f"Re-encoding export completed successfully: {output_path}")
            else:
                # Экспортируем каждый сегмент как отдельный файл
                output_dir = os.path.dirname(output_path)
                base_name = os.path.splitext(os.path.basename(output_path))[0]

                exported_files = []
                for i, (clip, marker) in enumerate(zip(clips, markers)):
                    # Применяем разрешение к каждому клипу
                    segment_clip = clip
                    if resolution and resolution != "source":
                        if resolution == "2160p":
                            segment_clip = clip.resized(height=2160)
                        elif resolution == "1080p":
                            segment_clip = clip.resized(height=1080)
                        elif resolution == "720p":
                            segment_clip = clip.resized(height=720)
                        elif resolution == "480p":
                            segment_clip = clip.resized(height=480)
                        elif resolution == "360p":
                            segment_clip = clip.resized(height=360)

                    # Генерируем имя файла для каждого сегмента
                    segment_output_path = os.path.join(
                        output_dir,
                        f"{base_name}_segment_{i+1:03d}_{marker.event_name}.mp4"
                    )

                    # Экспортируем сегмент
                    segment_clip.write_videofile(
                        segment_output_path,
                        fps=fps,
                        threads=4,
                        logger=None,  # Отключаем verbose вывод
                        **export_params
                    )

                    exported_files.append(segment_output_path)
                    print(f"  Exported segment {i+1}: {segment_output_path}")

                    # Освобождаем клип, если он был изменен (изменение размера)
                    if segment_clip is not clip:
                        segment_clip.close()

                print(f"Re-encoding export completed successfully: {len(exported_files)} separate files in {output_dir}")

        else:
            # Если нет маркеров, создаем пустой клип (минимальная длительность)
            print(f"Creating empty clip: {output_path}")
            final_clip = video.subclipped(0, 0.1)

            # Экспортируем пустой клип
            final_clip.write_videofile(
                output_path,
                fps=fps,
                threads=4,
                logger=None,  # Отключаем verbose вывод
                **export_params
            )

            final_clip.close()

        # Освобождаем ресурсы
        video.close()

        return True
