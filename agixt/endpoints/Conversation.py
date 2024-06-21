from fastapi import APIRouter, Depends, Header
from ApiClient import verify_api_key, Conversations
from XT import AGiXT
from Models import (
    HistoryModel,
    ConversationHistoryModel,
    ConversationHistoryMessageModel,
    UpdateConversationHistoryMessageModel,
    ResponseMessage,
    LogInteraction,
    RenameConversationModel,
)
import json
from datetime import datetime

app = APIRouter()


@app.get(
    "/api/conversations",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def get_conversations_list(user=Depends(verify_api_key)):
    c = Conversations(user=user)
    conversations = c.get_conversations()
    if conversations is None:
        conversations = []
    conversations_with_ids = c.get_conversations_with_ids()
    return {
        "conversations": conversations,
        "conversations_with_ids": conversations_with_ids,
    }


@app.get(
    "/api/conversation",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def get_conversation_history(history: HistoryModel, user=Depends(verify_api_key)):
    conversation_history = Conversations(
        conversation_name=history.conversation_name, user=user
    ).get_conversation(
        limit=history.limit,
        page=history.page,
    )
    if conversation_history is None:
        conversation_history = []
    if "interactions" in conversation_history:
        conversation_history = conversation_history["interactions"]
    return {"conversation_history": conversation_history}


@app.get(
    "/api/conversation/{conversation_name}",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def get_conversation_data(
    conversation_name: str,
    limit: int = 100,
    page: int = 1,
    user=Depends(verify_api_key),
):
    conversation_history = Conversations(
        conversation_name=conversation_name, user=user
    ).get_conversation(limit=limit, page=page)
    if conversation_history is None:
        conversation_history = []
    if "interactions" in conversation_history:
        conversation_history = conversation_history["interactions"]
    return {"conversation_history": conversation_history}


@app.post(
    "/api/conversation",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def new_conversation_history(
    history: ConversationHistoryModel,
    user=Depends(verify_api_key),
):
    Conversations(
        conversation_name=history.conversation_name, user=user
    ).new_conversation(conversation_content=history.conversation_content)
    return {"conversation_history": history.conversation_content}


@app.delete(
    "/api/conversation",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def delete_conversation_history(
    history: ConversationHistoryModel, user=Depends(verify_api_key)
) -> ResponseMessage:
    Conversations(
        conversation_name=history.conversation_name, user=user
    ).delete_conversation()
    return ResponseMessage(
        message=f"Conversation `{history.conversation_name}` for agent {history.agent_name} deleted."
    )


@app.delete(
    "/api/conversation/message",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def delete_history_message(
    history: ConversationHistoryMessageModel, user=Depends(verify_api_key)
) -> ResponseMessage:
    Conversations(
        conversation_name=history.conversation_name, user=user
    ).delete_message(message=history.message)
    return ResponseMessage(message=f"Message deleted.")


@app.put(
    "/api/conversation/message",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def update_history_message(
    history: UpdateConversationHistoryMessageModel, user=Depends(verify_api_key)
) -> ResponseMessage:
    Conversations(
        conversation_name=history.conversation_name, user=user
    ).update_message(
        message=history.message,
        new_message=history.new_message,
    )
    return ResponseMessage(message=f"Message updated.")


@app.post(
    "/api/conversation/message",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def log_interaction(
    log_interaction: LogInteraction, user=Depends(verify_api_key)
) -> ResponseMessage:
    Conversations(
        conversation_name=log_interaction.conversation_name, user=user
    ).log_interaction(
        message=log_interaction.message,
        role=log_interaction.role,
    )
    return ResponseMessage(message=f"Interaction logged.")


# Ask AI to rename the conversation
@app.put(
    "/api/conversation",
    tags=["Conversation"],
    dependencies=[Depends(verify_api_key)],
)
async def rename_conversation(
    rename: RenameConversationModel,
    user=Depends(verify_api_key),
    authorization: str = Header(None),
):
    c = Conversations(conversation_name=rename.conversation_name, user=user)
    if rename.new_conversation_name == "-":
        agixt = AGiXT(user=user, agent_name=rename.agent_name, api_key=authorization)
        conversation_list = c.get_conversations()
        response = await agixt.inference(
            user_input=f"Rename conversation",
            prompt_name="Name Conversation",
            conversation_name=rename.conversation_name,
            conversation_list="\n".join(conversation_list),
            websearch=False,
            browse_links=False,
            voice_response=False,
            log_user_input=False,
            log_output=False,
        )
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].strip()
        try:
            response = json.loads(response)
            new_name = response["suggested_conversation_name"]
            if new_name in conversation_list:
                # Do not use {new_name}!
                response = await agixt.inference(
                    user_input=f"**Do not use {new_name}!**",
                    prompt_name="Name Conversation",
                    conversation_name=rename.conversation_name,
                    conversation_list="\n".join(conversation_list),
                    websearch=False,
                    browse_links=False,
                    voice_response=False,
                    log_user_input=False,
                    log_output=False,
                )
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].strip()
                response = json.loads(response)
                new_name = response["suggested_conversation_name"]
                if new_name in conversation_list:
                    new_name = datetime.now().strftime(
                        "Conversation Created %Y-%m-%d %I:%M %p"
                    )
        except:
            new_name = datetime.now().strftime("Conversation Created %Y-%m-%d %I:%M %p")
        rename.new_conversation_name = new_name.replace("_", " ")
    c.rename_conversation(new_name=rename.new_conversation_name)
    c = Conversations(conversation_name=rename.new_conversation_name, user=user)
    c.log_interaction(
        message=f"[ACTIVITY][INFO] Conversation renamed to `{rename.new_conversation_name}`.",
        role=rename.agent_name,
    )
    return {"conversation_name": rename.new_conversation_name}
