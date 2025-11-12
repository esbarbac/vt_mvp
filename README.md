# English ➜ German Video Translator

Translate an English-captioned video into **German** while preserving identity, tone, and quality of the original audio in a **Streamlit app**.

---

## What it does (TL;DR)

- **Parses SRT captions** and normalizes multi-line cues
- **Translates** each cue **EN → DE** using an OpenAI LLM.
- **Clones the speaker’s voice** from a short sample (ElevenLabs IVC)
- **Synthesizes German audio per segment** (ElevenLabs TTS)
- **Renders the final MP4** and an **audio-only MP3**

> This app requires **both**: `OPENAI_API_KEY` (translation), and `ELEVEN_API_KEY` (TTS/voice cloning).

---

## Architecture

```
vt_mvp/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .env
├─ .gitignore
├─ src/
  ├─ init.py
  ├─ segment.py         # Dataclass: (index, start, end, text)
  ├─ translate.py       # OpenAI GPT-4o-mini translation EN ➜ DE
  ├─ voice_generator.py # ElevenLabs voice cloning + TTS
  ├─ video_editor.py    # MoviePy: retiming & composition
  └─ utils.py           # SRT parsing + helpers

```

Key design choices:

- **Segment-by-segment pipeline** keeps timing predictable and debuggable.
- **Speech speed-control** keeps scene boundaries intact without hard cuts.

---

## Quickstart

### Clone the repository
```bash
git clone https://github.com/esbarbac/vt_mvp.git
cd vt_mvp
```

### 1) Install system dependency

- **FFmpeg** is required by MoviePy and pydub.

macOS (Homebrew):
```bash
brew install ffmpeg
```

Ubuntu/Debian:
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

Windows

Option 1 — using **Chocolatey** (recommended):

```powershell
choco install ffmpeg
```

Option 2 — manual install (in case option 1 is not possible):

1. Go to [https://ffmpeg.org/download.html]
2. Download the **Windows build** (e.g., `ffmpeg-release-essentials.zip`).
3. Extract it (to `C:\ffmpeg\bin`).
4. Add `C:\ffmpeg\bin` to your **PATH** in System Environment Variables.

---

### 2) Create & activate a Python env
Using conda:

```bash
conda create -n vt-mvp python=3.11 -y
conda activate vt-mvp
```

### 3) Install Python deps
```bash
pip install -r requirements.txt
```

### 4) Set your OpenAI & elevenlabs API Keys
`.env` and set your keys:

```
OPENAI_API_KEY=your-api-key-here
ELEVEN_API_KEY=your-api-key-here
# Optional:
ELEVEN_MODEL=eleven_multilingual_v2  # default model for TTS
ELEVEN_VOICE_ID=                     # leave empty to auto-clone from video sample
OPENAI_MODEL=gpt-4o-mini             # default translation model
```

### 5) Run the app
```bash
streamlit run app.py
```

Upload:
- **Video** (`.mp4/.mov/.mkv`)
- **English SRT** (`.srt`)

Then click **“Run Translation to German”**. You’ll get:
- `translated_video.mp4`
- `translated_audio.mp3`

---

## Configuration

- **Translation model**: `OPENAI_MODEL` (default: `gpt-4o-mini`)
- **ElevenLabs model**: `ELEVEN_MODEL` (default: `eleven_multilingual_v2`)
- **Cloning**: A short sample (`~3–20s`) is auto-extracted from the uploaded video.

If you already have an ElevenLabs **voice ID**, set `ELEVEN_VOICE_ID` in `.env` to skip cloning.

---

## Troubleshooting

- **“Missing API keys”** — You must set *both* `OPENAI_API_KEY` and `ELEVEN_API_KEY`.
- **FFmpeg errors** — Make sure `ffmpeg` is installed and on your PATH.
- **ElevenLabs voice cloning** — Some accounts need IVC enabled. If cloning fails, set an existing `ELEVEN_VOICE_ID`.
- **Out of memory / slow export** — Large videos can be heavy. Try a shorter clip for validation, then scale up.

---

## Constraints

- **No TTS fallback**: ElevenLabs is the single TTS provider.
- **No full lipsync**: This MVP focuses on segment alignment and natural pacing; frame-level lipsync is out of scope. Good results can be achieved with wav2lip, however this is computationaly heavy, requiring GPUs for timely results. 
- **Deterministic translation**: Low temperature, per-cue prompts optimized for narration quality.

Perfect — here’s a concise, professional section you can place right after the “Pipeline Overview” in your README:

---

## Assumptions About the SRT File Format

The pipeline expects the subtitle file to follow the **standard SubRip (SRT) format** used by most captioning and editing tools.

### Required format

Each subtitle block must contain:

1. **A sequential index number** (starting from 1)
2. **Start and end timestamps** in the format `HH:MM:SS,mmm --> HH:MM:SS,mmm`
3. **One or more lines of text**

Example:

```
1
00:00:00,000 --> 00:00:04,500
Tanzania—home to some of the most breathtaking wildlife on Earth.

2
00:00:04,500 --> 00:00:08,000
Here, in the heart of East Africa, the great Serengeti unfolds.
```

---

## Pipeline Overview: From Upload to Final Output

The **VT_MVP pipeline** automates the entire video translation workflow, from ingesting the original video and English captions to delivering a fully retimed, voice-cloned German version. Below is a step-by-step breakdown of what happens internally:

### 1. **File Upload and Validation**

Users upload two files through the Streamlit interface:

* A **video file** (`.mp4`, `.mov`, `.mkv`)
* A **subtitle file** in **SRT format** (`.srt`)

Both files are stored temporarily and validated. The app stops early if either file or the required API keys (`OPENAI_API_KEY`, `ELEVEN_API_KEY`) are missing.

---

### 2. **Subtitle Parsing and Structuring**

The srt file is parsed using `load_srt()` (in `src/utils.py`), which converts each subtitle block into a `Segment` dataclass containing:

```python
Segment(index, start, end, text)
```

This standardizes timestamps and text, ensuring clean and reliable processing downstream.

---

### 3. **Translation (OpenAI)**

The `Translator` class (`src/translate.py`) processes each English segment with OpenAI’s `gpt-4o-mini` model:

* Translation is performed **segment-by-segment** for precision and timing consistency.
* The German text replaces the English captions while preserving the original start/end timestamps.
* Output: a new list of `Segment` objects containing the German text.

This approach guarantees localized, fluent sentences that align naturally with subtitle boundaries, ideal for dubbing.

---

### 4. **Voice Cloning (ElevenLabs)**

Before generating any speech, the system extracts a **3–20 second audio sample** from the uploaded video (using `moviepy`):

```python
clip.audio.subclip(0, sample_duration).write_audiofile("sample.wav")
```

The `VoiceGenerator` class then:

1. Sends this sample to ElevenLabs’ Instant Voice Cloning (IVC) API.
2. Receives a unique `voice_id` corresponding to the cloned voice.

This `voice_id` is cached and used for all subsequent speech synthesis.

---

### 5. **Text-to-Speech Generation (ElevenLabs)**

For each translated German segment:

* ElevenLabs’ TTS engine (`eleven_multilingual_v2`) generates natural speech in the cloned voice.
* Each output segment is saved as an individual MP3 file (`output/audio/seg_0001.mp3`, etc.).
* The duration of each generated file is measured and recorded.

These audio snippets now represent the **complete German narration**, aligned segment-by-segment.

---

### 6. **Video Retiming and Assembly**

The `create_final_video()` function (`src/video_editor.py`) combines the new German audio segments with the original video:

* Each video segment is trimmed or extended to match its corresponding TTS duration.
* If the video and audio clip have different lenghts. The video clip is adjusted to match the audio clip to maintain sync.
* Segments are concatenated seamlessly using **MoviePy**.

The final result: a fully synchronized video (`output/final_video_de.mp4`) with clean transitions and consistent pacing.

---

### 7. **User Output & Downloads**

Once processing is complete, the app:

* Displays the finished German video directly in the Streamlit interface (`st.video()`).
* Offers **download buttons** for both:

  * 🎬 The translated video (MP4)
  * 🎧 The German audio track (MP3)

---

### Summary Flow Diagram

```
[Upload Video + SRT]
          ↓
     Parse Captions
          ↓
  Translate (EN → DE)
          ↓
    Clone Voice Sample
          ↓
 Generate German Speech
          ↓
   Retimed Video Editing
          ↓
   Export MP4 + MP3 Outputs
```
