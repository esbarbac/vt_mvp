import os
from typing import List, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx
from .segment import Segment
from .utils import ensure_dir

def create_final_video(video_path: str, segments: List[Segment], audio_items: List[Dict], out_path: str) -> str:
    """
    Create the final video by aligning each translated audio segment
    with its corresponding video segment using playback speed changes:
      - If German audio is longer  -> slow down video.
      - If German audio is shorter -> speed up video slightly to fit.
    """
    ensure_dir(os.path.dirname(out_path))
    base_clip = VideoFileClip(video_path)
    subclips = []

    for seg, audio_item in zip(segments, audio_items):
        start_t, end_t = seg.start, seg.end
        segment_clip = base_clip.subclip(start_t, end_t)

        # New German audio for this segment
        seg_audio = AudioFileClip(audio_item["path"])
        seg_audio_dur = seg_audio.duration
        seg_video_dur = segment_clip.duration

        # Compute speed factor to match durations using speed changes only
        # MoviePy's speedx:
        #   factor > 1.0 -> faster (shorter)
        #   factor < 1.0 -> slower (longer)
        if seg_audio_dur != seg_video_dur and seg_audio_dur > 0:
            factor = seg_video_dur / seg_audio_dur
            segment_clip = segment_clip.fx(vfx.speedx, factor)

        # Attach the German audio after timing adjustment
        segment_clip = segment_clip.set_audio(seg_audio)
        subclips.append(segment_clip)

    final_clip = concatenate_videoclips(subclips, method="compose")
    final_clip.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, verbose=False)

    # Cleanup
    final_clip.close()
    base_clip.close()

    return out_path
