import os
from typing import List
from .segment import Segment
import srt

def load_srt(path: str) -> List[Segment]:
    with open(path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    subs = list(srt.parse(content))
    segs = []
    for i, sub in enumerate(subs, start=1):
        start = sub.start.total_seconds()
        end = sub.end.total_seconds()
        text = sub.content.replace('\n', ' ').strip()
        segs.append(Segment(index=i, start=start, end=end, text=text))
    return segs

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
