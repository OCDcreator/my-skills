#!/usr/bin/env python3
"""Generate or redraw math images for Obsidian notes via an OpenAI-compatible Images API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_DIALECT = "openai-native"
DEFAULT_SIZE = "auto"
DEFAULT_BACKGROUND = "auto"
DEFAULT_FORMAT = "png"


def load_dotenv_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env() -> None:
    candidates = [
        Path.cwd() / ".env",
        SKILL_DIR / ".env",
        Path.home() / ".codex" / ".env",
    ]
    explicit = os.environ.get("OPENAI_IMAGE_ENV")
    if explicit:
        candidates.insert(0, Path(explicit))
    for candidate in candidates:
        load_dotenv_file(candidate)


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def read_prompt(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.prompt:
        parts.append(args.prompt)
    if args.prompt_file:
        parts.append(Path(args.prompt_file).read_text(encoding="utf-8"))
    prompt = "\n\n".join(part.strip() for part in parts if part.strip())
    if not prompt:
        raise SystemExit("FAIL: provide --prompt or --prompt-file.")
    return prompt


def api_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def post_json(url: str, api_key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    return send(req)


def multipart_body(fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----math-to-obsidian-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, path in files:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {mime}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_multipart(url: str, api_key: str, fields: dict[str, str], files: list[tuple[str, Path]]) -> dict:
    body, content_type = multipart_body(fields, files)
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method="POST",
    )
    return send(req)


def send(req: request.Request) -> dict:
    try:
        with request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"FAIL: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"FAIL: request failed: {exc}") from exc


def write_output(response_json: dict, output: Path) -> None:
    data = response_json.get("data") or []
    if not data:
        raise SystemExit("FAIL: image API response did not contain data.")
    first = data[0]
    b64 = first.get("b64_json") or first.get("b64")
    if not b64:
        raise SystemExit("FAIL: image API response did not contain base64 image data.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(b64))
    print(str(output))


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--input-image", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", default=env("OPENAI_IMAGE_SIZE", DEFAULT_SIZE))
    parser.add_argument("--background", default=env("OPENAI_IMAGE_BACKGROUND", DEFAULT_BACKGROUND))
    parser.add_argument("--output-format", default=env("OPENAI_IMAGE_OUTPUT_FORMAT", DEFAULT_FORMAT))
    parser.add_argument("--quality", default=env("OPENAI_IMAGE_QUALITY"))
    parser.add_argument("--model", default=env("OPENAI_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=env("OPENAI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--dialect", default=env("OPENAI_IMAGE_API_DIALECT", DEFAULT_DIALECT))
    args = parser.parse_args()

    api_key = env("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("FAIL: OPENAI_API_KEY is required.")
    if args.dialect != "openai-native":
        raise SystemExit("FAIL: only OPENAI_IMAGE_API_DIALECT=openai-native is supported.")
    if args.background == "transparent" and args.output_format not in {"png", "webp"}:
        raise SystemExit("FAIL: transparent background requires png or webp output format.")

    prompt = read_prompt(args)
    common = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "background": args.background,
        "output_format": args.output_format,
    }
    if args.quality:
        common["quality"] = args.quality

    if args.input_image:
        for image in args.input_image:
            if not image.exists():
                raise SystemExit(f"FAIL: input image does not exist: {image}")
        fields = {key: str(value) for key, value in common.items() if value is not None}
        files = [("image", image) for image in args.input_image]
        result = post_multipart(api_url(args.base_url, "images/edits"), api_key, fields, files)
    else:
        result = post_json(api_url(args.base_url, "images/generations"), api_key, common)

    write_output(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
