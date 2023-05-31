from threading import Thread
from concurrent.futures import Future
import logging
import time


def call_with_future(fn, future, args, kwargs):
    try:
        result = fn(*args, **kwargs)
        future.set_result(result)
    except Exception as exc:
        future.set_exception(exc)


def threaded(fn):
    def wrapper(*args, **kwargs):
        future = Future()
        Thread(target=call_with_future, args=(fn, future, args, kwargs)).start()
        return future

    return wrapper


import requests


class RunpodProvider:
    def __init__(
        self,
        AI_PROVIDER_URI: str = "",
        API_KEY: str = "",
        MAX_TOKENS: int = 2000,
        AI_TEMPERATURE: float = 0.7,
        AI_MODEL: str = "",
        **kwargs,
    ):
        self.requirements = []
        self.AI_PROVIDER_URI = AI_PROVIDER_URI
        self.MAX_TOKENS = MAX_TOKENS
        self.AI_TEMPERATURE = AI_TEMPERATURE
        self.AI_MODEL = AI_MODEL
        self.API_KEY = API_KEY

    @threaded
    def instruct(self, prompt, tokens: int = 0):
        headers = {"Authorization": f"Bearer {self.API_KEY}"}
        max_tokens = (
            int(self.MAX_TOKENS) - tokens
            if int(self.MAX_TOKENS) > tokens
            else self.MAX_TOKENS
        )

        run_response = requests.post(
            f"{self.AI_PROVIDER_URI}/run",
            headers=headers,
            json={
                "input": {
                    "prompt": prompt,
                    "max_context_length": max_tokens,
                    "max_length": 200,
                    "temperature": float(self.AI_TEMPERATURE),
                },
            },
        )
        logging.info("Run Response: %s", run_response.json())
        jobId = run_response.json()["id"]
        logging.info("Job ID: %s", jobId)
        while True:
            status_url = f"{self.AI_PROVIDER_URI}/status/{jobId}"
            logging.info("Requesting status url: %s", status_url)
            status_response = requests.get(status_url, headers=headers)
            logging.info("Status Response: %s", status_response.json())
            status = status_response.json()["status"]
            logging.info("Status: %s", status)
            # IN_QUEUE, RUNNING, DONE, FAILED
            if status == "DONE":
                url = response.json()["results"]["url"]
                logging.debug("URL: %s", status)
                result = requests.get(
                    f"{self.AI_PROVIDER_URI}/status/{jobId}", headers=headers
                )
                logging.debug("Result: %s", result.json())
                return result["output"]
            elif status == "FAILED":
                logging.info("JOB FAILD - NEEDS HANDLING")
                return None
            else:
                logging.info("Sleeping for 2")
                time.sleep(2)
