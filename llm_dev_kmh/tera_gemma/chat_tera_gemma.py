#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_PROMPT_FILE = (
    REPO_ROOT / "prompts" / "local_model_prompts" / "tera_local_model_system_prompt.md"
)

BASE_MODEL = os.getenv("TERA_GEMMA_BASE_MODEL", "gemma3:4b")
CHAT_MODEL = os.getenv("TERA_GEMMA_MODEL", BASE_MODEL)
TUNED_MODEL = os.getenv("TERA_GEMMA_TUNED_MODEL", "tera-agent-gemma3:4b")
PROMPT_FILE = Path(os.getenv("TERA_GEMMA_PROMPT_FILE", str(DEFAULT_PROMPT_FILE)))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
TEMPERATURE = float(os.getenv("TERA_GEMMA_TEMPERATURE", "0.1"))
NUM_CTX = int(os.getenv("TERA_GEMMA_NUM_CTX", "4096"))
NUM_PREDICT = int(os.getenv("TERA_GEMMA_NUM_PREDICT", "256"))
NUM_GPU = os.getenv("TERA_GEMMA_NUM_GPU")
KEEP_ALIVE = os.getenv("TERA_GEMMA_KEEP_ALIVE", "30m")
REQUEST_TIMEOUT_S = float(os.getenv("TERA_GEMMA_TIMEOUT_S", "180"))
MAX_HISTORY_TURNS = int(os.getenv("TERA_GEMMA_HISTORY_TURNS", "4"))
AUTO_PULL = os.getenv("TERA_GEMMA_AUTO_PULL", "").lower() in {"1", "true", "yes"}
DEFAULT_RUNTIME_CONTEXT = """
Runtime context for this process:
- This is the terminal harness for local TERA Gemma testing.
- There is no live ATAK plugin attached to this terminal.
- There is no live map_state, CoT object registry, route dispatcher, or
  geospatial query result attached unless the user pastes it into chat.
- In deployed TERA, the ATAK plugin sends text or speech-to-text prompts and
  map context over local IP to the Jetson. The Jetson app runs local geo
  queries, creates routes/control measures/chat responses/CoT, and sends those
  results back to the plugin for display.
- In this terminal harness, describe the intended Jetson-side query, routing,
  control-measure, or CoT update sequence when live tools are required.
""".strip()
RUNTIME_CONTEXT = os.getenv("TERA_GEMMA_RUNTIME_CONTEXT", DEFAULT_RUNTIME_CONTEXT)


def fail(message: str, exit_code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def run_command(command: list[str], timeout_s: float = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_s,
    )


def run_ollama(
    *args: str, capture: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ollama", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def extract_system_prompt(prompt_file: Path) -> str:
    try:
        markdown = prompt_file.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"could not read prompt file {prompt_file}: {exc}")

    match = re.search(r"```(?:[A-Za-z0-9_-]+)?\s*\n(?P<body>[\s\S]*?)\n```", markdown)
    if match:
        return match.group("body").strip()
    return markdown.strip()


def modelfile_literal(value: str) -> str:
    return value.replace('"""', r"\"\"\"")


def ensure_ollama_available() -> None:
    if shutil.which("ollama") is None:
        fail("ollama was not found on PATH. Install/start Ollama first.")


def ensure_ollama_server() -> subprocess.Popen[bytes] | None:
    if run_ollama("list", capture=True, check=False).returncode == 0:
        return None

    print(
        "Ollama is not responding; starting `ollama serve` for this chat session...",
        flush=True,
    )
    process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(40):
        time.sleep(0.25)
        if run_ollama("list", capture=True, check=False).returncode == 0:
            return process

    process.terminate()
    fail("started `ollama serve`, but the Ollama API did not become ready")


def model_exists(model_name: str) -> bool:
    return run_ollama("show", model_name, capture=True, check=False).returncode == 0


def ensure_model(model_name: str) -> None:
    if model_exists(model_name):
        return

    if AUTO_PULL:
        print(
            f"Model {model_name} is missing; pulling because TERA_GEMMA_AUTO_PULL=1...",
            flush=True,
        )
        run_ollama("pull", model_name)
        return

    fail(
        f"model {model_name} is not installed. Run `ollama pull {model_name}` "
        "before going offline, or set TERA_GEMMA_AUTO_PULL=1 to let this script pull it."
    )


def create_tuned_model(system_prompt: str) -> None:
    lines = [
        f"FROM {BASE_MODEL}",
        f"PARAMETER temperature {TEMPERATURE}",
        f"PARAMETER num_ctx {NUM_CTX}",
        f"PARAMETER num_predict {NUM_PREDICT}",
    ]
    if NUM_GPU:
        lines.append(f"PARAMETER num_gpu {int(NUM_GPU)}")
    lines.extend([f'SYSTEM """{modelfile_literal(system_prompt)}"""', ""])
    modelfile = "\n".join(lines)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(modelfile)
        tmp_path = Path(tmp.name)

    try:
        print(f"Creating Ollama model {TUNED_MODEL} from {BASE_MODEL}...", flush=True)
        run_ollama("create", TUNED_MODEL, "-f", str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)


def ollama_chat(
    model: str,
    system_prompt: str,
    history: list[dict[str, str]],
    user_prompt: str,
) -> tuple[str, float]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": RUNTIME_CONTEXT},
    ]
    messages.extend(history[-MAX_HISTORY_TURNS * 2 :])
    messages.append({"role": "user", "content": user_prompt})
    options: dict[str, Any] = {
        "temperature": TEMPERATURE,
        "num_ctx": NUM_CTX,
        "num_predict": NUM_PREDICT,
    }
    if NUM_GPU:
        options["num_gpu"] = int(NUM_GPU)

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "keep_alive": KEEP_ALIVE,
        "options": options,
    }

    start = time.perf_counter()
    try:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        detail = f" HTTP {exc.code}"
        if body:
            detail += f": {body}"
        fail(f"could not reach Ollama at {OLLAMA_BASE_URL}:{detail}")
    except urllib.error.URLError as exc:
        fail(f"could not reach Ollama at {OLLAMA_BASE_URL}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Ollama returned invalid JSON: {exc}")

    elapsed_s = time.perf_counter() - start
    try:
        return str(data["message"]["content"]), elapsed_s
    except KeyError:
        fail(f"Ollama response did not contain message.content: {data}")


def parse_model_json(raw: str) -> tuple[str, list[Any], bool]:
    cleaned = raw.strip()
    fence = re.search(r"```(?:json)?\s*(?P<body>[\s\S]*?)\s*```", cleaned)
    if fence:
        cleaned = fence.group("body").strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return cleaned, [], False

    if isinstance(payload, dict):
        message = payload.get("assistantMessage") or payload.get("message") or ""
        actions = payload.get("actions", [])
        if isinstance(message, str):
            return message.strip(), actions if isinstance(actions, list) else [], True

    return cleaned, [], False


def print_response(
    raw: str,
    *,
    show_raw: bool,
    show_actions: bool,
    show_latency: bool,
    latency_s: float,
) -> None:
    message, actions, parsed = parse_model_json(raw)
    if message:
        print(f"TERA> {message}")
    else:
        print(f"TERA> {raw.strip()}")

    if show_actions and actions:
        print(json.dumps({"actions": actions}, separators=(",", ":")))
    if show_raw and not parsed:
        print(f"[raw] {raw.strip()}")
    if show_latency:
        print(f"[{latency_s:.1f}s]")


def preload_model(model: str, system_prompt: str) -> None:
    print(f"Preloading {model}; this is the only step that should feel slow...", flush=True)
    raw, latency_s = ollama_chat(
        model,
        system_prompt,
        [],
        "Reply with a five-word readiness check.",
    )
    message, _, _ = parse_model_json(raw)
    print(f"Ready: {message or raw.strip()} [{latency_s:.1f}s]")


def command_output(label: str, command: list[str], timeout_s: float = 8) -> str:
    if shutil.which(command[0]) is None:
        return f"{label}: not found"
    try:
        result = run_command(command, timeout_s=timeout_s)
    except subprocess.TimeoutExpired:
        return f"{label}: timed out"

    output = result.stdout.strip()
    if not output:
        output = f"exit {result.returncode} with no output"
    return f"{label}:\n{output}"


def nvcc_diagnostics() -> str:
    candidates = [
        shutil.which("nvcc"),
        "/usr/local/cuda/bin/nvcc",
        "/usr/local/cuda-12.6/bin/nvcc",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return command_output("nvcc", [str(path), "--version"])
    return "nvcc: not found on PATH or common CUDA locations"


def tegrastats_sample() -> str:
    if shutil.which("tegrastats") is None:
        return "tegrastats: not found"

    process = subprocess.Popen(
        ["tegrastats", "--interval", "1000"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        time.sleep(1.4)
        process.terminate()
        output, _ = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()

    output = output.strip()
    if not output:
        output = "no sample captured"
    return "tegrastats:\n" + output


def package_diagnostics() -> str:
    if shutil.which("dpkg-query") is None:
        return "CUDA package scan: dpkg-query not found"

    try:
        result = run_command(
            ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n"],
            timeout_s=12,
        )
    except subprocess.TimeoutExpired:
        return "CUDA package scan: timed out"

    needles = (
        "cuda",
        "cudnn",
        "tensorrt",
        "nvidia-jetpack",
        "nvidia-l4t",
        "libnvinfer",
        "nvidia-container",
    )
    lines = [
        line
        for line in result.stdout.splitlines()
        if any(needle in line.lower() for needle in needles)
    ]
    if not lines:
        return "CUDA package scan: no CUDA/Jetson packages found by dpkg-query"
    return "CUDA package scan:\n" + "\n".join(lines[:80])


def print_diagnostics(model: str) -> None:
    print("TERA Gemma diagnostics")
    print(f"host: {platform.platform()} ({platform.machine()})")
    print(f"python: {sys.version.split()[0]}")
    print(f"ollama_url: {OLLAMA_BASE_URL}")
    print(f"model: {model}")
    print(f"prompt: {PROMPT_FILE}")
    print(
        "options: "
        f"num_ctx={NUM_CTX} num_predict={NUM_PREDICT} "
        f"num_gpu={NUM_GPU or 'auto'}"
    )
    print()
    print(command_output("ollama version", ["ollama", "--version"]))
    print()
    print(command_output("ollama list", ["ollama", "list"]))
    print()
    print(command_output("ollama ps", ["ollama", "ps"]))
    print()
    print(command_output("nvpmodel", ["nvpmodel", "-q"]))
    print()
    print(command_output("jetson_clocks", ["jetson_clocks", "--show"]))
    print()
    print(command_output("nvidia-smi", ["nvidia-smi"]))
    print()
    print(tegrastats_sample())
    print()
    print(nvcc_diagnostics())
    print()
    print(package_diagnostics())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Chat with TERA through local Ollama. Omit PROMPT for an interactive "
            "terminal chat."
        )
    )
    parser.add_argument("prompt", nargs="*", help="optional one-shot prompt")
    parser.add_argument("--model", default=CHAT_MODEL, help=f"Ollama model, default {CHAT_MODEL}")
    parser.add_argument(
        "--preload",
        action="store_true",
        help="load the model before showing the chat prompt",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="print Ollama, CUDA, and Jetson package diagnostics, then exit",
    )
    parser.add_argument(
        "--show-actions",
        action="store_true",
        help="also print parsed action JSON when the model returns actions",
    )
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="print raw model text when JSON parsing fails",
    )
    parser.add_argument(
        "--show-latency",
        action="store_true",
        help="print response latency after each answer",
    )
    parser.add_argument(
        "--rebuild-model",
        action="store_true",
        help=f"rebuild the optional tuned Ollama alias {TUNED_MODEL} and use it",
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="compatibility flag; dynamic prompting is now used by default",
    )
    return parser.parse_args()


def chat_loop(args: argparse.Namespace, system_prompt: str) -> int:
    history: list[dict[str, str]] = []

    while True:
        try:
            user_prompt = input("USER> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 130

        if not user_prompt:
            continue
        if user_prompt in {"/bye", "/exit", "/quit"}:
            return 0
        if user_prompt in {"/diag", "/gpu"}:
            print_diagnostics(args.model)
            continue

        raw, latency_s = ollama_chat(args.model, system_prompt, history, user_prompt)
        print_response(
            raw,
            show_raw=args.show_raw,
            show_actions=args.show_actions,
            show_latency=args.show_latency,
            latency_s=latency_s,
        )
        history.extend(
            [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw},
            ]
        )


def main() -> int:
    args = parse_args()
    ensure_ollama_available()
    server_process = ensure_ollama_server()

    try:
        system_prompt = extract_system_prompt(PROMPT_FILE)
        if not system_prompt:
            fail(f"prompt file {PROMPT_FILE} did not contain any prompt text")

        if args.rebuild_model:
            ensure_model(BASE_MODEL)
            create_tuned_model(system_prompt)
            args.model = TUNED_MODEL
        else:
            ensure_model(args.model)

        if args.diagnostics:
            print_diagnostics(args.model)
            return 0

        if args.preload:
            preload_model(args.model, system_prompt)

        if args.prompt:
            user_prompt = " ".join(args.prompt)
            raw, latency_s = ollama_chat(args.model, system_prompt, [], user_prompt)
            print_response(
                raw,
                show_raw=args.show_raw,
                show_actions=args.show_actions,
                show_latency=args.show_latency,
                latency_s=latency_s,
            )
            return 0

        return chat_loop(args, system_prompt)
    finally:
        if server_process is not None:
            server_process.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
