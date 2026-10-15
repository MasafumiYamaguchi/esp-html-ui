from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class CompileError(Exception):
    """A diagnostic safe to present without a Python traceback."""


@dataclass(frozen=True)
class Location:
    path: Path
    line: int | None = None
    column: int | None = None
    context: str = ""

    def error(self, message: str) -> CompileError:
        position = f":{self.line}:{self.column}" if self.line is not None else ""
        context = f" ({self.context})" if self.context else ""
        return CompileError(f"{self.path}{position}{context}: {message}")


@dataclass
class Node:
    tag: str
    kind: str
    id: str
    parent: int | None
    text: str
    style: dict[str, Any]
    hidden: bool = False
    disabled: bool = False
    focusable: bool = False


@dataclass
class Document:
    name: str
    width: int
    height: int
    nodes: list[Node] = field(default_factory=list)
    sources: list[Path] = field(default_factory=list)
