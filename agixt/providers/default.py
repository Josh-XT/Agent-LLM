from providers.gpt4free import Gpt4freeProvider
from providers.google import GoogleProvider
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from faster_whisper import WhisperModel
import os
import logging
import numpy as np

# Default provider uses:
# llm: gpt4free
# tts: google
# transcription: faster-whisper
# translation: faster-whisper


class DefaultProvider:
    """
    The default provider uses free or built-in services for various tasks like LLM, TTS, transcription, translation, and embeddings.
    """

    def __init__(
        self,
        DEFAULT_MODEL: str = "mixtral-8x7b",
        DEFAULT_MAX_TOKENS: int = 16000,
        **kwargs,
    ):
        self.friendly_name = "Default"
        self.AI_MODEL = DEFAULT_MODEL if DEFAULT_MODEL else "mixtral-8x7b"
        self.AI_TEMPERATURE = 0.7
        self.AI_TOP_P = 0.7
        self.MAX_TOKENS = DEFAULT_MAX_TOKENS if DEFAULT_MAX_TOKENS else 16000
        self.TRANSCRIPTION_MODEL = (
            "base"
            if "TRANSCRIPTION_MODEL" not in kwargs
            else kwargs["TRANSCRIPTION_MODEL"]
        )
        self.embedder = ONNXMiniLM_L6_V2()
        self.embedder.DOWNLOAD_PATH = os.getcwd()
        self.chunk_size = 256

    @staticmethod
    def services():
        return [
            "llm",
            "embeddings",
            "tts",
            "transcription",
            "translation",
        ]

    async def inference(self, prompt, tokens: int = 0, images: list = []):
        return await Gpt4freeProvider(
            AI_MODEL=self.AI_MODEL,
            VOICE=self.VOICE,
        ).inference(prompt=prompt, tokens=tokens, images=images)

    async def text_to_speech(self, text: str):
        return await GoogleProvider().text_to_speech(text=text)

    def embeddings(self, input) -> np.ndarray:
        return self.embedder.__call__(input=[input])[0]

    async def transcribe_audio(
        self,
        audio_path,
        translate=False,
    ):
        self.w = WhisperModel(
            self.TRANSCRIPTION_MODEL,
            download_root="models",
            device="cpu",
            compute_type="int8",
        )
        segments, _ = self.w.transcribe(
            audio_path,
            task="transcribe" if not translate else "translate",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        segments = list(segments)
        user_input = ""
        for segment in segments:
            user_input += segment.text
        logging.info(f"[STT] Transcribed User Input: {user_input}")
        return user_input

    async def translate_audio(self, audio_path: str):
        return await self.transcribe_audio(
            audio_path=audio_path,
            translate=True,
        )
