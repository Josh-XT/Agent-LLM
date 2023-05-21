from AGiXT import AGiXT
import re
import json
from pathlib import Path
from Agent import Agent
from collections import deque


class Tasks:
    def __init__(self, agent_name: str = "AGiXT"):
        self.agent_name = agent_name
        self.agent = Agent(self.agent_name)
        self.primary_objective = None
        self.task_list = deque([])
        self.output_list = []
        self.stop_running_event = None

    def save_task(self, task_name):
        task_name = re.sub(
            r"[^\w\s]", "", task_name
        )  # remove non-alphanumeric & non-space characters
        task_name = task_name[:15]  # truncate to 15 characters

        # ensure the directories exist
        directory = Path(f"agents/{self.agent_name}")
        directory.mkdir(parents=True, exist_ok=True)

        # serialize the task state and save to a file
        task_state = {
            "task_name": task_name,
            "task_list": list(self.task_list),
            "output_list": self.output_list,
            "primary_objective": self.primary_objective,
        }
        with open(f"agents/{self.agent_name}/{task_name}.json", "w") as f:
            json.dump(task_state, f)

    def get_status(self):
        try:
            return not self.stop_running_event.is_set()
        except:
            return False

    def get_output_list(self):
        return self.output_list

    def update_output_list(self, output):
        print(
            self.agent.save_task_output(self.agent_name, output, self.primary_objective)
        )

    def stop_tasks(self):
        if self.stop_running_event is not None:
            self.stop_running_event.set()
        self.task_list.clear()

    def run_task(
        self,
        stop_event,
        objective,
        async_exec: bool = False,
        learn_file: str = "",
        smart: bool = False,
        **kwargs,
    ):
        self.primary_objective = objective
        if learn_file != "":
            learned_file = self.agent.memories.read_file(
                task=objective, file_path=learn_file
            )
            if learned_file:
                self.update_output_list(
                    f"Read file {learn_file} into memory for task {objective}.\n\n"
                )
            else:
                self.update_output_list(
                    f"Failed to read file {learn_file} into memory.\n\n"
                )

        self.update_output_list(
            f"Starting task with objective: {self.primary_objective}.\n\n"
        )

        if not self.task_list:
            self.task_list.append(
                {
                    "task_id": 1,
                    "task_name": "Develop a task list to complete the objective if necessary.  The plan is 'None' if not necessary.",
                }
            )

        self.stop_running_event = stop_event
        while not self.stop_running_event.is_set() and self.task_list:
            task = self.task_list.popleft()

            if task["task_name"] in ["None", "None.", ""]:
                self.stop_tasks()
                continue

            self.update_output_list(
                f"\nExecuting task {task['task_id']}: {task['task_name']}\n"
            )

            if smart:
                result = AGiXT(self.agent_name).smart_instruct(
                    task=task["task_name"],
                    shots=3,
                    async_exec=async_exec,
                    **kwargs,
                )
            else:
                result = AGiXT(self.agent_name).instruction_agent(
                    task=task["task_name"], **kwargs
                )

            self.update_output_list(f"\nTask Result:\n\n{result}\n")

            new_tasks = AGiXT(self.agent_name).task_agent(
                result=result,
                task_description=task["task_name"],
                task_list=list(self.task_list),
            )
            self.update_output_list(f"\nNew Tasks:\n\n{new_tasks}\n")

            for new_task in new_tasks:
                new_task_id = len(self.task_list) + 1
                new_task.update({"task_id": new_task_id})
                self.task_list.append(new_task)

        if not self.task_list:
            self.stop_tasks()

        self.update_output_list("All tasks completed or stopped.")
