from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "coverage",
    "playwright-report",
    "test-results",
    "__pycache__",
}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_/+=.-]{20,}"
    ),
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name in FORBIDDEN_NAMES:
            findings.append(f"forbidden file: {path.relative_to(ROOT)}")
            continue
        if path.name == ".env.example" or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {path.relative_to(ROOT)}")
    if findings:
        print("Potential secrets detected:\n" + "\n".join(findings))
        return 1
    print("Secret scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
