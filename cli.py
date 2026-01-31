from __future__ import annotations

import os
from pathlib import Path
import argparse

from Paper2Post.pdf_loader import load_pdf_text
from Paper2Post.section_parser import parse_sections
from Paper2Post.prompt import LLMClient, build_paper_context
from Paper2Post.generators.twitter import generate_twitter_thread
from Paper2Post.generators.xiaohongshu import generate_xiaohongshu
from Paper2Post.generators.linkedin import generate_linkedin_post


def _write_or_print(label: str, content: str, outdir: Path | None) -> None:
    if outdir is None:
        print(f"\n===== {label} =====\n")
        print(content.rstrip())
        return
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{label}.md"
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="papercaster", description="Generate posts from a paper PDF.")
    parser.add_argument("pdf", help="Path to paper PDF")
    parser.add_argument("--all", action="store_true", help="Generate all formats")
    parser.add_argument("--twitter", action="store_true", help="Generate Twitter/X thread")
    parser.add_argument("--xiaohongshu", action="store_true", help="Generate Xiaohongshu-style summary")
    parser.add_argument("--linkedin", action="store_true", help="Generate LinkedIn technical post")
    parser.add_argument("--outdir", default=None, help="Output directory (writes separate markdown files)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max PDF pages to parse (optional)")
    args = parser.parse_args(argv)

    want_twitter = args.all or args.twitter
    want_xhs = args.all or args.xiaohongshu
    want_linkedin = args.all or args.linkedin
    if not (want_twitter or want_xhs or want_linkedin):
        parser.error("Choose at least one: --all / --twitter / --xiaohongshu / --linkedin")

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY environment variable.")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()

    outdir = Path(args.outdir).resolve() if args.outdir else None

    doc = load_pdf_text(args.pdf, max_pages=args.max_pages)
    parsed = parse_sections(doc.text)
    paper_context = build_paper_context(
        title=parsed.title,
        sections=parsed.sections,
        raw_text=doc.text,
    )

    llm = LLMClient(api_key=api_key, base_url=base_url, model=model)

    if want_twitter:
        content = generate_twitter_thread(llm, paper_context)
        _write_or_print("twitter_thread", content, outdir)

    if want_xhs:
        content = generate_xiaohongshu(llm, paper_context)
        _write_or_print("xiaohongshu", content, outdir)

    if want_linkedin:
        content = generate_linkedin_post(llm, paper_context)
        _write_or_print("linkedin", content, outdir)


if __name__ == "__main__":
    main()

