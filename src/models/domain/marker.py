from typing import Dict, Any


class Marker:
    """>45;L <0@:5@0 4;O E>::59=>3> 2845>."""
    
    def __init__(self, id: int, start_frame: int, end_frame: int, event_name: str, note: str = ""):
        self.id = id
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.event_name = event_name
        self.note = note
    
    def to_marker(self):
        """Convert to legacy Marker format for compatibility."""
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """>=25@B8@>20BL <0@:5@ 2 A;>20@L."""
        return {
            "id": self.id,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "event_name": self.event_name,
            "note": self.note
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Marker':
        """!>740BL <0@:5@ 87 A;>20@O."""
        return cls(
            id=data["id"],
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=data["event_name"],
            note=data.get("note", "")
        )
    
    def __repr__(self):
        return f"Marker(id={self.id}, start_frame={self.start_frame}, end_frame={self.end_frame}, event_name='{self.event_name}', note='{self.note}')"
    
    def __eq__(self, other):
        if not isinstance(other, Marker):
            return False
        return (self.id == other.id and 
                self.start_frame == other.start_frame and 
                self.end_frame == other.end_frame and 
                self.event_name == other.event_name and 
                self.note == other.note)
