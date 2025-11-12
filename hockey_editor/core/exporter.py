from moviepy import VideoFileClip, concatenate_videoclips
from typing import List
from models.marker import Marker

class VideoExporter:
    @staticmethod
    def export(video_path: str, markers: List[Marker], total_frames: int, fps: float, output_path: str):
        video = VideoFileClip(video_path)
        clips = []
        markers_with_end = markers + [Marker(frame=total_frames, type=None)]
        
        for i in range(len(markers)):
            start_sec = markers[i].frame / fps
            end_sec = markers_with_end[i + 1].frame / fps
            clip = video.subclip(start_sec, end_sec)
            clips.append(clip)
        
        final = concatenate_videoclips(clips)
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=4)
        video.close()