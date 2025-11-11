import os, io, time
from typing import List, Dict, Optional
from dataclasses import dataclass
from pydub import AudioSegment
from .segment import Segment

# ElevenLabs
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

DEFAULT_ELEVEN_MODEL = "eleven_multilingual_v2"

@dataclass
class AudioItem:
    index: int
    path: str
    duration: float

class VoiceGenerator:
    def __init__(
        self,
        out_dir: str = "output/audio",
        eleven_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        eleven_model: str = DEFAULT_ELEVEN_MODEL,
        stability: float = 0.45,
        similarity_boost: float = 0.7,
        style: float = 0.2,
        use_speaker_boost: bool = True,
    ):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

        self.eleven_api_key = eleven_api_key or os.environ.get("ELEVEN_API_KEY")
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.eleven_model = eleven_model

        self.eleven = ElevenLabs(api_key=self.eleven_api_key) if self.eleven_api_key else None
        self.openai = OpenAIClient(api_key=self.openai_api_key) if self.openai_api_key else None

        self.voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
        )

        self._cached_voice_id: Optional[str] = None

    # ---------------- Voice cloning ----------------
    def clone_voice_from_sample(self, sample_wav_path: str, name: str = "auto_clone") -> str:
        """Create an Instant Voice Clone via ElevenLabs API and return voice_id."""
        if not self.eleven:
            raise ValueError("ElevenLabs client not initialized. ELEVEN_API_KEY is required.")

        # Read the sample audio file
        with open(sample_wav_path, "rb") as f:
            sample_bytes = f.read()

        # Create the voice clone using the "ivc.create" method
        voice = self.eleven.voices.ivc.create(
            name=name,
            description="Auto-clone from VT MVP sample",
            files=[("sample.wav", sample_bytes)]
        )

        voice_id = getattr(voice, "voice_id", None) or getattr(voice, "id", None)
        if not voice_id:
            raise RuntimeError("Failed to obtain voice_id after clone request.")

        self._cached_voice_id = voice_id
        return voice_id

    def ensure_voice(self, sample_wav_path: Optional[str]) -> Optional[str]:
        if self._cached_voice_id:
            return self._cached_voice_id
        if self.eleven and sample_wav_path:
            return self.clone_voice_from_sample(sample_wav_path)
        return None

    # ---------------- Synthesis ----------------
    def generate_audio_segments(
        self,
        segments: List[Segment],
        prefer: str = "elevenlabs",
        voice_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate audio files for each translated segment.
        Prints the duration of each synthesized clip for debugging.
        """
        results: List[Dict] = []

        if prefer == "elevenlabs" and self.eleven:
            if not voice_id and not self._cached_voice_id:
                raise ValueError("No ElevenLabs voice_id available. Call ensure_voice() first or pass voice_id.")

            vid = voice_id or self._cached_voice_id

            print("\n Generating ElevenLabs audio segments...\n")

            for seg in segments:
                text = (seg.text or "").strip()
                out_path = os.path.join(self.out_dir, f"seg_{seg.index:04d}.mp3")

                # Synthesize or create silent filler
                if text:
                    audio_bytes = self._synthesize_eleven(text, vid)
                    with open(out_path, "wb") as f:
                        f.write(audio_bytes)
                else:
                    AudioSegment.silent(
                        duration=max(200, int((seg.end - seg.start) * 1000))
                    ).export(out_path, format="mp3")

                # Measure and display duration
                dur = AudioSegment.from_file(out_path).duration_seconds
                print(f"[Segment {seg.index:03d}] → {dur:.2f} seconds | Text: {text[:60]}")

                results.append({
                    "index": seg.index,
                    "path": out_path,
                    "duration": dur
                })

            print("\n Finished generating ElevenLabs audio segments.\n")
            return results

    

    def _synthesize_eleven(self, text: str, voice_id: str) -> bytes:
        # Non-streaming synthesis to MP3 bytes
        audio = self.eleven.text_to_speech.convert(
            voice_id=voice_id,
            model_id=self.eleven_model,
            output_format="mp3_44100_128",
            text=text,
            voice_settings=self.voice_settings,
        )
        buf = io.BytesIO()
        for chunk in audio:
            buf.write(chunk)
        return buf.getvalue()

    def _synthesize_openai_tts(self, text: str) -> bytes:
        # Uses OpenAI Audio API; model name may evolve. 'gpt-4o-mini-tts' widely available.
        resp = self.openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            format="mp3",
        )
        return resp.read()
