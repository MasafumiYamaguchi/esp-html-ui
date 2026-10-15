"""CSS semantics and LVGL value validation; syntax belongs to tinycss2/cssselect2."""

import copy
import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import cssselect2
import tinycss2
from tinycss2.color3 import parse_color

from .model import CompileError, Location

CAPABILITIES = json.loads(files("esp_html_ui").joinpath("capabilities.json").read_text())
INHERITED = {"color", "font-size", "text-align", "white-space"}
DYNAMIC = {"hover", "focus", "focus-visible", "focus-within", "active", "disabled", "enabled", "checked"}
SHORTHANDS = {"padding": ["padding-top", "padding-right", "padding-bottom", "padding-left"],
              "gap": ["row-gap", "column-gap"]}


@dataclass
class Declaration:
    name: str
    tokens: list
    important: bool
    location: Location


def significant(tokens):
    return [t for t in tokens if t.type not in {"whitespace", "comment"}]


def declarations(tokens, location):
    result = []
    for decl in tinycss2.parse_declaration_list(tokens, skip_comments=True, skip_whitespace=True):
        loc = Location(location.path, getattr(decl, "source_line", None),
                       getattr(decl, "source_column", None), location.context)
        if decl.type == "error":
            raise loc.error(decl.message)
        if decl.type != "declaration":
            raise loc.error("Expected a CSS declaration")
        name = decl.name if decl.name.startswith("--") else decl.lower_name
        if not name.startswith("--") and name not in CAPABILITIES["css"]:
            raise loc.error(f"Unsupported CSS property in 0.1: {name}")
        # Diagnose unsupported literal values even in a rule that matches no node.
        # var() values require element-specific substitution and are checked later.
        serialized = tinycss2.serialize(decl.value)
        if not name.startswith("--") and "var(" not in serialized.lower():
            for longhand, value in expand(name, significant(decl.value), loc).items():
                if tinycss2.serialize(value).strip().lower() not in {"initial", "inherit", "unset"}:
                    value_for(longhand, value, loc)
        result.append(Declaration(name, decl.value, decl.important, loc))
    return result


def reject_dynamic(tokens, location):
    tokens = significant(tokens)
    for i, token in enumerate(tokens):
        if token.type == "literal" and token.value == ":" and i + 1 < len(tokens):
            following = tokens[i + 1]
            if following.type == "ident" and following.lower_value in DYNAMIC:
                raise location.error(f"Dynamic selector :{following.value} is planned, not implemented in 0.1")
        if token.type == "function":
            reject_dynamic(token.arguments, location)
        elif token.type in {"[] block", "() block"}:
            # Attribute contents are values, not selectors.
            if token.type == "() block":
                reject_dynamic(token.content, location)


def variable_references(tokens):
    result = set()
    for token in tokens or []:
        if token.type == "function":
            arguments = significant(token.arguments)
            if token.lower_name == "var" and arguments and arguments[0].type == "ident":
                result.add(arguments[0].value)
            result.update(variable_references(token.arguments))
    return result


def cyclic_variables(variables):
    graph = {name: variable_references(value) & variables.keys() for name, value in variables.items()}
    invalid = set()
    for name, targets in graph.items():
        pending, seen = list(targets), set()
        while pending:
            target = pending.pop()
            if target == name:
                invalid.add(name)
                break
            if target not in seen:
                seen.add(target)
                pending.extend(graph[target])
    return invalid


class Stylesheet:
    def __init__(self):
        self.matcher = cssselect2.Matcher()

    def add(self, text: str, location: Location):
        for rule in tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True):
            loc = Location(location.path, rule.source_line, rule.source_column, location.context)
            if rule.type == "error":
                raise loc.error(rule.message)
            if rule.type != "qualified-rule":
                raise loc.error("CSS at-rules are not implemented in 0.1")
            reject_dynamic(rule.prelude, loc)
            try:
                selectors = cssselect2.compile_selector_list(rule.prelude)
            except cssselect2.SelectorError as error:
                raise loc.error(f"Invalid or unsupported selector: {error}") from error
            payload = declarations(rule.content, location)
            for selector in selectors:
                if selector.pseudo_element is not None or selector.never_matches:
                    raise loc.error("Unsupported pseudo-element or nonmatching selector")
                self.matcher.add_selector(selector, payload)

    def compute(self, wrapper, parent_style, parent_variables, location):
        candidates = []
        for specificity, order, _, decls in self.matcher.match(wrapper):
            for index, decl in enumerate(decls):
                candidates.append(((int(decl.important), 0, *specificity, order, index), decl))
        inline = wrapper.etree_element.get("style")
        if inline is not None:
            for index, decl in enumerate(declarations(inline, location)):
                candidates.append(((int(decl.important), 1, 0, 0, 0, 0, index), decl))

        raw_variables = dict(parent_variables)
        for _, decl in sorted(candidates, key=lambda item: item[0]):
            if decl.name.startswith("--"):
                keyword = tinycss2.serialize(decl.tokens).strip().lower()
                raw_variables[decl.name] = (None if keyword == "initial" else
                                           parent_variables.get(decl.name) if keyword in {"inherit", "unset"}
                                           else decl.tokens)
        for name in cyclic_variables(raw_variables):
            raw_variables[name] = None
        variables = {}
        for name, value in raw_variables.items():
            try:
                variables[name] = resolve(value, raw_variables, (name,), location)
            except CompileError:
                # An invalid custom property may be unused or consumed with a fallback.
                variables[name] = None

        style = defaults(wrapper.local_name)
        for name in INHERITED:
            if parent_style is not None:
                style[name] = parent_style[name]
        if wrapper.local_name.startswith("h") and wrapper.local_name in {f"h{i}" for i in range(1, 7)}:
            style["font-size"] = defaults(wrapper.local_name)["font-size"]
        winners = {}
        for priority, decl in candidates:
            if decl.name.startswith("--"):
                continue
            value = significant(resolve(decl.tokens, variables, (), decl.location))
            expanded = expand(decl.name, value, decl.location)
            for name, tokens in expanded.items():
                if name not in winners or priority >= winners[name][0]:
                    winners[name] = (priority, tokens, decl.location)
        for name, (_, tokens, loc) in winners.items():
            keyword = tinycss2.serialize(tokens).strip().lower()
            if keyword in {"initial", "inherit", "unset"}:
                inherits = keyword == "inherit" or keyword == "unset" and name in INHERITED
                style[name] = (parent_style[name] if inherits and parent_style is not None
                               else defaults("@initial")[name])
            else:
                style[name] = value_for(name, tokens, loc)
        return style, variables


def resolve(tokens, variables, trail, location):
    if tokens is None:
        raise location.error("Invalid CSS variable")
    result = []
    for token in tokens:
        if token.type == "error":
            raise location.error(token.message)
        if token.type == "function" and token.lower_name == "var":
            args = token.arguments
            comma = next((i for i, t in enumerate(args) if t.type == "literal" and t.value == ","), len(args))
            names = significant(args[:comma])
            if len(names) != 1 or names[0].type != "ident" or not names[0].value.startswith("--"):
                raise location.error("var() requires a custom property name")
            name = names[0].value
            try:
                if name in trail or name not in variables or variables[name] is None:
                    raise location.error(f"Undefined or cyclic CSS variable: {name}")
                replacement = resolve(variables[name], variables, (*trail, name), location)
            except CompileError:
                if comma == len(args):
                    raise
                replacement = resolve(args[comma + 1:], variables, trail, location)
            result.extend(replacement)
        elif token.type == "function":
            function = copy.copy(token)
            function.arguments = resolve(token.arguments, variables, trail, location)
            result.append(function)
        else:
            result.append(token)
    return result


def expand(name, tokens, location):
    if name not in SHORTHANDS:
        return {name: tokens}
    keyword = tinycss2.serialize(tokens).strip().lower()
    if keyword in {"inherit", "initial", "unset"}:
        return {key: tokens for key in SHORTHANDS[name]}
    count = len(tokens)
    if name == "padding" and 1 <= count <= 4:
        values = [tokens[0], tokens[1] if count > 1 else tokens[0],
                  tokens[2] if count > 2 else tokens[0], tokens[3] if count > 3 else tokens[1] if count > 1 else tokens[0]]
    elif name == "gap" and 1 <= count <= 2:
        values = [tokens[0], tokens[-1]]
    else:
        raise location.error(f"Invalid {name} shorthand")
    return {key: [value] for key, value in zip(SHORTHANDS[name], values)}


def defaults(tag):
    container = tag in CAPABILITIES["tags"] and CAPABILITIES["tags"][tag] == "container"
    block_label = tag == "p" or tag in {f"h{i}" for i in range(1, 7)}
    style: dict[str, Any] = {
        "display": "flex", "width": ["percent", 100] if container or block_label else ["auto", 0],
        "height": ["percent", 100] if tag == "body" else ["auto", 0],
        "box-sizing": "border-box", "color": [0xffffff, 255], "background-color": [0, 0],
        "opacity": 255, "row-gap": 0, "column-gap": 0,
        "padding-top": 0, "padding-right": 0, "padding-bottom": 0, "padding-left": 0,
        "border-width": 0, "border-color": [0, 255], "border-radius": 0,
        "flex-direction": "column", "flex-wrap": "nowrap", "flex-grow": 0,
        "justify-content": "flex-start", "align-items": "flex-start", "align-content": "flex-start",
        "font-size": {"h1": 32, "h2": 24, "h3": 20}.get(tag, 16), "text-align": "left",
        "white-space": "normal", "text-overflow": "clip", "overflow": "hidden",
    }
    if tag == "button":
        style.update({"background-color": [0x2563eb, 255], "border-radius": 6,
                      "padding-top": 8, "padding-bottom": 8, "padding-left": 12, "padding-right": 12,
                      "text-align": "center"})
    return style


def value_for(name, tokens, location):
    def invalid():
        raise location.error(f"Unsupported value for {name}: {tinycss2.serialize(tokens).strip()}")

    if len(tokens) != 1:
        invalid()
    token = tokens[0]
    text = tinycss2.serialize(tokens).strip().lower()
    enums = {
        "display": {"flex", "none"}, "box-sizing": {"border-box"},
        "flex-direction": {"row", "column", "row-reverse", "column-reverse"},
        "flex-wrap": {"nowrap", "wrap"},
        "justify-content": {"flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"},
        "align-items": {"flex-start", "center", "flex-end"},
        "align-content": {"flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"},
        "text-align": {"left", "center", "right"}, "white-space": {"normal", "nowrap", "pre"},
        "text-overflow": {"clip", "ellipsis"}, "overflow": {"hidden", "auto", "scroll"},
    }
    if name in enums:
        if text not in enums[name]:
            invalid()
        return text
    if name in {"color", "background-color", "border-color"}:
        parsed = parse_color(token)
        if parsed is None or parsed == "currentColor":
            invalid()
        return [round(parsed.red * 255) << 16 | round(parsed.green * 255) << 8 | round(parsed.blue * 255),
                round(parsed.alpha * 255)]
    if name == "opacity":
        if token.type not in {"number", "percentage"}:
            invalid()
        value = token.value / 100 if token.type == "percentage" else token.value
        if not 0 <= value <= 1:
            invalid()
        return round(value * 255)
    if name == "flex-grow":
        if token.type != "number" or not token.is_integer or not 0 <= token.value <= 255:
            invalid()
        return int(token.value)
    if name in {"width", "height"}:
        if text == "auto":
            return ["auto", 0]
        if token.type == "percentage" and token.is_integer and 0 <= token.value <= 100:
            return ["percent", int(token.value)]
    pixel = (token.type == "dimension" and token.lower_unit == "px" or
             token.type == "number" and token.value == 0)
    if not pixel or not token.is_integer or not 0 <= token.value <= 32767:
        invalid()
    value = int(token.value)
    if name == "font-size" and value not in CAPABILITIES["fonts"]:
        raise location.error(f"font-size requires a compiled font: {CAPABILITIES['fonts']}")
    return ["px", value] if name in {"width", "height"} else value
