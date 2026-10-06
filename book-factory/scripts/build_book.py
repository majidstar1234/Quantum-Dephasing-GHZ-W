from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTLINE = ROOT / "book" / "outline.json"
CHAPTERS = ROOT / "book" / "chapters"
TEMPLATE = ROOT / "templates" / "book.tex"
OUTPUT = ROOT / "output" / "book.tex"


def tex_escape(s: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def inline(s: str) -> str:
    # Preserve simple Markdown emphasis/code while escaping normal LaTeX chars.
    tokens = []
    def stash(m):
        tokens.append(m.group(2))
        return f"@@TOKEN{len(tokens)-1}@@"
    s = re.sub(r"(`)(.*?)(`)", lambda m: stash(type("M", (), {"group": lambda self, n: m.group(2)})()), s)
    s = tex_escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\textbf{\1}", s)
    s = re.sub(r"\*(.+?)\*", r"\textit{\1}", s)
    for i, token in enumerate(tokens):
        s = s.replace(f"@@TOKEN{i}@@", r"\texttt{" + tex_escape(token) + "}")
    return s


def markdown_to_tex(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_itemize = False
    in_enumerate = False
    paragraph: list[str] = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            out.append(inline(" ".join(x.strip() for x in paragraph)))
            out.append("")
            paragraph = []

    def close_lists():
        nonlocal in_itemize, in_enumerate
        if in_itemize:
            out.append(r"\end{itemize}")
            in_itemize = False
        if in_enumerate:
            out.append(r"\end{enumerate}")
            in_enumerate = False

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            continue
        if line.startswith("# "):
            flush_paragraph(); close_lists(); out.append(r"\chapter{" + inline(line[2:]) + "}"); out.append("")
        elif line.startswith("## "):
            flush_paragraph(); close_lists(); out.append(r"\section{" + inline(line[3:]) + "}"); out.append("")
        elif line.startswith("### "):
            flush_paragraph(); close_lists(); out.append(r"\subsection{" + inline(line[4:]) + "}"); out.append("")
        elif re.match(r"^- \s*", line):
            flush_paragraph()
            if not in_itemize:
                close_lists(); out.append(r"\begin{itemize}"); in_itemize = True
            out.append(r"\item " + inline(re.sub(r"^-\s*", "", line)))
        elif re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            if not in_enumerate:
                close_lists(); out.append(r"\begin{enumerate}"); in_enumerate = True
            out.append(r"\item " + inline(re.sub(r"^\d+\.\s+", "", line)))
        elif line.startswith(">"):
            flush_paragraph(); close_lists(); out.append(r"\begin{quote}" + inline(line[1:].strip()) + r"\end{quote}"); out.append("")
        else:
            paragraph.append(line)
    flush_paragraph(); close_lists()
    return "\n".join(out)


def main() -> None:
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))
    chapters: list[str] = []
    for ch in outline["chapters"]:
        if ch.get("status") != "approved":
            continue
        path = CHAPTERS / f"chapter_{int(ch['id']):03d}.md"
        if path.exists():
            chapters.append(markdown_to_tex(path.read_text(encoding="utf-8")))

    if not chapters:
        raise SystemExit("No approved chapters are available for PDF build.")

    template = TEMPLATE.read_text(encoding="utf-8")
    tex = template.replace("%%BOOK_TITLE%%", tex_escape(outline["book_title"]))
    tex = tex.replace("%%BOOK_SUBTITLE%%", tex_escape(outline.get("book_subtitle", "")))
    tex = tex.replace("%%CHAPTERS%%", "\n\n".join(chapters))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(tex, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
