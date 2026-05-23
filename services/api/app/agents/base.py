import json
import redis
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseAgent(ABC):
    def __init__(self, job_id: str, redis_client: redis.Redis):
        self.job_id = job_id
        self.r = redis_client

    def emit(self, step_name: str, status: str, message: str | None = None) -> None:
        step = {
            "name": step_name,
            "status": status,
            "message": message,
            "startedAt": datetime.now(timezone.utc).isoformat() if status == "running" else None,
            "completedAt": datetime.now(timezone.utc).isoformat()
            if status in ("completed", "failed")
            else None,
        }
        self.r.publish(f"job:progress:{self.job_id}", json.dumps(step))

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the agent. Returns output_data dict."""
        ...
