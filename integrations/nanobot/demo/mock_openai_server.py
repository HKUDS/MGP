from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _build_reply(messages: list[dict]) -> str:
    system_parts = [_text_content(m.get("content")) for m in messages if m.get("role") == "system"]
    user_parts = [_text_content(m.get("content")) for m in messages if m.get("role") == "user"]

    system_text = "\n".join(part for part in system_parts if part)
    latest_user_text = next((part for part in reversed(user_parts) if part), "").lower()

    has_governed_memory = "Governed Memory Recall" in system_text
    remembers_concise = "concise replies" in system_text or "response_style" in system_text

    if "prefer concise replies" in latest_user_text:
        return "Understood. I will remember that you prefer concise replies."

    if (
        "concise replies" in latest_user_text
        or "reply preference" in latest_user_text
        or "response style" in latest_user_text
    ):
        if has_governed_memory and remembers_concise:
            return "According to governed memory, you prefer concise replies."
        return "I do not have governed memory in the prompt right now, so I cannot confirm your reply preference."

    if has_governed_memory:
        return "I can see governed memory in the prompt and will use it when relevant."

    return "This is a mock Nanobot reply without governed memory context."


class MockOpenAIHandler(BaseHTTPRequestHandler):
    server_version = "MockOpenAI/0.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8") or "{}")
        messages = payload.get("messages", [])
        content = _build_reply(messages)

        body = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 0,
            "model": payload.get("model", "mock-model"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 32,
                "completion_tokens": 16,
                "total_tokens": 48,
            },
        }

        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/v1/models"}:
            body = {
                "object": "list",
                "data": [{"id": "mock-model", "object": "model"}],
            }
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 18081), MockOpenAIHandler)
    try:
        print("Mock OpenAI server listening on http://127.0.0.1:18081")
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
