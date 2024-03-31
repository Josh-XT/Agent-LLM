import logging
import asyncio
from g4f.Provider import RetryProvider
from g4f.models import ModelUtils
import random
import base64
import requests


class Gpt4freeProvider:
    def __init__(
        self,
        AI_MODEL: str = "mixtral-8x7b",
        MAX_TOKENS: int = 4096,
        AI_TEMPERATURE: float = 0.7,
        AI_TOP_P: float = 0.7,
        VOICE: str = "Brian",
        **kwargs,
    ):
        self.requirements = ["g4f", "httpx"]
        self.AI_MODEL = AI_MODEL if AI_MODEL else "mixtral-8x7b"
        self.AI_TEMPERATURE = AI_TEMPERATURE if AI_TEMPERATURE else 0.7
        self.MAX_TOKENS = MAX_TOKENS if MAX_TOKENS else 4096
        self.AI_TOP_P = AI_TOP_P if AI_TOP_P else 0.7
        STREAMLABS_VOICES = [
            "Filiz",
            "Astrid",
            "Tatyana",
            "Maxim",
            "Carmen",
            "Ines",
            "Cristiano",
            "Vitoria",
            "Ricardo",
            "Maja",
            "Jan",
            "Jacek",
            "Ewa",
            "Ruben",
            "Lotte",
            "Liv",
            "Seoyeon",
            "Takumi",
            "Mizuki",
            "Giorgio",
            "Carla",
            "Bianca",
            "Karl",
            "Dora",
            "Mathieu",
            "Celine",
            "Chantal",
            "Penelope",
            "Miguel",
            "Mia",
            "Enrique",
            "Conchita",
            "Geraint",
            "Salli",
            "Matthew",
            "Kimberly",
            "Kendra",
            "Justin",
            "Joey",
            "Joanna",
            "Ivy",
            "Raveena",
            "Aditi",
            "Emma",
            "Brian",
            "Amy",
            "Russell",
            "Nicole",
            "Vicki",
            "Marlene",
            "Hans",
            "Naja",
            "Mads",
            "Gwyneth",
            "Zhiyu",
            "es-ES-Standard-A",
            "it-IT-Standard-A",
            "it-IT-Wavenet-A",
            "ja-JP-Standard-A",
            "ja-JP-Wavenet-A",
            "ko-KR-Standard-A",
            "ko-KR-Wavenet-A",
            "pt-BR-Standard-A",
            "tr-TR-Standard-A",
            "sv-SE-Standard-A",
            "nl-NL-Standard-A",
            "nl-NL-Wavenet-A",
            "en-US-Wavenet-A",
            "en-US-Wavenet-B",
            "en-US-Wavenet-C",
            "en-US-Wavenet-D",
            "en-US-Wavenet-E",
            "en-US-Wavenet-F",
            "en-GB-Standard-A",
            "en-GB-Standard-B",
            "en-GB-Standard-C",
            "en-GB-Standard-D",
            "en-GB-Wavenet-A",
            "en-GB-Wavenet-B",
            "en-GB-Wavenet-C",
            "en-GB-Wavenet-D",
            "en-US-Standard-B",
            "en-US-Standard-C",
            "en-US-Standard-D",
            "en-US-Standard-E",
            "de-DE-Standard-A",
            "de-DE-Standard-B",
            "de-DE-Wavenet-A",
            "de-DE-Wavenet-B",
            "de-DE-Wavenet-C",
            "de-DE-Wavenet-D",
            "en-AU-Standard-A",
            "en-AU-Standard-B",
            "en-AU-Wavenet-A",
            "en-AU-Wavenet-B",
            "en-AU-Wavenet-C",
            "en-AU-Wavenet-D",
            "en-AU-Standard-C",
            "en-AU-Standard-D",
            "fr-CA-Standard-A",
            "fr-CA-Standard-B",
            "fr-CA-Standard-C",
            "fr-CA-Standard-D",
            "fr-FR-Standard-C",
            "fr-FR-Standard-D",
            "fr-FR-Wavenet-A",
            "fr-FR-Wavenet-B",
            "fr-FR-Wavenet-C",
            "fr-FR-Wavenet-D",
            "da-DK-Wavenet-A",
            "pl-PL-Wavenet-A",
            "pl-PL-Wavenet-B",
            "pl-PL-Wavenet-C",
            "pl-PL-Wavenet-D",
            "pt-PT-Wavenet-A",
            "pt-PT-Wavenet-B",
            "pt-PT-Wavenet-C",
            "pt-PT-Wavenet-D",
            "ru-RU-Wavenet-A",
            "ru-RU-Wavenet-B",
            "ru-RU-Wavenet-C",
            "ru-RU-Wavenet-D",
            "sk-SK-Wavenet-A",
            "tr-TR-Wavenet-A",
            "tr-TR-Wavenet-B",
            "tr-TR-Wavenet-C",
            "tr-TR-Wavenet-D",
            "tr-TR-Wavenet-E",
            "uk-UA-Wavenet-A",
            "ar-XA-Wavenet-A",
            "ar-XA-Wavenet-B",
            "ar-XA-Wavenet-C",
            "cs-CZ-Wavenet-A",
            "nl-NL-Wavenet-B",
            "nl-NL-Wavenet-C",
            "nl-NL-Wavenet-D",
            "nl-NL-Wavenet-E",
            "en-IN-Wavenet-A",
            "en-IN-Wavenet-B",
            "en-IN-Wavenet-C",
            "fil-PH-Wavenet-A",
            "fi-FI-Wavenet-A",
            "el-GR-Wavenet-A",
            "hi-IN-Wavenet-A",
            "hi-IN-Wavenet-B",
            "hi-IN-Wavenet-C",
            "hu-HU-Wavenet-A",
            "id-ID-Wavenet-A",
            "id-ID-Wavenet-B",
            "id-ID-Wavenet-C",
            "it-IT-Wavenet-B",
            "it-IT-Wavenet-C",
            "it-IT-Wavenet-D",
            "ja-JP-Wavenet-B",
            "ja-JP-Wavenet-C",
            "ja-JP-Wavenet-D",
            "cmn-CN-Wavenet-A",
            "cmn-CN-Wavenet-B",
            "cmn-CN-Wavenet-C",
            "cmn-CN-Wavenet-D",
            "nb-no-Wavenet-E",
            "nb-no-Wavenet-A",
            "nb-no-Wavenet-B",
            "nb-no-Wavenet-C",
            "nb-no-Wavenet-D",
            "vi-VN-Wavenet-A",
            "vi-VN-Wavenet-B",
            "vi-VN-Wavenet-C",
            "vi-VN-Wavenet-D",
            "sr-rs-Standard-A",
            "lv-lv-Standard-A",
            "is-is-Standard-A",
            "bg-bg-Standard-A",
            "af-ZA-Standard-A",
            "Tracy",
            "Danny",
            "Huihui",
            "Yaoyao",
            "Kangkang",
            "HanHan",
            "Zhiwei",
            "Asaf",
            "An",
            "Stefanos",
            "Filip",
            "Ivan",
            "Heidi",
            "Herena",
            "Kalpana",
            "Hemant",
            "Matej",
            "Andika",
            "Rizwan",
            "Lado",
            "Valluvar",
            "Linda",
            "Heather",
            "Sean",
            "Michael",
            "Karsten",
            "Guillaume",
            "Pattara",
            "Jakub",
            "Szabolcs",
            "Hoda",
            "Naayf",
        ]
        if VOICE not in STREAMLABS_VOICES:
            self.STREAMLABS_VOICE = random.choice(STREAMLABS_VOICES)
        else:
            self.STREAMLABS_VOICE = VOICE

    @staticmethod
    def services():
        return ["llm", "tts"]

    async def inference(self, prompt, tokens: int = 0, images: list = []):
        max_new_tokens = (
            int(self.MAX_TOKENS) - int(tokens) if tokens > 0 else self.MAX_TOKENS
        )
        model = ModelUtils.convert["mixtral-8x7b"]
        provider = model.best_provider
        if provider:
            append_model = f" and model: {model.name}" if model.name else ""
            logging.info(f"[Gpt4Free] Use provider: {provider.__name__}{append_model}")
        try:
            return (
                await asyncio.gather(
                    provider.create_async(
                        model=model.name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_new_tokens,
                        temperature=float(self.AI_TEMPERATURE),
                        top_p=float(self.AI_TOP_P),
                    )
                )
            )[0]
        except Exception as e:
            raise e
        finally:
            if provider and isinstance(provider, RetryProvider):
                if hasattr(provider, "exceptions"):
                    for provider_name in provider.exceptions:
                        error = provider.exceptions[provider_name]
                        logging.error(f"[Gpt4Free] {provider_name}: {error}")

    async def text_to_speech(self, text: str):
        response = requests.get(
            f"https://api.streamelements.com/kappa/v2/speech?voice={self.STREAMLABS_VOICE}&text={text}"
        )
        return response.content.decode("utf-8")
