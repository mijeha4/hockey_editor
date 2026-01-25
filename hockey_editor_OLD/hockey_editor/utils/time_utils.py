def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def frames_to_time(frames: int, fps: float) -> str:
    """Convert frame number to time string in format MM:SS.FF"""
    if fps <= 0:
        return "00:00.00"

    total_seconds = frames / fps
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    frames_remainder = frames % int(fps)
    return f"{minutes:02d}:{seconds:02d}.{frames_remainder:02d}"


def time_to_frames(time_str: str, fps: float) -> int:
    """Convert time string in format MM:SS.FF to frame number"""
    if fps <= 0:
        return 0

    try:
        # Handle different time formats
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                # MM:SS format
                minutes = int(parts[0])
                seconds_part = parts[1]
                if '.' in seconds_part:
                    seconds, frames = seconds_part.split('.')
                    seconds = int(seconds)
                    frames = int(frames)
                else:
                    seconds = int(seconds_part)
                    frames = 0
            elif len(parts) == 3:
                # HH:MM:SS format - convert to minutes
                hours = int(parts[0])
                minutes = int(parts[1]) + hours * 60
                seconds_part = parts[2]
                if '.' in seconds_part:
                    seconds, frames = seconds_part.split('.')
                    seconds = int(seconds)
                    frames = int(frames)
                else:
                    seconds = int(seconds_part)
                    frames = 0
            else:
                return 0
        else:
            # Assume seconds only
            total_seconds = float(time_str)
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            frames = int((total_seconds % 1) * fps)

        # Convert to frames
        total_frames = int((minutes * 60 + seconds) * fps + frames)
        return max(0, total_frames)
    except (ValueError, IndexError):
        return 0


def validate_time_format(time_str: str) -> bool:
    """Validate time string format (MM:SS.FF)"""
    import re
    # Match patterns like 00:00.00, 1:23.45, 12:34.56, etc.
    # Must have minutes:seconds.frames format
    pattern = r'^\d{1,3}:\d{1,2}\.\d{1,2}$'
    return bool(re.match(pattern, time_str))
