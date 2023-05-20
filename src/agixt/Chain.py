import os
import json
from . import AGiXT
import argparse
from . import CustomPrompt
from . import Commands


class Chain:
    def get_chain(self, chain_name):
        with open(os.path.join("chains", f"{chain_name}.json"), "r") as f:
            chain_data = json.load(f)
        return chain_data

    def get_chains(self):
        chains = [
            f.replace(".json", "") for f in os.listdir("chains") if f.endswith(".json")
        ]
        return chains

    def add_chain(self, chain_name):
        chain_data = {"chain_name": chain_name, "steps": []}
        with open(os.path.join("chains", f"{chain_name}.json"), "w") as f:
            json.dump(chain_data, f)

    def rename_chain(self, chain_name, new_name):
        os.rename(
            os.path.join("chains", f"{chain_name}.json"),
            os.path.join("chains", f"{new_name}.json"),
        )

    def add_chain_step(self, chain_name, step_number, agent_name, prompt_type, prompt):
        chain_data = self.get_chain(chain_name)
        chain_data["steps"].append(
            {
                "step": step_number,
                "agent_name": agent_name,
                "prompt_type": prompt_type,
                "prompt": prompt,
            }
        )
        with open(os.path.join("chains", f"{chain_name}.json"), "w") as f:
            json.dump(chain_data, f)

    def update_step(self, chain_name, step_number, agent_name, prompt_type, prompt):
        chain_data = self.get_chain(chain_name)
        for step in chain_data["steps"]:
            if step["step"] == step_number:
                step["agent_name"] = agent_name
                step["prompt_type"] = prompt_type
                step["prompt"] = prompt
                break
        with open(os.path.join("chains", f"{chain_name}.json"), "w") as f:
            json.dump(chain_data, f)

    def delete_step(self, chain_name, step_number):
        chain_data = self.get_chain(chain_name)
        chain_data["steps"] = [
            step for step in chain_data["steps"] if step["step"] != step_number
        ]
        with open(os.path.join("chains", f"{chain_name}.json"), "w") as f:
            json.dump(chain_data, f)

    def delete_chain(self, chain_name):
        os.remove(os.path.join("chains", f"{chain_name}.json"))

    def get_step(self, chain_name, step_number):
        chain_data = self.get_chain(chain_name)
        for step in chain_data["steps"]:
            if step["step"] == step_number:
                return step
        return None

    def get_steps(self, chain_name):
        chain_data = self.get_chain(chain_name)
        return chain_data["steps"]

    def run_chain(self, chain_name):
        chain_data = self.get_chain(chain_name)
        print(f"Running chain '{chain_name}'")
        for step_data in chain_data["steps"]:
            if "prompt" in step_data and "step" in step_data:
                print(f"Running step {step_data['step']}")
                self.run_chain_step(step_data)

    def run_chain_step(self, step):
        if step:
            if "prompt_type" in step:
                prompt_type = step["prompt_type"]
                prompt = step["prompt"]
                agent_name = step["agent_name"]
                try:
                    prompt_name = prompt["prompt_name"]
                    prompt = {k: v for k, v in prompt.items() if k != "prompt_name"}
                    prompt_content = CustomPrompt().get_prompt(prompt_name)
                except:
                    prompt_name = ""
                try:
                    command_name = prompt["command_name"]
                    prompt = {k: v for k, v in prompt.items() if k != "command_name"}
                except:
                    command_name = ""
                if prompt_type == "Prompt":
                    AGiXT(agent_name).run(
                        task=prompt_content, prompt=prompt_name, **prompt
                    )
                elif prompt_type == "Command":
                    Commands(agent_name=agent_name).execute_command(
                        command_name, prompt
                    )
                elif prompt_type == "Chain":
                    self.run_chain(prompt["chain_name"])
                elif prompt_type == "Smart Instruct":
                    AGiXT(agent_name).smart_instruct(task=prompt_content, **prompt)
                elif prompt_type == "Smart Chat":
                    AGiXT(agent_name).smart_chat(task=prompt_content, **prompt)
                elif prompt_type == "Task":
                    AGiXT(agent_name, primary_objective=prompt_content).run_task(
                        objective=prompt_content, **prompt
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", type=str, default="")
    args = parser.parse_args()
    chain_name = args.chain
    Chain().run_chain(chain_name)
