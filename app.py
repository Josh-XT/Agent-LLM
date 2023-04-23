import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Config import Config
from AgentLLM import AgentLLM
from Commands import Commands
import threading

CFG = Config()
app = FastAPI()
agent_instances = CFG.agent_instances

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentName(BaseModel):
    agent_name: str

class AgentNewName(BaseModel):
    new_name: str

class Objective(BaseModel):
    objective: str

class Prompt(BaseModel):
    prompt: str

class ChainName(BaseModel):
    chain_name: str

class StepInfo(BaseModel):
    step_number: int
    prompt_type: str
    prompt: str

class ChainStep(BaseModel):
    chain_name: str
    step_number: int
    agent_name: str
    prompt_type: str
    prompt: str

class ChainStepNewInfo(BaseModel):
    chain_name: str
    old_step_number: int
    new_step_number: int
    prompt_type: str

@app.get("/api/provider")
async def get_providers():
    providers = CFG.get_providers()
    return {"providers": providers}

@app.post("/api/agent")
async def add_agent(agent_name: AgentName):
    agent_info = CFG.add_agent(agent_name.agent_name)
    return {"message": "Agent added", "agent_file": agent_info['agent_file']}

@app.put("/api/agent/{agent_name}")
async def rename_agent(agent_name: str, new_name: AgentNewName):
    CFG.rename_agent(agent_name, new_name.new_name)
    return {"message": f"Agent {agent_name} renamed to {new_name.new_name}."}

@app.delete("/api/agent/{agent_name}")
async def delete_agent(agent_name: str):
    result = CFG.delete_agent(agent_name)
    return result

@app.get("/api/agent")
async def get_agents():
    agents = CFG.get_agents()
    return {"agents": agents}

@app.get("/api/agent/{agent_name}")
async def get_agent_config(agent_name: str):
    agent_config = CFG.get_agent_config(agent_name)
    return {"agent": agent_config}

@app.get("/api/{agent_name}/chat")
async def get_chat_history(agent_name: str):
    chat_history = CFG.get_chat_history(agent_name)
    return {"chat_history": chat_history}

@app.delete("/api/agent/{agent_name}/memory")
async def wipe_agent_memories(agent_name: str):
    CFG.wipe_agent_memories(agent_name)
    return {"message": f"Memories for agent {agent_name} deleted."}

@app.post("/api/agent/{agent_name}/instruct")
async def instruct(agent_name: str, objective: Objective):
    agent = AgentLLM(agent_name)
    response = agent.run(objective.objective, max_context_tokens=500, long_term_access=False)
    return {"response": str(response)}

@app.post("/api/agent/{agent_name}/chat")
async def chat(agent_name: str, prompt: Prompt):
    # TODO: Change this from using the normal instruct and add a chat method to AgentLLM
    agent = AgentLLM(agent_name)
    response = agent.run(prompt.prompt, max_context_tokens=500, long_term_access=False)
    return {"response": str(response)}

@app.get("/api/agent/{agent_name}/command")
async def get_commands(agent_name: str):
    commands = Commands(agent_name)
    available_commands = commands.get_available_commands()
    return {"commands": available_commands}

@app.patch("/api/agent/{agent_name}/command")
async def toggle_command(agent_name: str, enable: bool, command_name: str):
    try:
        if command_name == "*":
            commands = Commands(agent_name)
            for each_command_name in commands.agent_config["commands"]:
                commands.agent_config["commands"][each_command_name] = enable
            CFG.update_agent_config(agent_name, commands.agent_config)
            return {"message": f"All commands enabled for agent '{agent_name}'."}
        else:
            commands = Commands(agent_name)
            commands.agent_config["commands"][command_name] = enable
            CFG.update_agent_config(agent_name, commands.agent_config)
            return {"message": f"Command '{command_name}' toggled for agent '{agent_name}'."}
    except Exception as e:
        return {"message": f"Error enabled all commands for agent '{agent_name}': {str(e)}"}, 500

@app.post("/api/agent/{agent_name}/task")
async def toggle_task_agent(agent_name: str, objective: Objective):
    if agent_name not in agent_instances:
        if agent_name not in agent_instances:
            agent_instances[agent_name] = AgentLLM(agent_name)
        agent_instance = agent_instances[agent_name]
        agent_instance.set_agent_name(agent_name)
        agent_instance.set_objective(objective.objective)
        agent_thread = threading.Thread(target=agent_instance.run_task)
        agent_thread.start()
        return {"message": "Task agent started"}
    else:
        agent_instance = agent_instances[agent_name]
        agent_instance.stop_running()
        return {"message": "Task agent stopped"}

@app.get("/api/agent/{agent_name}/task")
async def get_task_output(agent_name: str):
    if agent_name not in agent_instances:
        raise HTTPException(status_code=404, detail="Task agent not found")
    agent_instance = agent_instances[agent_name]
    output = CFG.get_task_output(agent_name, agent_instance)
    if agent_instance.get_status():
        return {"output": output, "message": "Task agent is still running"}
    return {"output": output}

@app.get("/api/agent/{agent_name}/task/status")
async def get_task_status(agent_name: str):
    if agent_name not in agent_instances:
        return {"status": False}
    agent_instance = agent_instances[agent_name]
    status = agent_instance.get_status()
    return {"status": status}

@app.get("/api/chain")
async def get_chains():
    chains = CFG.get_chains()
    return chains

@app.get("/api/chain")
async def get_chain(chain_name: ChainName):
    chain_data = CFG.get_chain(chain_name.chain_name)
    return chain_data

@app.post("/api/chain")
async def add_chain(chain_name: ChainName):
    CFG.add_chain(chain_name.chain_name)
    return {"message": f"Chain '{chain_name.chain_name}' created"}

@app.post("/api/chain/step")
async def add_chain_step(chain_step: ChainStep):
    CFG.add_chain_step(chain_step.chain_name, chain_step.step_number, chain_step.agent_name, chain_step.prompt_type, chain_step.prompt)
    return {"message": f"Step '{chain_step.step_number}' created for chain '{chain_step.chain_name}'"}

@app.post("/api/chain/step/update")
async def update_step(chain_step_new_info: ChainStepNewInfo):
    CFG.update_step(chain_step_new_info.chain_name, chain_step_new_info.old_step_number, chain_step_new_info.new_step_number, chain_step_new_info.prompt_type)
    return {"message": f"Step '{chain_step_new_info.old_step_number}' changed to '{chain_step_new_info.new_step_number}' for chain '{chain_step_new_info.chain_name}' with prompt type {chain_step_new_info.prompt_type}."}

@app.delete("/api/chain")
async def delete_chain(chain_name: ChainName):
    CFG.delete_chain(chain_name.chain_name)
    return {"message": f"Chain '{chain_name.chain_name}' deleted"}

@app.delete("/api/chain/step/{step_number}")
async def delete_chain_step(step_number: int, chain_name: ChainName):
    CFG.delete_chain_step(chain_name.chain_name, step_number)
    return {"message": f"Step '{step_number}' deleted for chain '{chain_name.chain_name}'"}

@app.post("/api/chain/run")
async def run_chain(agent_name: str, chain_name: ChainName):
    CFG.run_chain(agent_name, chain_name.chain_name)
    return {"message": "Prompt chain started"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=False)