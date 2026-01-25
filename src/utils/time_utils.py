def frames_to_time(frames: int, fps: float) -> str:
    """Convert frame count to time string (HH:MM:SS.mmm)."""
    if fps <= 0:
        return "00:00:00.000"
    
    total_seconds = frames / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds * 1000) % 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def time_to_frames(time_str: str, fps: float) -> int:
    """Convert time string (HH:MM:SS.mmm) to frame count."""
    try:
        parts = time_str.split(':')
        if len(parts) != 3:
            return 0
        
        hours = int(parts[0])
        minutes = int(parts[1])
        
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        return int(total_seconds * fps)
    except (ValueError, IndexError):
        return 0
