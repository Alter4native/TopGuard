from abc import ABC, abstractmethod
from collections.abc import Sequence

import httpx

from app.events.schemas import VisionEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, events: Sequence[VisionEvent]) -> None:
        raise NotImplementedError


class InMemoryEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[VisionEvent] = []

    def publish(self, events: Sequence[VisionEvent]) -> None:
        self.events.extend(events)


class HttpEventPublisher(EventPublisher):
    def __init__(self, backend_internal_url: str, service_token: str, timeout_seconds: float = 5.0) -> None:
        self.backend_internal_url = backend_internal_url.rstrip("/")
        self.service_token = service_token
        self.timeout_seconds = timeout_seconds

    def publish(self, events: Sequence[VisionEvent]) -> None:
        if not events:
            return

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.backend_internal_url}/events",
                headers={"Authorization": f"Bearer {self.service_token}"},
                json={"events": [event.as_dict() for event in events]},
            )
            response.raise_for_status()

