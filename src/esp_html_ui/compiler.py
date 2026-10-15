import re
from pathlib import Path

import cssselect2
import html5lib

from .css import CAPABILITIES, Stylesheet
from .model import CompileError, Document, Location, Node

GLOBAL_ATTRIBUTES = {"id", "class", "style", "hidden", "tabindex"}
CPP_KEYWORDS = set("alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t char16_t char32_t class compl concept const consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t while xor xor_eq".split())


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise CompileError(f"{path}: {error}") from error


def validate_attributes(element, allowed, location):
    for attribute in element.attrib:
        if attribute not in allowed:
            raise location.error(f"Unsupported attribute on <{element.tag}>: {attribute}")


def compile_document(path: Path, name="counter", width=320, height=170) -> Document:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in CPP_KEYWORDS or "__" in name or name.startswith("lv_"):
        raise CompileError("Name must be a lowercase C++ identifier, not a keyword or an lv_ name")
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise CompileError("Width and height must be between 1 and 4096")
    path = path.resolve()
    parser = html5lib.HTMLParser(namespaceHTMLElements=False)
    root = parser.parse(read_text(path))
    missing_doctype = {"expected-doctype-but-got-start-tag", "expected-doctype-but-got-chars", "expected-doctype-but-got-eof"}
    for (line, column), code, details in parser.errors:
        if code not in missing_doctype:
            raise Location(path, line, column).error(f"Invalid HTML: {code} {details}")

    document = Document(name, width, height, sources=[path])
    sheet = Stylesheet()
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue  # Comments have no rendering semantics.
        if element.tag not in CAPABILITIES["tags"]:
            raise Location(path, context=element.tag).error(f"Unsupported HTML tag in 0.1: {element.tag}")
        location = Location(path, context=element.tag)
        if element.tag == "html":
            validate_attributes(element, {"lang"}, location)
        elif element.tag in {"head", "title"}:
            validate_attributes(element, set(), location)
        elif element.tag == "meta":
            validate_attributes(element, {"charset"}, location)
            if element.get("charset", "").lower() not in {"utf-8", "utf8"}:
                raise location.error("Only meta charset=UTF-8 is supported")
        elif element.tag == "link":
            validate_attributes(element, {"rel", "href", "type"}, location)
            if element.get("rel", "").lower() != "stylesheet" or not element.get("href"):
                raise location.error("link requires rel=stylesheet and a local href")
            if element.get("type", "text/css").lower() != "text/css":
                raise location.error("Stylesheet type must be text/css")
            href = element.get("href")
            if ":" in href or href.startswith("//") or "?" in href or "#" in href:
                raise location.error("Stylesheets must be local files without query or fragment")
            css_path = (path.parent / href).resolve()
            sheet.add(read_text(css_path), Location(css_path))
            document.sources.append(css_path)
        elif element.tag == "style":
            validate_attributes(element, {"type"}, location)
            if element.get("type", "text/css").lower() != "text/css":
                raise location.error("Style type must be text/css")
            sheet.add(element.text or "", Location(path, context="style; positions within CSS block"))

    wrapper = cssselect2.ElementWrapper.from_html_root(root)
    styles, variables, wrappers = {}, {}, {}
    for wrapped in wrapper.iter_subtree():
        parent = wrapped.parent.etree_element if wrapped.parent else None
        element = wrapped.etree_element
        loc = Location(path, context=f"{element.tag}#{element.get('id', '')}; inline positions within attribute")
        style, custom = sheet.compute(wrapped, styles.get(parent), variables.get(parent, {}), loc)
        styles[element], variables[element], wrappers[element] = style, custom, wrapped

    body = root.find("body")
    if body is None:
        raise CompileError(f"{path}: Document has no body")
    ids = set()

    def visit(element, parent):
        if not isinstance(element.tag, str):
            return
        tag = element.tag
        kind = CAPABILITIES["tags"][tag]
        if kind in {"stylesheet", "metadata", "document"}:
            # Styles may appear in body, but do not produce LVGL objects.
            if element.tail and element.tail.strip():
                raise Location(path, context=tag).error("Put container text inside a text element")
            return
        loc = Location(path, context=f"{tag}#{element.get('id', '')}")
        allowed = GLOBAL_ATTRIBUTES | ({"disabled", "type"} if kind == "button" else set())
        validate_attributes(element, allowed, loc)
        element_id = element.get("id", "")
        if "id" in element.attrib and (not element_id or any(c.isspace() for c in element_id)):
            raise loc.error("IDs must be nonempty and contain no whitespace")
        if element_id in ids:
            raise loc.error(f"Duplicate id: {element_id}")
        if element_id:
            ids.add(element_id)
        tabindex = element.get("tabindex")
        if tabindex not in {None, "0", "-1"}:
            raise loc.error("Only tabindex=0 or -1 is implemented")
        if kind == "button" and element.get("type", "button").lower() != "button":
            raise loc.error("Form submit/reset buttons are planned; use type=button in 0.1")

        children = [child for child in element if isinstance(child.tag, str)]
        style = styles[element]
        if kind == "container":
            if element.text and element.text.strip() or any(child.tail and child.tail.strip() for child in element):
                raise loc.error("Put container text inside span, p, a heading, or button")
            text = ""
        else:
            if children:
                raise loc.error("Nested/rich text is planned; text elements currently contain text only")
            text = (element.text or "") + "".join(child.tail or "" for child in element)
            if style["white-space"] != "pre":
                text = re.sub(r"[\t\n\r\f ]+", " ", text).strip()
            if any(not (32 <= ord(c) < 127 or c in "\n\t") for c in text):
                raise loc.error("Text needs an additional font; 0.1 currently compiles printable ASCII only")
        if len(document.nodes) >= 128:
            raise loc.error("0.1 supports at most 128 rendered elements per screen")
        index = len(document.nodes)
        document.nodes.append(Node(tag, kind, element_id, parent, text, style,
                                   "hidden" in element.attrib, "disabled" in element.attrib,
                                   kind == "button" and tabindex != "-1" or tabindex == "0"))
        for child in children:
            visit(child, index)

    visit(body, None)
    return document
