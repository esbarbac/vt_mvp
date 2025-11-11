import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip

from src.utils import load_srt, ensure_dir
from src.translate import Translator
from src.voice_generator import VoiceGenerator
from src.video_editor import create_final_video

# ------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# ------------------------------------------------------------------
# Streamlit setup
# ------------------------------------------------------------------
st.set_page_config(
    page_title="VT MVP — Translate to German",
    page_icon="🎬",
    layout="centered"
)
st.title("🎬 VT MVP — English ➜ German Video Translator")
st.caption("Translates captions, clones voice automatically, and retimes the video to match German speech.")

uploaded_video = st.file_uploader("Upload source video (mp4/mov/mkv)", type=["mp4", "mov", "mkv"])
uploaded_srt = st.file_uploader("Upload SRT captions (English)", type=["srt"])
run = st.button("Run Translation to German")

# ------------------------------------------------------------------
# Main process
# ------------------------------------------------------------------
if run:
    if not uploaded_video or not uploaded_srt:
        st.error("Please upload both a video and an SRT file.")
        st.stop()

    if not OPENAI_API_KEY or not ELEVEN_API_KEY:
        st.error("Missing API keys. Add them to your `.env` file.")
        st.stop()

    status = st.empty()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save inputs
        video_path = os.path.join(tmpdir, uploaded_video.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())

        srt_path = os.path.join(tmpdir, uploaded_srt.name)
        with open(srt_path, "wb") as f:
            f.write(uploaded_srt.read())

        # Step 1: Parse SRT
        status.info("📖 Parsing subtitles...")
        segments = load_srt(srt_path)

        # Step 2: Translate English → German
        status.info("🔁 Translating text to German...")
        translator = Translator(openai_api_key=OPENAI_API_KEY)
        segments_de = translator.translate_segments(segments, "en", "de")

        # Step 3: Extract voice sample
        status.info("🎙 Extracting short voice sample from video...")
        clip = VideoFileClip(video_path)
        sample_duration = min(20, max(3, clip.duration))
        sample_wav = os.path.join(tmpdir, "sample.wav")
        clip.audio.subclip(0, sample_duration).write_audiofile(
            sample_wav, fps=44100, nbytes=2, codec="pcm_s16le", verbose=False
        )
        clip.close()

        # Step 4: Clone voice and generate German TTS
        status.info("🧬 Cloning voice and generating German TTS...")
        vg = VoiceGenerator(out_dir="output/audio", eleven_api_key=ELEVEN_API_KEY)
        voice_id = vg.ensure_voice(sample_wav)

        # Step 5: Generate audio segments
        status.info("🔊 Synthesizing German audio segments...")
        audio_items = vg.generate_audio_segments(segments_de, voice_id=voice_id)

        # Step 6: Assemble final video
        status.info("🎞 Assembling final translated video (this may take a few minutes)...")
        ensure_dir("output")
        out_path = "output/final_video_de.mp4"
        out_path = create_final_video(video_path, segments_de, audio_items, out_path=out_path)

        # Step 7: Extract final audio track
        status.info("🎧 Exporting German audio track...")
        audio_out_path = "output/final_audio_de.mp3"
        audio_clip = AudioFileClip(out_path)
        audio_clip.write_audiofile(audio_out_path, verbose=False)
        audio_clip.close()

        # Step 8: Display results
        status.success("✅ Translation complete!")

        st.video(out_path)
        col1, col2 = st.columns(2)
        with col1:
            with open(out_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Translated Video (MP4)",
                    f,
                    file_name="final_video_de.mp4",
                    mime="video/mp4",
                )
        with col2:
            with open(audio_out_path, "rb") as f:
                st.download_button(
                    "🎧 Download German Audio Only (MP3)",
                    f,
                    file_name="final_audio_de.mp3",
                    mime="audio/mpeg",
                )

        status.empty()
