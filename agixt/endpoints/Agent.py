from typing import Dict
from fastapi import APIRouter, HTTPException, Depends, Header
from Interactions import Interactions
from Websearch import Websearch
from Globals import getenv
from ApiClient import (
    Agent,
    add_agent,
    delete_agent,
    rename_agent,
    get_agents,
    verify_api_key,
    get_api_client,
    is_admin,
)
from Models import (
    AgentNewName,
    AgentPrompt,
    ToggleCommandPayload,
    AgentCommands,
    AgentSettings,
    AgentConfig,
    ResponseMessage,
    UrlInput,
    TTSInput,
)
import base64
import uuid

app = APIRouter()


@app.post("/api/agent", tags=["Agent", "Admin"], dependencies=[Depends(verify_api_key)])
async def addagent(
    agent: AgentSettings,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> Dict[str, str]:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    add_agent(
        agent_name=agent.agent_name,
        provider_settings=agent.settings,
        commands=agent.commands,
        user=user,
    )
    if agent.training_urls != [] and agent.training_urls != None:
        if len(agent.training_urls) < 1:
            return {"message": "Agent added."}
        ApiClient = get_api_client(authorization=authorization)
        _agent = Agent(agent_name=agent.agent_name, user=user, ApiClient=ApiClient)
        reader = Websearch(
            collection_number=0,
            agent=_agent,
            user=user,
            ApiClient=ApiClient,
        )
        for url in agent.training_urls:
            await reader.get_web_content(url=url)
        return {"message": "Agent added and trained."}
    return {"message": "Agent added."}


@app.post(
    "/api/agent/import", tags=["Agent", "Admin"], dependencies=[Depends(verify_api_key)]
)
async def import_agent(
    agent: AgentConfig, user=Depends(verify_api_key), authorization: str = Header(None)
) -> Dict[str, str]:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    return add_agent(
        agent_name=agent.agent_name,
        provider_settings=agent.settings,
        commands=agent.commands,
        user=user,
    )


@app.patch(
    "/api/agent/{agent_name}",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def renameagent(
    agent_name: str,
    new_name: AgentNewName,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    rename_agent(agent_name=agent_name, new_name=new_name.new_name, user=user)
    return ResponseMessage(message="Agent renamed.")


@app.put(
    "/api/agent/{agent_name}",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def update_agent_settings(
    agent_name: str,
    settings: AgentSettings,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    update_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).update_agent_config(new_config=settings.settings, config_key="settings")
    return ResponseMessage(message=update_config)


@app.put(
    "/api/agent/{agent_name}/commands",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def update_agent_commands(
    agent_name: str,
    commands: AgentCommands,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    update_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).update_agent_config(new_config=commands.commands, config_key="commands")
    return ResponseMessage(message=update_config)


@app.delete(
    "/api/agent/{agent_name}",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def deleteagent(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    await Websearch(
        collection_number=0,
        agent=agent,
        user=user,
        ApiClient=ApiClient,
    ).agent_memory.wipe_memory()
    delete_agent(agent_name=agent_name, user=user)
    return ResponseMessage(message=f"Agent {agent_name} deleted.")


@app.get("/api/agent", tags=["Agent"], dependencies=[Depends(verify_api_key)])
async def getagents(user=Depends(verify_api_key)):
    agents = get_agents(user=user)
    return {"agents": agents}


@app.get(
    "/api/agent/{agent_name}",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def get_agentconfig(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
):
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent_config = Agent(
        agent_name=agent_name, user=user, ApiClient=ApiClient
    ).get_agent_config()
    return {"agent": agent_config}


@app.post(
    "/api/agent/{agent_name}/prompt",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def prompt_agent(
    agent_name: str,
    agent_prompt: AgentPrompt,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
):
    ApiClient = get_api_client(authorization=authorization)
    agent = Interactions(agent_name=agent_name, user=user, ApiClient=ApiClient)
    if (
        "prompt" in agent_prompt.prompt_args
        and "prompt_name" not in agent_prompt.prompt_args
    ):
        agent_prompt.prompt_args["prompt_name"] = agent_prompt.prompt_args["prompt"]
    if "prompt_name" not in agent_prompt.prompt_args:
        agent_prompt.prompt_args["prompt_name"] = "Chat"
    if "prompt_category" not in agent_prompt.prompt_args:
        agent_prompt.prompt_args["prompt_category"] = "Default"
    agent_prompt.prompt_args = {k: v for k, v in agent_prompt.prompt_args.items()}
    response = await agent.run(
        log_user_input=True,
        **agent_prompt.prompt_args,
    )
    return {"response": str(response)}


@app.get(
    "/api/agent/{agent_name}/command",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def get_commands(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
):
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    return {"commands": agent.AGENT_CONFIG["commands"]}


@app.patch(
    "/api/agent/{agent_name}/command",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def toggle_command(
    agent_name: str,
    payload: ToggleCommandPayload,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
) -> ResponseMessage:
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    try:
        if payload.command_name == "*":
            for each_command_name in agent.AGENT_CONFIG["commands"]:
                agent.AGENT_CONFIG["commands"][each_command_name] = payload.enable

            agent.update_agent_config(
                new_config=agent.AGENT_CONFIG["commands"], config_key="commands"
            )
            return ResponseMessage(
                message=f"All commands enabled for agent '{agent_name}'."
            )
        else:
            agent.AGENT_CONFIG["commands"][payload.command_name] = payload.enable
            agent.update_agent_config(
                new_config=agent.AGENT_CONFIG["commands"], config_key="commands"
            )
            return ResponseMessage(
                message=f"Command '{payload.command_name}' toggled for agent '{agent_name}'."
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error enabling all commands for agent '{agent_name}': {str(e)}",
        )


# Get agent browsed links
@app.get(
    "/api/agent/{agent_name}/browsed_links",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def get_agent_browsed_links(
    agent_name: str, user=Depends(verify_api_key), authorization: str = Header(None)
):
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    return {"links": agent.get_browsed_links()}


# Delete browsed link from memory
@app.delete(
    "/api/agent/{agent_name}/browsed_links",
    tags=["Agent", "Admin"],
    dependencies=[Depends(verify_api_key)],
)
async def delete_browsed_link(
    agent_name: str,
    url: UrlInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
):
    if is_admin(email=user, api_key=authorization) != True:
        raise HTTPException(status_code=403, detail="Access Denied")
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    websearch = Websearch(
        collection_number=url.collection_number,
        agent=agent,
        user=user,
        ApiClient=ApiClient,
    )
    websearch.agent_memory.delete_memories_from_external_source(url=url.url)
    agent.delete_browsed_link(url=url.url)
    return {"message": "Browsed links deleted."}


@app.post(
    "/api/agent/{agent_name}/text_to_speech",
    tags=["Agent"],
    dependencies=[Depends(verify_api_key)],
)
async def text_to_speech(
    agent_name: str,
    text: TTSInput,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
):
    ApiClient = get_api_client(authorization=authorization)
    agent = Agent(agent_name=agent_name, user=user, ApiClient=ApiClient)
    AGIXT_URI = getenv("AGIXT_URI")
    tts_response = await agent.text_to_speech(text=text.text)
    if not str(tts_response).startswith("http"):
        file_type = "wav"
        file_name = f"{uuid.uuid4().hex}.{file_type}"
        audio_path = f"./WORKSPACE/{file_name}"
        audio_data = base64.b64decode(tts_response)
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        tts_response = f"{AGIXT_URI}/outputs/{file_name}"
    return {"url": tts_response}
