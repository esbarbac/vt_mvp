from dataclasses import dataclass

@dataclass
class Segment:
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str
