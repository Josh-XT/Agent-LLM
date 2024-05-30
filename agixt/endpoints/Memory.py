import os
import base64
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Header
from ApiClient import Agent, verify_api_key, get_api_client, WORKERS, is_admin
from typing import Dict, Any, List
from Websearch import Websearch
from XT import AGiXT
from Memories import Memories
from readers.github import GithubReader
from readers.file import FileReader
from readers.arxiv import ArxivReader
from readers.youtube import YoutubeReader
from Models import (
    AgentMemoryQuery,
    TextMemoryInput,
    FileInput,
    UrlInput,
    GitHubInput,
    ArxivInput,
    YoutubeInput,
    ResponseMessage,
    Dataset,
    FinetuneAgentModel,
    ExternalSource,
)

app = APIRouter()


@app.post(
    "/api/agent/{agent_name}/memory/{collection_number}/query",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def query_memories(
    agent_name: str,
    memory: AgentMemoryQuery,
    collection_number=0,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> Dict[str, Any]:
    ApiClient = get_api_client(authorization=authorization)
    try:
        collection_number = int(collection_number)
    except:
        collection_number = 0
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    memories = await Memories(
        agent_name=agent_name,
        agent_config=agent_config,
        collection_number=collection_number,
        ApiClient=ApiClient,
        user=user,
    ).get_memories_data(
        user_input=memory.user_input,
        limit=memory.limit,
        min_relevance_score=memory.min_relevance_score,
    )
    return {"memories": memories}


# Export all agent memories
@app.get(
    "/api/agent/{agent_name}/memory/export",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def export_agent_memories(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
) -> Dict[str, Any]:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    memories = await Memories(
        agent_name=agent_name, agent_config=agent_config, ApiClient=ApiClient, user=user
    ).export_collections_to_json()
    return {"memories": memories}


@app.post(
    "/api/agent/{agent_name}/memory/import",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def import_agent_memories(
    agent_name: str,
    memories: List[dict],
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    await Memories(
        agent_name=agent_name, agent_config=agent_config, ApiClient=ApiClient, user=user
    ).import_collections_from_json(memories)
    return ResponseMessage(message="Memories imported.")


@app.post(
    "/api/agent/{agent_name}/learn/text",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_text(
    agent_name: str,
    data: TextMemoryInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    await Memories(
        agent_name=agent_name,
        agent_config=agent_config,
        collection_number=data.collection_number,
        ApiClient=ApiClient,
        user=user,
    ).write_text_to_memory(
        user_input=data.user_input, text=data.text, external_source="user input"
    )
    return ResponseMessage(
        message="Agent learned the content from the text assocated with the user input."
    )


@app.post(
    "/api/agent/{agent_name}/learn/file",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_file(
    agent_name: str,
    file: FileInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    # Strip any path information from the file name
    file.file_name = os.path.basename(file.file_name)
    base_path = os.path.join(os.getcwd(), "WORKSPACE")
    file_path = os.path.normpath(os.path.join(base_path, file.file_name))
    if not file_path.startswith(base_path):
        raise Exception("Path given not allowed")
    try:
        file_content = base64.b64decode(file.file_content)
    except:
        file_content = file.file_content.encode("utf-8")
    with open(file_path, "wb") as f:
        f.write(file_content)
    try:
        agent_config = Agent(
            agent_name=agent_name, user=user, ApiClient=ApiClient
        ).get_agent_config()
        await FileReader(
            agent_name=agent_name,
            agent_config=agent_config,
            collection_number=file.collection_number,
            ApiClient=ApiClient,
            user=user,
        ).write_file_to_memory(file_path=file_path)
        try:
            os.remove(file_path)
        except Exception:
            pass
        return ResponseMessage(message="Agent learned the content from the file.")
    except Exception as e:
        try:
            os.remove(file_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/agent/{agent_name}/learn/url",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_url(
    agent_name: str,
    url: UrlInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    url.url = url.url.replace(" ", "%20")
    response = await Websearch(
        collection_number=url.collection_number,
        agent=agent,
        user=user,
        ApiClient=ApiClient,
    ).scrape_websites(
        user_input=f"I am browsing {url.url} and collecting data from it to learn more.",
        search_depth=3,
    )
    return ResponseMessage(message=response)


@app.post(
    "/api/agent/{agent_name}/learn/github",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_github_repo(
    agent_name: str,
    git: GitHubInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    await GithubReader(
        agent_name=agent_name,
        agent_config=agent_config,
        collection_number=git.collection_number,
        use_agent_settings=git.use_agent_settings,
        ApiClient=ApiClient,
        user=user,
    ).write_github_repository_to_memory(
        github_repo=git.github_repo,
        github_user=git.github_user,
        github_token=git.github_token,
        github_branch=git.github_branch,
    )
    return ResponseMessage(
        message="Agent learned the content from the GitHub Repository."
    )


@app.post(
    "/api/agent/{agent_name}/learn/arxiv",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_arxiv(
    agent_name: str,
    arxiv_input: ArxivInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    await ArxivReader(
        agent_name=agent_name,
        agent_config=agent_config,
        collection_number=arxiv_input.collection_number,
        ApiClient=ApiClient,
    ).write_arxiv_articles_to_memory(
        query=arxiv_input.query,
        article_ids=arxiv_input.article_ids,
        max_articles=arxiv_input.max_results,
    )
    return ResponseMessage(message="Agent learned the content from the arXiv articles.")


@app.post(
    "/api/agent/{agent_name}/learn/youtube",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def learn_youtube(
    agent_name: str,
    youtube_input: YoutubeInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    await YoutubeReader(
        agent_name=agent_name,
        agent_config=agent_config,
        collection_number=youtube_input.collection_number,
        ApiClient=ApiClient,
    ).write_youtube_captions_to_memory(video_id=youtube_input.video_id)
    return ResponseMessage(message="Agent learned the content from the YouTube video.")


@app.post(
    "/api/agent/{agent_name}/reader/{reader_name}",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def agent_reader(
    agent_name: str,
    reader_name: str,
    data: dict,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    agent_config = agent.AGENT_CONFIG
    collection_number = data["collection_number"] if "collection_number" in data else 0
    if reader_name == "file":
        response = await FileReader(
            agent_name=agent_name,
            agent_config=agent_config,
            collection_number=collection_number,
            ApiClient=ApiClient,
            user=user,
        ).write_file_to_memory(file_path=data["file_path"])
    elif reader_name == "website":
        response = await Websearch(
            collection_number=collection_number,
            agent=agent,
            user=user,
            ApiClient=ApiClient,
        ).get_web_content(url=data["url"])
    elif reader_name == "github":
        response = await GithubReader(
            agent_name=agent_name,
            agent_config=agent_config,
            collection_number=collection_number,
            use_agent_settings=(
                data["use_agent_settings"] if "use_agent_settings" in data else False
            ),
            ApiClient=ApiClient,
            user=user,
        ).write_github_repository_to_memory(
            github_repo=data["github_repo"],
            github_user=data["github_user"] if "github_user" in data else None,
            github_token=data["github_token"] if "github_token" in data else None,
            github_branch=data["github_branch"] if "github_branch" in data else "main",
        )
    elif reader_name == "arxiv":
        response = await ArxivReader(
            agent_name=agent_name,
            agent_config=agent_config,
            collection_number=collection_number,
            ApiClient=ApiClient,
            user=user,
        ).write_arxiv_articles_to_memory(
            query=data["query"],
            article_ids=data["article_ids"],
            max_articles=data["max_articles"],
        )
    elif reader_name == "youtube":
        response = await YoutubeReader(
            agent_name=agent_name,
            agent_config=agent_config,
            collection_number=collection_number,
            ApiClient=ApiClient,
            user=user,
        ).write_youtube_captions_to_memory(video_id=data["video_id"])
    else:
        raise HTTPException(status_code=400, detail="Invalid reader name.")
    if response == True:
        return ResponseMessage(
            message=f"Agent learned the content from the {reader_name}."
        )
    else:
        return ResponseMessage(message=f"Agent failed to learn the content.")


@app.delete(
    "/api/agent/{agent_name}/memory",
    tags=["Memory", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def wipe_agent_memories(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    await Memories(
        agent_name=agent_name,
        agent_config=agent.AGENT_CONFIG,
        collection_number=0,
        ApiClient=ApiClient,
        user=user,
    ).wipe_memory()
    return ResponseMessage(message=f"Memories for agent {agent_name} deleted.")


@app.delete(
    "/api/agent/{agent_name}/memory/{collection_number}",
    tags=["Memory", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def wipe_agent_memories(
    agent_name: str,
    collection_number=0,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    try:
        collection_number = int(collection_number)
    except:
        collection_number = 0
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    await Memories(
        agent_name=agent_name,
        agent_config=agent.AGENT_CONFIG,
        collection_number=collection_number,
        ApiClient=ApiClient,
        user=user,
    ).wipe_memory()
    return ResponseMessage(message=f"Memories for agent {agent_name} deleted.")


@app.delete(
    "/api/agent/{agent_name}/memory/{collection_number}/{memory_id}",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def delete_agent_memory(
    agent_name: str,
    collection_number=0,
    memory_id="",
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    ApiClient = get_api_client(authorization=authorization)
    try:
        collection_number = int(collection_number)
    except:
        collection_number = 0
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    await Memories(
        agent_name=agent_name,
        agent_config=agent.AGENT_CONFIG,
        collection_number=collection_number,
        ApiClient=ApiClient,
        user=user,
    ).delete_memory(key=memory_id)
    return ResponseMessage(
        message=f"Memory {memory_id} for agent {agent_name} deleted."
    )


# Create dataset
@app.post(
    "/api/agent/{agent_name}/memory/dataset",
    tags=["Memory", "Admin"],
    dependencies=[Depends(verify_api_key)],
    summary="Create a dataset from the agent's memories",
)
async def create_dataset(
    agent_name: str,
    dataset: Dataset,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    batch_size = dataset.batch_size if dataset.batch_size < (int(WORKERS) - 2) else 4
    asyncio.create_task(
        await AGiXT(
            agent_name=agent_name,
            user=user,
            api_key=authorization,
        ).create_dataset_from_memories(
            dataset_name=dataset.dataset_name,
            batch_size=batch_size,
        )
    )
    return ResponseMessage(
        message=f"Creation of dataset {dataset.dataset_name} for agent {agent_name} started."
    )


# Train model
@app.post(
    "/api/agent/{agent_name}/memory/dataset/{dataset_name}/finetune",
    tags=["Memory", "Admin"],
    dependencies=[Depends(verify_api_key)],
    summary="Fine tune a language model with the agent's memories as a synthetic dataset",
)
async def fine_tune_model(
    agent_name: str,
    finetune: FinetuneAgentModel,
    dataset_name: str,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    from Tuning import fine_tune_llm

    ApiClient = get_api_client(authorization=authorization)
    asyncio.create_task(
        fine_tune_llm(
            agent_name=agent_name,
            dataset_name=dataset_name,
            model_name=finetune.model,
            max_seq_length=finetune.max_seq_length,
            huggingface_output_path=finetune.huggingface_output_path,
            private_repo=finetune.private_repo,
            ApiClient=ApiClient,
        )
    )
    return ResponseMessage(
        message=f"Fine-tuning of model {finetune.model_name} started. The agent's status has is now set to True, it will be set to False once the training is complete."
    )


# Delete memories from external source
@app.delete(
    "/api/agent/{agent_name}/memory/external_source",
    tags=["Memory", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def delete_memories_from_external_source(
    agent_name: str,
    external_source: ExternalSource,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    await Memories(
        agent_name=agent_name,
        agent_config=agent.AGENT_CONFIG,
        collection_number=external_source.collection_number,
        ApiClient=ApiClient,
        user=user,
    ).delete_memories_from_external_source(
        external_source=external_source.external_source
    )
    return ResponseMessage(
        message=f"Memories from external source {external_source.external_source} for agent {agent_name} deleted."
    )


# Get unique external sources
@app.get(
    "/api/agent/{agent_name}/memory/external_sources",
    tags=["Memory"],
    dependencies=[Depends(verify_api_key)],
)
async def get_unique_external_sources(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
) -> Dict[str, Any]:
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    external_sources = await Memories(
        agent_name=agent_name,
        agent_config=agent.AGENT_CONFIG,
        collection_number=0,
        ApiClient=ApiClient,
        user=user,
    ).get_external_data_sources()
    return {"external_sources": external_sources}
