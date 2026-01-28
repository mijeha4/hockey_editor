from dataclasses import dataclass

@dataclass
class Marker:
    id: int
    start_time: float
    end_time: float
    label: str