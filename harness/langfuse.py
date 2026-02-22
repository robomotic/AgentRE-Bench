from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
import urllib.request

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NoopLangfuseClient:
    enabled = False

    def create_task_trace(self, **kwargs) -> str | None:
        return None

    def update_trace(self, trace_id: str, **kwargs) -> None:
        return None

    def create_generation(self, trace_id: str | None, **kwargs) -> str | None:
        return None

    def end_generation(self, trace_id: str | None, generation_id: str | None, **kwargs) -> None:
        return None

    def create_span(self, trace_id: str | None, **kwargs) -> str | None:
        return None

    def end_span(self, trace_id: str | None, span_id: str | None, **kwargs) -> None:
        return None

    def create_event(self, trace_id: str | None, **kwargs) -> None:
        return None


class LangfuseClient:
    enabled = True

    def __init__(self, public_key: str, secret_key: str, host: str = "https://cloud.langfuse.com"):
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host.rstrip("/")
        token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {token}"
        self._warned = False

    def _truncate(self, value: Any, max_chars: int = 12000) -> Any:
        text = json.dumps(value, default=str) if isinstance(value, (dict, list, tuple)) else str(value)
        if len(text) <= max_chars:
            return value
        return text[:max_chars] + "... [truncated]"

    def _emit(self, event_type: str, body: dict[str, Any]) -> None:
        payload = {
            "batch": [
                {
                    "id": str(uuid.uuid4()),
                    "type": event_type,
                    "timestamp": _now_iso(),
                    "body": body,
                }
            ],
            "metadata": {"sdk_integration": "agentre-bench-raw-http"},
        }
        data = json.dumps(payload, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._auth_header,
        }
        url = f"{self.host}/api/public/ingestion"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15):
                pass
        except Exception as e:
            if not self._warned:
                log.warning("Langfuse emission failed (suppressing further warnings): %s", e)
                self._warned = True

    def create_task_trace(
        self,
        task_id: str,
        model: str,
        provider: str,
        difficulty: int,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        trace_id = str(uuid.uuid4())
        body = {
            "id": trace_id,
            "name": f"task:{task_id}",
            "sessionId": f"{provider}:{model}",
            "metadata": {
                "task_id": task_id,
                "provider": provider,
                "model": model,
                "difficulty": difficulty,
                **(metadata or {}),
            },
        }
        self._emit("trace-create", body)
        return trace_id

    def update_trace(
        self,
        trace_id: str,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
        level: str | None = None,
        status_message: str | None = None,
    ) -> None:
        body: dict[str, Any] = {"id": trace_id}
        if output is not None:
            body["output"] = self._truncate(output)
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if level is not None:
            body["level"] = level
        if status_message is not None:
            body["statusMessage"] = status_message
        self._emit("trace-update", body)

    def create_generation(
        self,
        trace_id: str | None,
        name: str,
        model: str,
        input: Any,
        metadata: dict[str, Any] | None = None,
        parent_observation_id: str | None = None,
    ) -> str | None:
        if not trace_id:
            return None
        generation_id = str(uuid.uuid4())
        body = {
            "id": generation_id,
            "traceId": trace_id,
            "name": name,
            "model": model,
            "input": self._truncate(input),
        }
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if parent_observation_id:
            body["parentObservationId"] = parent_observation_id
        self._emit("generation-create", body)
        return generation_id

    def end_generation(
        self,
        trace_id: str | None,
        generation_id: str | None,
        output: Any,
        usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        level: str | None = None,
        status_message: str | None = None,
    ) -> None:
        if not trace_id or not generation_id:
            return
        body: dict[str, Any] = {
            "id": generation_id,
            "traceId": trace_id,
            "output": self._truncate(output),
            "endTime": _now_iso(),
        }
        if usage is not None:
            body["usage"] = usage
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if level is not None:
            body["level"] = level
        if status_message is not None:
            body["statusMessage"] = status_message
        self._emit("generation-update", body)

    def create_span(
        self,
        trace_id: str | None,
        name: str,
        input: Any,
        metadata: dict[str, Any] | None = None,
        parent_observation_id: str | None = None,
    ) -> str | None:
        if not trace_id:
            return None
        span_id = str(uuid.uuid4())
        body: dict[str, Any] = {
            "id": span_id,
            "traceId": trace_id,
            "name": name,
            "input": self._truncate(input),
        }
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if parent_observation_id:
            body["parentObservationId"] = parent_observation_id
        self._emit("span-create", body)
        return span_id

    def end_span(
        self,
        trace_id: str | None,
        span_id: str | None,
        output: Any,
        metadata: dict[str, Any] | None = None,
        level: str | None = None,
        status_message: str | None = None,
    ) -> None:
        if not trace_id or not span_id:
            return
        body: dict[str, Any] = {
            "id": span_id,
            "traceId": trace_id,
            "output": self._truncate(output),
            "endTime": _now_iso(),
        }
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if level is not None:
            body["level"] = level
        if status_message is not None:
            body["statusMessage"] = status_message
        self._emit("span-update", body)

    def create_event(
        self,
        trace_id: str | None,
        name: str,
        input: Any | None = None,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
        level: str | None = None,
        status_message: str | None = None,
        parent_observation_id: str | None = None,
    ) -> None:
        if not trace_id:
            return
        body: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "traceId": trace_id,
            "name": name,
        }
        if input is not None:
            body["input"] = self._truncate(input)
        if output is not None:
            body["output"] = self._truncate(output)
        if metadata is not None:
            body["metadata"] = self._truncate(metadata)
        if level is not None:
            body["level"] = level
        if status_message is not None:
            body["statusMessage"] = status_message
        if parent_observation_id:
            body["parentObservationId"] = parent_observation_id
        self._emit("event-create", body)


def create_langfuse_client(
    public_key: str | None,
    secret_key: str | None,
    host: str = "https://cloud.langfuse.com",
) -> LangfuseClient | NoopLangfuseClient:
    if public_key and secret_key:
        return LangfuseClient(public_key=public_key, secret_key=secret_key, host=host)
    return NoopLangfuseClient()
