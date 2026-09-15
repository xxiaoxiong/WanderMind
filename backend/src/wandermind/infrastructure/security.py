from __future__ import annotations

from wandermind.infrastructure.errors import UnsafeInputError


def validate_safe_text(text: str, *, max_length: int) -> str:
    if not text.strip():
        raise UnsafeInputError("text cannot be empty")
    if len(text) > max_length:
        raise UnsafeInputError("text exceeds the configured size limit")
    if any((ord(char) < 32 and ord(char) not in {9, 10, 13}) or ord(char) == 127 for char in text):
        raise UnsafeInputError("text contains disallowed control characters")
    if _longest_character_run(text) >= 128:
        raise UnsafeInputError("text contains an excessive repeated-character run")
    return text


def redact_secrets(value: object) -> object:
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            lowered = key.casefold()
            if any(marker in lowered for marker in ("secret", "token", "password", "api_key")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    return value


def validate_safe_metadata(metadata: dict[str, object]) -> dict[str, object]:
    node_count = 0

    def visit(value: object, depth: int) -> None:
        nonlocal node_count
        node_count += 1
        if node_count > 500:
            raise UnsafeInputError("metadata contains too many values")
        if depth > 5:
            raise UnsafeInputError("metadata nesting exceeds the configured limit")
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str) or not key or len(key) > 100:
                    raise UnsafeInputError("metadata keys must be 1 to 100 characters")
                if any(ord(char) < 32 or ord(char) == 127 for char in key):
                    raise UnsafeInputError("metadata key contains control characters")
                lowered = key.casefold()
                if any(marker in lowered for marker in ("secret", "token", "password", "api_key")):
                    raise UnsafeInputError("metadata must not contain credentials")
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth + 1)
        elif isinstance(value, str):
            validate_safe_text(value, max_length=5_000)
        elif value is not None and not isinstance(value, bool | int | float):
            raise UnsafeInputError("metadata values must be JSON-compatible")

    visit(metadata, 0)
    return metadata


def _longest_character_run(text: str) -> int:
    longest = 0
    current = 0
    previous = ""
    for char in text:
        if char == previous:
            current += 1
        else:
            previous = char
            current = 1
        longest = max(longest, current)
    return longest
