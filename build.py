#!/usr/bin/env python3
"""Build dist/index.html by inlining evidence.json into template.html.

No third-party dependencies. Usage:

    python3 build.py

Options:
    --data FILE      evidence file (default: evidence.json)
    --template FILE  template file (default: template.html)
    --out FILE       output file (default: dist/index.html)
    --strict         exit non-zero on warnings as well as errors

Validation rules below mirror the validate() function in template.html.
If you change one, change the other.
"""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

PLACEHOLDER = "__EVIDENCE_JSON__"
PYRAMIDS = ("stated", "revealed")
LAYERS = ("base", "middle", "top")
CLASSIFICATIONS = ("deliberate positioning", "misalignment", "unclear")

# ANSI colour, dropped when stdout is not a terminal.
_TTY = sys.stdout.isatty()


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def has(v) -> bool:
    return v is not None and str(v).strip() != ""


def as_list(v) -> list:
    return v if isinstance(v, list) else []


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def validate(data: dict) -> tuple[list, list]:
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []

    elements = as_list(data.get("elements"))
    gaps = as_list(data.get("gaps"))
    seen: dict[str, dict] = {}

    if not elements:
        errors.append(("elements", "No elements found in the data."))

    for i, el in enumerate(elements):
        el = el if isinstance(el, dict) else {}
        eid = el.get("id")
        where = f"elements[{i}]" + (f" {eid}" if has(eid) else "")

        if not has(eid):
            errors.append((where, "Element has no id."))
        elif eid in seen:
            errors.append((where, f'Duplicate element id "{eid}".'))
        else:
            seen[eid] = el

        if el.get("pyramid") not in PYRAMIDS:
            errors.append((where, f'pyramid must be "stated" or "revealed" (found {json.dumps(el.get("pyramid"))}).'))
        if el.get("layer") not in LAYERS:
            errors.append((where, f'layer must be "base", "middle" or "top" (found {json.dumps(el.get("layer"))}).'))
        if not has(el.get("claim")):
            errors.append((where, "claim is empty — nothing to show on the pyramid."))

        evidence = as_list(el.get("evidence"))
        if el.get("pyramid") == "revealed" and not evidence:
            errors.append((where, "Revealed element has no evidence entries."))
        if el.get("pyramid") == "stated" and not evidence:
            warnings.append((where, "Stated element has no evidence entries."))

        for j, ev in enumerate(evidence):
            ev = ev if isinstance(ev, dict) else {}
            ewhere = f"{where} evidence[{j}]"
            for field in ("document", "section", "page"):
                if not has(ev.get(field)):
                    errors.append((ewhere, f'Citation is missing "{field}".'))
            if not has(ev.get("excerpt")):
                warnings.append((ewhere, "Citation has no excerpt."))
            if not has(ev.get("accessed")):
                warnings.append((ewhere, "Citation has no accessed date."))

        if el.get("layer") == "middle":
            if el.get("rcType") not in ("resource", "capability"):
                errors.append((where, 'Middle-layer element needs rcType "resource" or "capability" '
                                      f'(found {json.dumps(el.get("rcType"))}).'))
        elif has(el.get("rcType")):
            warnings.append((where, f'{el.get("layer") or "this"}-layer element has rcType '
                                    f'"{el.get("rcType")}" — expected null.'))

    for i, gap in enumerate(gaps):
        gap = gap if isinstance(gap, dict) else {}
        gid = gap.get("id")
        where = f"gaps[{i}]" + (f" {gid}" if has(gid) else "")
        if not has(gid):
            warnings.append((where, "Gap has no id."))
        for key, side in (("statedIds", "stated"), ("revealedIds", "revealed")):
            ids = as_list(gap.get(key))
            if not ids:
                warnings.append((where, f"{key} is empty."))
            for ref in ids:
                target = seen.get(ref)
                if target is None:
                    errors.append((where, f'{key} references element id "{ref}", which does not exist.'))
                elif target.get("pyramid") != side:
                    warnings.append((where, f'{key} lists "{ref}", but that element is on the '
                                            f'{target.get("pyramid")} pyramid.'))
        if gap.get("classification") not in CLASSIFICATIONS:
            errors.append((where, 'classification must be "deliberate positioning", "misalignment" or '
                                  f'"unclear" (found {json.dumps(gap.get("classification"))}).'))
        if not has(gap.get("classificationReasoning")):
            warnings.append((where, "classification has no reasoning."))

    if len(gaps) < 2:
        warnings.append(("gaps", f"Only {len(gaps)} gap(s) defined — at least 2 expected."))

    for where, count, fields in placeholder_groups(data):
        warnings.append((where, f'{count} field(s) still start with "SAMPLE:" — placeholder data ({fields}).'))

    return errors, warnings


def placeholder_groups(data: dict) -> list[tuple[str, int, str]]:
    """Group every string starting with 'SAMPLE:' by the object that holds it."""
    hits: list[list[str]] = []

    def walk(value, path: list[str]) -> None:
        if isinstance(value, str):
            if value.startswith("SAMPLE:"):
                hits.append(path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path + [str(i)])
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(v, path + [k])

    walk(data, [])

    order: list[str] = []
    groups: dict[str, dict] = {}
    for path in hits:
        key, rest = path[0], path[1:]
        if len(path) > 1 and path[1].isdigit():
            key = f"{path[0]}[{path[1]}]"
            rest = path[2:]
            host = as_list(data.get(path[0]))[int(path[1])]
            if isinstance(host, dict) and has(host.get("id")):
                key += f" {host['id']}"
        if key not in groups:
            groups[key] = {"count": 0, "fields": []}
            order.append(key)
        groups[key]["count"] += 1
        if len(groups[key]["fields"]) < 4:
            groups[key]["fields"].append(".".join(rest) or "(value)")

    out = []
    for key in order:
        g = groups[key]
        fields = ", ".join(g["fields"]) + (", …" if g["count"] > len(g["fields"]) else "")
        out.append((key, g["count"], fields))
    return out


def report(errors: list, warnings: list) -> None:
    print()
    print(c("1", "Data checks"))
    for where, msg in errors:
        print(f'  {c("31", "ERROR")}   {where}: {msg}')
    for where, msg in warnings:
        print(f'  {c("33", "WARNING")} {where}: {msg}')
    if not errors and not warnings:
        print(f'  {c("32", "OK")}      all checks passed')
    else:
        print(f'  {len(errors)} error(s), {len(warnings)} warning(s)')


# --------------------------------------------------------------------------
# self-containment check on the built file
# --------------------------------------------------------------------------
class ExternalRefScanner(HTMLParser):
    """Flag script/link/img (and other loaders) that pull from the network."""

    WATCH = {
        "script": ("src",),
        "link": ("href",),
        "img": ("src", "srcset"),
        "iframe": ("src",),
        "source": ("src", "srcset"),
        "video": ("src", "poster"),
        "audio": ("src"),
        "embed": ("src",),
        "object": ("data",),
        "track": ("src",),
        "input": ("src",),
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[str] = []
        self.checked = 0
        self.tags = 0

    def handle_starttag(self, tag, attrs):
        watched = self.WATCH.get(tag)
        if not watched:
            return
        self.tags += 1
        for name, value in attrs:
            if name not in watched or not value:
                continue
            self.checked += 1
            v = value.strip()
            low = v.lower()
            external = low.startswith("//") or (
                ":" in low.split("/")[0] and not low.startswith(("data:", "blob:"))
            )
            if external:
                self.findings.append(f"<{tag} {name}=\"{v}\"> on line {self.getpos()[0]}")


def check_self_contained(html: str) -> tuple[bool, list[str], str]:
    scanner = ExternalRefScanner()
    scanner.feed(html)
    scanner.close()
    detail = (f"{scanner.tags} script/link/img-style tag(s) parsed, "
              f"{scanner.checked} URL attribute(s) found")
    return (not scanner.findings), scanner.findings, detail


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def inline(template: str, data_text: str) -> str:
    # Escape the three characters that could break out of a <script> block.
    safe = data_text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return template.replace(PLACEHOLDER, safe)


def main() -> int:
    ap = argparse.ArgumentParser(description="Inline evidence.json into template.html.")
    ap.add_argument("--data", default="evidence.json")
    ap.add_argument("--template", default="template.html")
    ap.add_argument("--out", default="dist/index.html")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    data_path = (root / args.data) if not Path(args.data).is_absolute() else Path(args.data)
    tpl_path = (root / args.template) if not Path(args.template).is_absolute() else Path(args.template)
    out_path = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)

    for p in (data_path, tpl_path):
        if not p.exists():
            print(c("31", f"Missing file: {p}"), file=sys.stderr)
            return 2

    raw = data_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(c("31", f"{data_path.name} is not valid JSON: {exc}"), file=sys.stderr)
        return 2

    template = tpl_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        print(c("31", f"{tpl_path.name} does not contain {PLACEHOLDER}."), file=sys.stderr)
        return 2

    errors, warnings = validate(data)

    # Re-serialise compactly so the built page carries exactly the parsed data.
    html = inline(template, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    report(errors, warnings)

    ok, findings, detail = check_self_contained(html)
    print()
    print(c("1", "Self-containment check"))
    if ok:
        print(f'  {c("32", "OK")}      no external script/link/img URLs ({detail})')
    else:
        for f in findings:
            print(f'  {c("31", "ERROR")}   external reference: {f}')

    size_kb = out_path.stat().st_size / 1024
    print()
    print(f'{c("1", "Built")} {out_path.relative_to(root) if out_path.is_relative_to(root) else out_path} '
          f'({size_kb:.1f} KB) — open it in a browser.')

    if errors or not ok:
        print(c("31", f"\nFinished with errors. {out_path.name} was still written so you can inspect it."))
        return 1
    if warnings and args.strict:
        print(c("33", "\nFinished with warnings (--strict)."))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
