import asyncio
import os

try:
    import google.generativeai as genai  # Primary import attempt
except ImportError:
    import sys
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "google-generativeai"]
    )
    import google.generativeai as genai  # Import again after installation

try:
    import gtts as ts
except ImportError:
    import sys
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "gTTS"])
    import gtts as ts

from pydub import AudioSegment


class GoogleProvider:
    def __init__(
        self,
        GOOGLE_API_KEY: str,
        AI_MODEL: str = "gemini-pro",
        MAX_TOKENS: int = 4000,
        AI_TEMPERATURE: float = 0.7,
        **kwargs,
    ):
        """
        Initialize the GeminiProvider with required parameters.

        Parameters:
        - GOOGLE_API_KEY: str, API key for Google API.
        - AI_MODEL: str, AI model to use (default is 'gemini-pro').
        - MAX_TOKENS: int, maximum tokens to generate (default is 4000).
        - AI_TEMPERATURE: float, temperature for AI model (default is 0.7).
        """
        self.requirements = ["google-generativeai"]
        self.GOOGLE_API_KEY = GOOGLE_API_KEY
        self.AI_MODEL = AI_MODEL
        self.MAX_TOKENS = MAX_TOKENS
        self.AI_TEMPERATURE = AI_TEMPERATURE

        # Configure and setup Gemini model
        try:
            genai.configure(api_key=self.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(self.AI_MODEL)
        except Exception as e:
            print(f"Error setting up Gemini model: {e}")

        # Set default generation config
        self.generation_config = genai.types.GenerationConfig(
            max_output_tokens=self.MAX_TOKENS, temperature=self.AI_TEMPERATURE
        )

    @staticmethod
    def services():
        return ["llm", "tts"]

    async def inference(self, prompt, tokens: int = 0, images: list = []):
        """
        Perform inference using the Gemini model asynchronously.

        Parameters:
        - prompt: str, input prompt for generating text.
        - tokens: int, additional tokens to generate (default is 0).

        Returns:
        - str, generated text.
        """
        try:
            # Adjust based on Gemini API
            new_max_tokens = int(self.MAX_TOKENS) - tokens
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=new_max_tokens, temperature=float(self.AI_TEMPERATURE)
            )

            response = await asyncio.to_thread(
                self.model.generate_content,
                contents=prompt,
                generation_config=generation_config,
            )

            # Extract the generated text from the response
            if response.parts:
                generated_text = "".join(part.text for part in response.parts)
            else:
                generated_text = "".join(
                    part.text for part in response.candidates[0].content.parts
                )

            return generated_text
        except Exception as e:
            return f"Gemini Error: {e}"

    async def text_to_speech(self, text: str):
        tts = ts.gTTS(text)
        mp3_path = "speech.mp3"
        tts.save(mp3_path)
        wav_path = "output_speech.wav"
        AudioSegment.from_mp3(mp3_path).set_frame_rate(16000).export(
            wav_path, format="wav"
        )
        os.remove(mp3_path)
        with open(wav_path, "rb") as f:
            audio_content = f.read()
        os.remove(wav_path)
        return audio_content
