#!/usr/bin/env python3
"""clipboard - Clipboard manager with history.

One file. Zero deps. Remember what you copied.

Usage:
  clipboard.py copy "text"         → copy to clipboard
  clipboard.py paste               → paste from clipboard
  clipboard.py history              → show clipboard history
  clipboard.py pick 3               → paste item #3 from history
  clipboard.py clear                → clear history
  echo "text" | clipboard.py copy   → pipe to clipboard
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time

HISTORY_PATH = os.path.expanduser("~/.cache/clipboard_history.json")
MAX_HISTORY = 50


def _copy(text: str):
    if platform.system() == "Darwin":
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
    elif platform.system() == "Linux":
        for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
            try:
                subprocess.run(cmd, input=text.encode(), check=True)
                return
            except FileNotFoundError:
                continue


def _paste() -> str:
    if platform.system() == "Darwin":
        r = subprocess.run(["pbpaste"], capture_output=True)
        return r.stdout.decode()
    elif platform.system() == "Linux":
        for cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
            try:
                r = subprocess.run(cmd, capture_output=True)
                return r.stdout.decode()
            except FileNotFoundError:
                continue
    return ""


def load_history() -> list:
    try:
        with open(HISTORY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(history: list):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history[-MAX_HISTORY:], f)


def add_to_history(text: str):
    history = load_history()
    history.append({"text": text, "time": time.time()})
    save_history(history)


def cmd_copy(args):
    if args.text:
        text = " ".join(args.text)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Nothing to copy", file=sys.stderr)
        return 1
    _copy(text)
    add_to_history(text)
    print(f"✅ Copied ({len(text)} chars)")


def cmd_paste(args):
    print(_paste(), end="")


def cmd_history(args):
    history = load_history()
    if not history:
        print("(empty history)")
        return
    for i, entry in enumerate(reversed(history[-20:]), 1):
        preview = entry["text"][:60].replace("\n", "\\n")
        print(f"  {i:3d}  {preview}")


def cmd_pick(args):
    history = load_history()
    idx = len(history) - args.n
    if idx < 0 or idx >= len(history):
        print(f"Invalid index {args.n}", file=sys.stderr)
        return 1
    text = history[idx]["text"]
    _copy(text)
    print(text, end="")


def cmd_clear(args):
    save_history([])
    print("✅ History cleared")


def main():
    p = argparse.ArgumentParser(description="Clipboard manager with history")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("copy")
    s.add_argument("text", nargs="*")

    sub.add_parser("paste")
    sub.add_parser("history")

    s = sub.add_parser("pick")
    s.add_argument("n", type=int)

    sub.add_parser("clear")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1
    cmds = {"copy": cmd_copy, "paste": cmd_paste, "history": cmd_history,
            "pick": cmd_pick, "clear": cmd_clear}
    return cmds[args.cmd](args) or 0

if __name__ == "__main__":
    sys.exit(main())
