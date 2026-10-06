from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
OUTLINE_PATH = ROOT / "book" / "outline.json"
CHAPTERS_DIR = ROOT / "book" / "chapters"
SYSTEM_PROMPT = (ROOT / "prompts" / "system.txt").read_text(encoding="utf-8")
CHAPTER_PROMPT = (ROOT / "prompts" / "chapter.txt").read_text(encoding="utf-8")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def load_outline() -> dict[str, Any]:
    return json.loads(OUTLINE_PATH.read_text(encoding="utf-8"))


def save_outline(outline: dict[str, Any]) -> None:
    OUTLINE_PATH.write_text(
        json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def clean_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
        if text.endswith("```"):
            text = text[:-3].rstrip()
    elif text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
    return text


def choose_chapter(outline: dict[str, Any]) -> dict[str, Any] | None:
    requested = os.getenv("CHAPTER_ID", "").strip()
    if requested:
        try:
            wanted = int(requested)
        except ValueError as exc:
            raise SystemExit("CHAPTER_ID must be an integer") from exc
        for ch in outline["chapters"]:
            if int(ch["id"]) == wanted:
                if ch.get("status") in {"pending", "failed", "revision_required"}:
                    return ch
                raise SystemExit(f"Chapter {wanted} is not writable; status={ch.get('status')}")
        raise SystemExit(f"Chapter {wanted} not found")

    for ch in outline["chapters"]:
        if ch.get("status") in {"pending", "failed", "revision_required"}:
            return ch
    return None


def previous_context(outline: dict[str, Any], current_id: int) -> str:
    chunks: list[str] = []
    for ch in outline["chapters"]:
        if int(ch["id"]) >= current_id:
            continue
        path = CHAPTERS_DIR / f"chapter_{int(ch['id']):03d}.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            # Keep the context bounded; the model does not need the full earlier book.
            chunks.append(text[:5000])
    return "\n\n--- فصل قبلی ---\n\n".join(chunks) or "هنوز فصل قبلی تولید نشده است."


def revision_context(chapter: dict[str, Any]) -> str:
    review_path = ROOT / "book" / "reviews" / f"review_{int(chapter['id']):03d}.json"
    if not review_path.exists():
        return "این فصل بازبینی قبلی ندارد."
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "بازبینی قبلی قابل خواندن نیست؛ فصل را از نظر دقت و ساختار دوباره بررسی کن."
    instructions = review.get("revision_instructions", [])
    issues = review.get("issues", [])
    parts = []
    if instructions:
        parts.append("دستورهای اصلاحی:\n" + "\n".join(f"- {x}" for x in instructions))
    if issues:
        parts.append("ایرادهای ثبت‌شده:\n" + "\n".join(f"- [{i.get('severity', 'medium')}] {i.get('description', '')}" for i in issues))
    return "\n".join(parts) or "اصلاح مشخصی ثبت نشده است؛ فصل را از نظر کیفیت عمومی بازبینی کن."


def generate(chapter: dict[str, Any], outline: dict[str, Any]) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    chapter_list = "\n".join(
        f"{int(ch['id'])}. {ch['title']} [{ch.get('status', 'pending')}]"
        for ch in outline["chapters"]
    )
    prompt = CHAPTER_PROMPT.format(
        book_title=outline["book_title"],
        chapter_title=chapter["title"],
        chapter_id=chapter["id"],
        chapter_list=chapter_list,
        previous_context=previous_context(outline, int(chapter["id"])),
    )
    if chapter.get("status") == "revision_required":
        prompt += "\n\nاصلاحات بازبینی قبلی:\n" + revision_context(chapter)

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]),
            types.Content(role="user", parts=[types.Part(text=prompt)]),
        ],
        config=types.GenerateContentConfig(
            temperature=0.65,
            max_output_tokens=12000,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response")
    return clean_text(response.text)


def main() -> None:
    outline = load_outline()
    chapter = choose_chapter(outline)
    if chapter is None:
        print("No writable chapter is pending. Nothing to do.")
        return

    chapter["status"] = "writing"
    chapter["attempts"] = int(chapter.get("attempts", 0)) + 1
    save_outline(outline)

    try:
        content = generate(chapter, outline)
        chapter_id = int(chapter["id"])
        out_path = CHAPTERS_DIR / f"chapter_{chapter_id:03d}.md"
        out_path.write_text(
            f"# {chapter['title']}\n\n{content}\n", encoding="utf-8"
        )
        chapter["status"] = "written"
        chapter["review"] = "pending"
        print(f"Generated {out_path}")
    except Exception as exc:
        chapter["status"] = "failed"
        chapter["last_error"] = str(exc)
        save_outline(outline)
        raise

    save_outline(outline)


if __name__ == "__main__":
    main()
