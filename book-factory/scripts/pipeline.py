from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTLINE = ROOT / "book" / "outline.json"


def run(module: str, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print(f"\n=== RUN {module} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / module)], cwd=ROOT, env=merged, check=True)


def git_commit(message: str) -> bool:
    subprocess.run(["git", "config", "user.name", "AI Book Bot"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "book/"], cwd=ROOT, check=True)
    tex_path = ROOT / "output" / "book.tex"
    if tex_path.exists():
        subprocess.run(["git", "add", "output/book.tex"], cwd=ROOT, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    subprocess.run(["git", "push"], cwd=ROOT, check=True)
    return True


def load() -> dict[str, Any]:
    return json.loads(OUTLINE.read_text(encoding="utf-8"))


def writable(outline: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in outline["chapters"] if c.get("status") in {"pending", "failed", "revision_required"}]


def written_pending_review(outline: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in outline["chapters"] if c.get("status") == "written" and c.get("review") == "pending"]


def all_approved(outline: dict[str, Any]) -> bool:
    chapters = outline["chapters"]
    return bool(chapters) and all(c.get("status") == "approved" for c in chapters)


def main() -> None:
    max_chapters_raw = os.getenv("MAX_CHAPTERS", "0").strip()
    max_chapters = int(max_chapters_raw or "0")
    max_revisions = int(os.getenv("MAX_REVISIONS", "2"))
    processed = 0

    while True:
        outline = load()
        candidates = writable(outline)
        if not candidates:
            # A written chapter can exist if a previous run stopped between writer/reviewer.
            pending_reviews = written_pending_review(outline)
            if pending_reviews:
                chapter_id = int(pending_reviews[0]["id"])
                run("reviewer.py", {"CHAPTER_ID": str(chapter_id)})
                git_commit(f"book: review chapter {chapter_id:03d}")
                continue
            break

        if max_chapters and processed >= max_chapters:
            break

        chapter = candidates[0]
        chapter_id = int(chapter["id"])
        revisions = 0

        while True:
            try:
                run("ai_writer.py", {"CHAPTER_ID": str(chapter_id)})
            except subprocess.CalledProcessError:
                # ai_writer.py persists status=failed before raising. Preserve that state in Git.
                git_commit(f"book: generation failed for chapter {chapter_id:03d}")
                raise
            git_commit(f"book: generate chapter {chapter_id:03d}")

            try:
                run("reviewer.py", {"CHAPTER_ID": str(chapter_id)})
            except subprocess.CalledProcessError:
                git_commit(f"book: review failed for chapter {chapter_id:03d}")
                raise
            git_commit(f"book: review chapter {chapter_id:03d}")

            latest = load()
            state = next(c for c in latest["chapters"] if int(c["id"]) == chapter_id)
            if state.get("status") == "approved":
                break

            revisions += 1
            if revisions > max_revisions:
                raise SystemExit(
                    f"Chapter {chapter_id} exceeded MAX_REVISIONS={max_revisions}; leaving it as revision_required."
                )
            print(f"Chapter {chapter_id} needs revision; retry {revisions}/{max_revisions}.", flush=True)

        processed += 1

    # Rebuild the book from every approved chapter currently in the repository.
    if any(c.get("status") == "approved" for c in load()["chapters"]):
        run("build_book.py")
        git_commit("book: rebuild TeX source")

    final = load()
    print("\n=== PIPELINE COMPLETE ===")
    print(f"Processed this run: {processed}")
    print(f"All chapters approved: {all_approved(final)}")


if __name__ == "__main__":
    main()
