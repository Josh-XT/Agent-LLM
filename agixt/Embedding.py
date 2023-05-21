import requests
import inspect
from chromadb.utils import embedding_functions
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from typing import Optional


class GooglePalmEmbeddingFunction(EmbeddingFunction):
    """To use this EmbeddingFunction, you must have the google.generativeai Python package installed and have a PaLM API key."""

    def __init__(self, api_key: str, model_name: str = "models/embedding-gecko-001"):
        if not api_key:
            raise ValueError("Please provide a PaLM API key.")

        if not model_name:
            raise ValueError("Please provide the model name.")

        try:
            import google.generativeai as palm
        except ImportError:
            raise ValueError(
                "The Google Generative AI python package is not installed. Please install it with `pip install google-generativeai`"
            )

        palm.configure(api_key=api_key)
        self._palm = palm
        self._model_name = model_name

    def __call__(self, texts: Documents) -> Embeddings:
        return [
            self._palm.generate_embeddings(model=self._model_name, text=text)[
                "embedding"
            ]
            for text in texts
        ]


class GoogleVertexEmbeddingFunction(EmbeddingFunction):
    # Follow API Quickstart for Google Vertex AI
    # https://cloud.google.com/vertex-ai/docs/generative-ai/start/quickstarts/api-quickstart
    # Information about the text embedding modules in Google Vertex AI
    # https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings
    def __init__(
        self,
        api_key: str,
        model_name: str = "textembedding-gecko-001",
        project_id: str = "cloud-large-language-models",
        region: str = "us-central1",
    ):
        self._api_url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/endpoints/{model_name}:predict"
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def __call__(self, texts: Documents) -> Embeddings:
        response = self._session.post(
            self._api_url, json={"instances": [{"content": texts}]}
        ).json()

        if "predictions" in response:
            return response["predictions"]
        return {}


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-ada-002",
        organization_id: Optional[str] = None,
        api_base: Optional[str] = None,
        api_type: Optional[str] = None,
    ):
        try:
            import openai
        except ImportError:
            raise ValueError(
                "The openai python package is not installed. Please install it with `pip install openai`"
            )

        if api_key is not None:
            openai.api_key = api_key
        # If the api key is still not set, raise an error
        elif openai.api_key is None:
            raise ValueError(
                "Please provide an OpenAI API key. You can get one at https://platform.openai.com/account/api-keys"
            )

        if api_base is not None:
            openai.api_base = api_base

        if api_type is not None:
            openai.api_type = api_type

        if organization_id is not None:
            openai.organization = organization_id

        self._client = openai.Embedding
        self._model_name = model_name

    def __call__(self, texts: Documents) -> Embeddings:
        # replace newlines, which can negatively affect performance.
        texts = [t.replace("\n", " ") for t in texts]

        # Call the OpenAI Embedding API
        embeddings = self._client.create(input=texts, engine=self._model_name)["data"]

        # Sort resulting embeddings by index
        sorted_embeddings = sorted(embeddings, key=lambda e: e["index"])  # type: ignore

        # Return just the embeddings
        return [result["embedding"] for result in sorted_embeddings]


class Embedding:
    def __init__(self, CFG=None):
        # We need to take the embedder string and then return the correct embedder
        # We also need to return the correct chunk size
        self.CFG = CFG
        try:
            embedder = self.CFG.AGENT_CONFIG["settings"]["embedder"]
            self.embed, self.chunk_size = self.__getattribute__(embedder)()
        except:
            self.embed, self.chunk_size = self.default()
            print("Embedder not found, using default embedder")

    def default(self):
        chunk_size = 128
        embed = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-mpnet-base-v2"
        )
        return embed, chunk_size

    def large_local(self):
        chunk_size = 500
        embed = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="gtr-t5-large"
        )
        return embed, chunk_size

    def azure(self):
        chunk_size = 1000
        embed = OpenAIEmbeddingFunction(
            api_key=self.CFG.AGENT_CONFIG["settings"]["AZURE_API_KEY"],
            organization_id=self.CFG.AGENT_CONFIG["settings"][
                "AZURE_EMBEDDER_DEPLOYMENT_ID"
            ],
            api_type="azure",
            api_base=self.CFG.AGENT_CONFIG["settings"]["AZURE_OPENAI_ENDPOINT"],
        )
        return embed, chunk_size

    def openai(self):
        chunk_size = 1000
        embed = OpenAIEmbeddingFunction(
            api_key=self.CFG.AGENT_CONFIG["settings"]["OPENAI_API_KEY"],
        )
        return embed, chunk_size

    def google_palm(self):
        chunk_size = 1000
        embed = GooglePalmEmbeddingFunction(
            api_key=self.CFG.AGENT_CONFIG["settings"]["GOOGLE_API_KEY"],
        )
        return embed, chunk_size

    def google_vertex(self):
        chunk_size = 1000
        embed = GoogleVertexEmbeddingFunction(
            api_key=self.CFG.AGENT_CONFIG["settings"]["GOOGLE_API_KEY"],
            project_id=self.CFG.AGENT_CONFIG["settings"]["GOOGLE_PROJECT_ID"],
        )
        return embed, chunk_size

    def cohere(self):
        chunk_size = 500
        embed = embedding_functions.CohereEmbeddingFunction(
            api_key=self.CFG.AGENT_CONFIG["settings"]["COHERE_API_KEY"],
        )
        return embed, chunk_size


def get_embedding_providers():
    return [
        func
        for func, _ in inspect.getmembers(Embedding, predicate=inspect.isfunction)
        if not func.startswith("__")
    ]
