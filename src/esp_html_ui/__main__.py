import argparse
import json
import sys
from pathlib import Path

from .codegen import generate
from .compiler import compile_document
from .css import CAPABILITIES
from .model import CompileError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="esp-html-ui")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_parser = commands.add_parser("compile", help="Compile HTML and linked CSS into LVGL C++")
    compile_parser.add_argument("html", type=Path)
    compile_parser.add_argument("--output", type=Path, required=True)
    compile_parser.add_argument("--name", default="counter")
    compile_parser.add_argument("--width", type=int, default=320)
    compile_parser.add_argument("--height", type=int, default=170)
    commands.add_parser("support", help="Print implemented capabilities and planned features as JSON")
    args = parser.parse_args(argv)
    if args.command == "support":
        print(json.dumps(CAPABILITIES, ensure_ascii=False, indent=2))
        return 0
    try:
        document = compile_document(args.html, args.name, args.width, args.height)
        outputs = generate(document)
        args.output.mkdir(parents=True, exist_ok=True)
        for filename, content in outputs.items():
            target = args.output / filename
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                target.write_text(content, encoding="utf-8")
        print(f"Generated {len(document.nodes)} LVGL objects in {args.output}")
    except (CompileError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
