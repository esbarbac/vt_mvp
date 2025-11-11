from typing import List
from .segment import Segment
import os
from openai import OpenAI

class Translator:
    def __init__(self, openai_api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for translation.")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.model = model

    def translate_segments(self, segments: List[Segment], source_lang: str = "en", target_lang: str = "de") -> List[Segment]:
        out = []
        for s in segments:
            text = self.translate_text(s.text, source_lang, target_lang)
            out.append(Segment(s.index, s.start, s.end, text))
        return out

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        # Use Responses API for deterministic, concise translation
        prompt = (
            f"Translate the following {source_lang} text into {target_lang}. "
            "Keep meaning, tone, and style natural for voiceover. "
            "Do NOT add punctuation or words not present unless needed for fluent German.\n\n"
            f"Text: {text}"
        )
        resp = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.2,
        )
        return resp.output_text.strip()
