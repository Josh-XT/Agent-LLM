from DBConnection import User
from Interactions import Interactions
from ApiClient import get_api_client, Conversations
from readers.file import FileReader
from Extensions import Extensions
from Chains import Chains
from pydub import AudioSegment
from Defaults import getenv, get_tokens, DEFAULT_SETTINGS
from Models import ChatCompletions
import os
import base64
import uuid
import requests
import json
import time


class AGiXT:
    def __init__(self, user: User, agent_name: str, api_key: str):
        self.user = user
        self.user_email = str(user.email).lower()
        self.api_key = api_key
        self.agent_name = agent_name
        self.uri = getenv("AGIXT_URI")
        self.outputs = f"{self.uri}/outputs/"
        self.ApiClient = get_api_client(api_key)
        self.agent_interactions = Interactions(
            agent_name=self.agent_name, user=self.user.email, ApiClient=self.ApiClient
        )
        self.agent = self.agent_interactions.agent
        self.agent_settings = (
            self.agent.AGENT_CONFIG["settings"]
            if "settings" in self.agent.AGENT_CONFIG
            else DEFAULT_SETTINGS
        )

    async def inference(
        self,
        user_input: str,
        prompt_category: str = "Default",
        prompt_name: str = "Custom Input",
        conversation_name: str = "",
        images: list = [],
        injected_memories: int = 5,
        shots: int = 1,
        browse_links: bool = False,
        voice_response: bool = False,
        **kwargs,
    ):
        """
        Run inference on the AGiXT agent

        Args:
            user_input (str): User input to the agent
            prompt_category (str): Category of the prompt
            prompt_name (str): Name of the prompt to use
            injected_memories (int): Number of memories to inject into the conversation
            conversation_name (str): Name of the conversation
            browse_links (bool): Whether to browse links in the response
            images (list): List of image URLs
            shots (int): Number of responses to generate
            **kwargs: Additional keyword arguments

        Returns:
            str: Response from the agent
        """
        return await self.agent_interactions.run(
            user_input=user_input,
            prompt_category=prompt_category,
            prompt_name=prompt_name,
            context_results=injected_memories,
            shots=shots,
            conversation_name=conversation_name,
            browse_links=browse_links,
            images=images,
            tts=voice_response,
            **kwargs,
        )

    async def text_to_speech(self, text: str):
        """
        Generate Text to Speech audio from text

        Args:
            text (str): Text to convert to speech

        Returns:
            str: URL of the generated audio
        """
        tts_url = await self.agent.text_to_speech(text=text.text)
        if not str(tts_url).startswith("http"):
            file_type = "wav"
            file_name = f"{uuid.uuid4().hex}.{file_type}"
            audio_path = f"./WORKSPACE/{file_name}"
            audio_data = base64.b64decode(tts_url)
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            tts_url = f"{self.outputs}/{file_name}"
        return tts_url

    async def generate_image(self, prompt: str) -> str:
        """
        Generate an image from a prompt

        Args:
            prompt (str): Prompt for the image generation

        Returns:
            str: URL of the generated image
        """
        return await self.agent.generate_image(prompt=prompt)

    async def transcribe_audio(self, audio_path: str):
        """
        Transcribe an audio file

        Args:
            audio_path (str): Path to the audio file

        Returns
            str: Transcription of the audio
        """
        return await self.agent.transcribe_audio(audio_path=audio_path)

    async def translate_audio(self, audio_path: str):
        """
        Translate an audio file

        Args:
            audio_path (str): Path to the audio file

        Returns
            str: Translation of the audio
        """
        return await self.agent.translate_audio(audio_path=audio_path)

    async def execute_command(
        self,
        command_name: str,
        command_args: dict,
        user_input: str = None,
        conversation_name: str = "",
        voice_response: bool = False,
    ):
        """
        Execute a command with arguments

        Args:
            command_name (str): Name of the command to execute
            command_args (dict): Arguments for the command
            user_input (str): Message to add to conversation log pre-execution
            conversation_name (str): Name of the conversation
            voice_response (bool): Whether to generate a voice response

        Returns:
            str: Response from the command
        """
        if not user_input:
            user_input = "Execute command: {command_name} with args: {command_args}"
        c = Conversations(conversation_name=conversation_name, user=self.user_email)
        c.log_interaction(role="USER", message=user_input)
        response = await Extensions(
            agent_name=self.agent_name,
            agent_config=self.agent.AGENT_CONFIG,
            conversation_name=conversation_name,
            ApiClient=self.ApiClient,
            api_key=self.api_key,
            user=self.user_email,
        ).execute_command(
            command_name=command_name,
            command_args=command_args,
        )
        if "tts_provider" in self.agent_settings and voice_response:
            if (
                self.agent_settings["tts_provider"] != "None"
                and self.agent_settings["tts_provider"] != ""
                and self.agent_settings["tts_provider"] != None
            ):
                tts_response = await self.text_to_speech(text=response)
                response = f"{response}\n\n{tts_response}"
        c.log_interaction(role=self.agent_name, message=response)
        return response

    async def execute_chain(
        self,
        chain_name: str,
        user_input: str,
        chain_args: dict = {},
        use_current_agent: bool = True,
        conversation_name: str = "",
        voice_response: bool = False,
    ):
        """
        Execute a chain with arguments

        Args:
            chain_name (str): Name of the chain to execute
            user_input (str): Message to add to conversation log pre-execution
            chain_args (dict): Arguments for the chain
            use_current_agent (bool): Whether to use the current agent
            conversation_name (str): Name of the conversation
            voice_response (bool): Whether to generate a voice response

        Returns:
            str: Response from the chain
        """
        c = Conversations(conversation_name=conversation_name, user=self.user_email)
        c.log_interaction(role="USER", message=user_input)
        response = await Chains(
            user=self.user_email, ApiClient=self.ApiClient
        ).run_chain(
            chain_name=chain_name,
            user_input=user_input,
            agent_override=self.agent_name if use_current_agent else None,
            all_responses=False,
            chain_args=chain_args,
            from_step=1,
        )
        if "tts_provider" in self.agent_settings and voice_response:
            if (
                self.agent_settings["tts_provider"] != "None"
                and self.agent_settings["tts_provider"] != ""
                and self.agent_settings["tts_provider"] != None
            ):
                tts_response = await self.text_to_speech(text=response)
                response = f'{response}\n\n<audio controls><source src="{tts_response}" type="audio/wav"></audio>'
        c.log_interaction(role=self.agent_name, message=response)
        return response

    async def learn_from_websites(
        self,
        urls: list = [],
        scrape_depth: int = 3,
        summarize_content: bool = True,
        conversation_name: str = "",
    ):
        """
        Scrape a website and summarize the content

        Args:
            urls (list): List of URLs to scrape
            scrape_depth (int): Depth to scrape each URL
            summarize_content (bool): Whether to summarize the content
            conversation_name (str): Name of the conversation

        Returns:
            str: Agent response with a list of scraped links
        """
        c = Conversations(conversation_name=conversation_name, user=self.user_email)
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            user_input = f"Learn from the information from {url}"
            c.log_interaction(role="USER", message=user_input)
            if str(url).startswith("https://github.com"):
                res = await self.agent_interactions.github_memories.write_github_repository_to_memory(
                    github_repo=url,
                    github_user=(
                        self.agent_settings["GITHUB_USER"]
                        if "GITHUB_USER" in self.agent_settings
                        else None
                    ),
                    github_token=(
                        self.agent_settings["GITHUB_TOKEN"]
                        if "GITHUB_TOKEN" in self.agent_settings
                        else None
                    ),
                )
                if res == True:
                    response = f"I have read the entire content of the Github repository at {url} into my memory."
                else:
                    response = await self.agent_interactions.websearch.scrape_website(
                        user_input=user_input,
                        search_depth=scrape_depth,
                        summarize_content=summarize_content,
                    )
            else:
                response = await self.agent_interactions.websearch.scrape_website(
                    user_input=user_input,
                    search_depth=scrape_depth,
                    summarize_content=summarize_content,
                )
            c.log_interaction(role=self.agent_name, message=response)
        return response

    async def learn_from_file(
        self,
        file_path: str,
        collection_number: int = 1,
        conversation_name: str = "",
    ):
        """
        Learn from a file

        Args:
            file_path (str): Path to the file
            collection_number (int): Collection number to store the file
            conversation_name (str): Name of the conversation

        Returns:
            str: Response from the agent
        """
        c = Conversations(conversation_name=conversation_name, user=self.user_email)
        file_name = os.path.basename(file_path)
        c.log_interaction(
            role="USER",
            message=f"Learn from the information in the uploaded file called {file_name}",
        )
        file_reader = FileReader(
            agent_name=self.agent_name,
            agent_config=self.agent.AGENT_CONFIG,
            collection_number=collection_number,
            ApiClient=self.ApiClient,
            user=self.user_email,
        )
        res = await file_reader.write_file_to_memory(file_path=file_path)
        if res == True:
            response = f"I have read the entire content of the file called {file_name} into my memory."
        else:
            response = f"I was unable to read the file called {file_name}."
        c.log_interaction(role=self.agent_name, message=response)
        return response

    async def chat_completions(self, prompt: ChatCompletions):
        """
        Generate an OpenAI style chat completion response with a ChatCompletion prompt

        Args:
            prompt (ChatCompletions): Chat completions prompt

        Returns:
            dict: Chat completion response
        """
        agent_name = prompt.model
        conversation_name = prompt.user
        images = []
        new_prompt = ""
        browse_links = True
        tts = False
        if "mode" in self.agent_settings:
            mode = self.agent_settings["mode"]
        else:
            mode = "prompt"
        if "prompt_name" in self.agent_settings:
            prompt_name = self.agent_settings["prompt_name"]
        else:
            prompt_name = "Chat"
        if "prompt_category" in self.agent_settings:
            prompt_category = self.agent_settings["prompt_category"]
        else:
            prompt_category = "Default"
        prompt_args = {}
        if "prompt_args" in self.agent_settings:
            prompt_args = (
                json.loads(self.agent_settings["prompt_args"])
                if isinstance(self.agent_settings["prompt_args"], str)
                else self.agent_settings["prompt_args"]
            )
        if "context_results" in self.agent_settings:
            context_results = int(self.agent_settings["context_results"])
        else:
            context_results = 5
        if "injected_memories" in self.agent_settings:
            context_results = int(self.agent_settings["injected_memories"])
        if "command_name" in self.agent_settings:
            command_name = self.agent_settings["command_name"]
        else:
            command_name = ""
        if "command_args" in self.agent_settings:
            command_args = (
                json.loads(self.agent_settings["command_args"])
                if isinstance(self.agent_settings["command_args"], str)
                else self.agent_settings["command_args"]
            )
        else:
            command_args = {}
        if "command_variable" in self.agent_settings:
            command_variable = self.agent_settings["command_variable"]
        else:
            command_variable = "text"
        if "chain_name" in self.agent_settings:
            chain_name = self.agent_settings["chain_name"]
        else:
            chain_name = ""
        if "chain_args" in self.agent_settings:
            chain_args = (
                json.loads(self.agent_settings["chain_args"])
                if isinstance(self.agent_settings["chain_args"], str)
                else self.agent_settings["chain_args"]
            )
        else:
            chain_args = {}
        if "tts_provider" in self.agent_settings:
            tts_provider = str(self.agent_settings["tts_provider"]).lower()
            if tts_provider != "none" and tts_provider != "":
                tts = True
        for message in prompt.messages:
            if "mode" in message:
                if message["mode"] in ["prompt", "command", "chain"]:
                    mode = message["mode"]
            if "injected_memories" in message:
                context_results = int(message["injected_memories"])
            if "prompt_category" in message:
                prompt_category = message["prompt_category"]
            if "prompt_name" in message:
                prompt_name = message["prompt_name"]
            if "prompt_args" in message:
                prompt_args = (
                    json.loads(message["prompt_args"])
                    if isinstance(message["prompt_args"], str)
                    else message["prompt_args"]
                )
            if "command_name" in message:
                command_name = message["command_name"]
            if "command_args" in message:
                command_args = (
                    json.loads(message["command_args"])
                    if isinstance(message["command_args"], str)
                    else message["command_args"]
                )
            if "command_variable" in message:
                command_variable = message["command_variable"]
            if "chain_name" in message:
                chain_name = message["chain_name"]
            if "chain_args" in message:
                chain_args = (
                    json.loads(message["chain_args"])
                    if isinstance(message["chain_args"], str)
                    else message["chain_args"]
                )
            if "browse_links" in message:
                browse_links = str(message["browse_links"]).lower() == "true"
            if "tts" in message:
                tts = str(message["tts"]).lower() == "true"
            if "content" not in message:
                continue
            if isinstance(message["content"], str):
                role = message["role"] if "role" in message else "User"
                if role.lower() == "system":
                    if "/" in message["content"]:
                        new_prompt += f"{message['content']}\n\n"
                if role.lower() == "user":
                    new_prompt += f"{message['content']}\n\n"
            if isinstance(message["content"], list):
                for msg in message["content"]:
                    if "text" in msg:
                        role = message["role"] if "role" in message else "User"
                        if role.lower() == "user":
                            new_prompt += f"{msg['text']}\n\n"
                    if "image_url" in msg:
                        url = str(
                            msg["image_url"]["url"]
                            if "url" in msg["image_url"]
                            else msg["image_url"]
                        )
                        image_path = f"./WORKSPACE/{uuid.uuid4().hex}.jpg"
                        if url.startswith("http"):
                            image = requests.get(url).content
                        else:
                            file_type = url.split(",")[0].split("/")[1].split(";")[0]
                            if file_type == "jpeg":
                                file_type = "jpg"
                            file_name = f"{uuid.uuid4().hex}.{file_type}"
                            image_path = f"./WORKSPACE/{file_name}"
                            image = base64.b64decode(url.split(",")[1])
                        with open(image_path, "wb") as f:
                            f.write(image)
                        images.append(image_path)
                    if "audio_url" in msg:
                        audio_url = str(
                            msg["audio_url"]["url"]
                            if "url" in msg["audio_url"]
                            else msg["audio_url"]
                        )
                        # If it is not a url, we need to find the file type and convert with pydub
                        if not audio_url.startswith("http"):
                            file_type = (
                                audio_url.split(",")[0].split("/")[1].split(";")[0]
                            )
                            audio_data = base64.b64decode(audio_url.split(",")[1])
                            audio_path = f"./WORKSPACE/{uuid.uuid4().hex}.{file_type}"
                            with open(audio_path, "wb") as f:
                                f.write(audio_data)
                            audio_url = audio_path
                        else:
                            # Download the audio file from the url, get the file type and convert to wav
                            audio_type = audio_url.split(".")[-1]
                            audio_url = f"./WORKSPACE/{uuid.uuid4().hex}.{audio_type}"
                            audio_data = requests.get(audio_url).content
                            with open(audio_url, "wb") as f:
                                f.write(audio_data)
                        wav_file = f"./WORKSPACE/{uuid.uuid4().hex}.wav"
                        AudioSegment.from_file(audio_url).set_frame_rate(16000).export(
                            wav_file, format="wav"
                        )
                        transcribed_audio = await self.transcribe_audio(
                            audio_path=wav_file
                        )
                        new_prompt += transcribed_audio
                    if "video_url" in msg:
                        video_url = str(
                            msg["video_url"]["url"]
                            if "url" in msg["video_url"]
                            else msg["video_url"]
                        )
                        if video_url.startswith("http"):
                            await self.learn_from_websites(
                                url=[video_url],
                                scrape_depth=0,
                                summarize_content=True,
                                conversation_name=conversation_name,
                            )
                    if (
                        "file_url" in msg
                        or "application_url" in msg
                        or "text_url" in msg
                        or "url" in msg
                    ):
                        file_url = str(
                            msg["file_url"]["url"]
                            if "url" in msg["file_url"]
                            else msg["file_url"]
                        )
                        if file_url.startswith("http"):
                            await self.learn_from_websites(
                                urls=[file_url],
                                scrape_depth=3,
                                summarize_content=True,
                                conversation_name=conversation_name,
                            )
                        else:
                            file_type = (
                                file_url.split(",")[0].split("/")[1].split(";")[0]
                            )
                            file_data = base64.b64decode(file_url.split(",")[1])
                            file_path = f"./WORKSPACE/{uuid.uuid4().hex}.{file_type}"
                            with open(file_path, "wb") as f:
                                f.write(file_data)
                            await self.learn_from_file(file_path=file_path)
            if mode == "command" and command_name and command_variable:
                try:
                    command_args = (
                        json.loads(self.agent_settings["command_args"])
                        if isinstance(self.agent_settings["command_args"], str)
                        else self.agent_settings["command_args"]
                    )
                except Exception as e:
                    command_args = {}
                command_args[self.agent_settings["command_variable"]] = new_prompt
                response = await self.execute_command(
                    command_name=self.agent_settings["command_name"],
                    command_args=command_args,
                    user_input=new_prompt,
                    conversation_name=conversation_name,
                    tts=tts,
                )
            elif mode == "chain" and chain_name:
                chain_name = self.agent_settings["chain_name"]
                try:
                    chain_args = (
                        json.loads(self.agent_settings["chain_args"])
                        if isinstance(self.agent_settings["chain_args"], str)
                        else self.agent_settings["chain_args"]
                    )
                except Exception as e:
                    chain_args = {}
                response = await self.execute_chain(
                    chain_name=chain_name,
                    user_input=new_prompt,
                    chain_args=chain_args,
                    use_current_agent=True,
                )
            elif mode == "prompt":
                response = await self.inference(
                    user_input=new_prompt,
                    prompt_name=prompt_name,
                    prompt_category=prompt_category,
                    conversation_name=conversation_name,
                    injected_memories=context_results,
                    shots=prompt.n,
                    browse_links=browse_links,
                    voice_response=tts,
                    images=images,
                    **prompt_args,
                )
        prompt_tokens = get_tokens(new_prompt)
        completion_tokens = get_tokens(response)
        total_tokens = int(prompt_tokens) + int(completion_tokens)
        res_model = {
            "id": conversation_name,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": agent_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(response),
                    },
                    "finish_reason": "stop",
                    "logprobs": None,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
        return res_model
