"""
Scans all PDFs in a folder and reports which ones extract text successfully.
Run before ingest to catch scanned/image-only PDFs early.

Usage (inside container):
    docker-compose exec api bash
    python scripts/check_pdfs.py --dir ./docs/
"""
import sys, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Root folder to scan")
    parser.add_argument("--min-words", type=int, default=50, help="Min words to consider OK")
    return parser.parse_args()


def main():
    args = parse_args()
    docs_dir = Path(args.dir)

    ok, empty, corrupt = [], [], []

    for pdf_path in sorted(docs_dir.glob("**/*.pdf")):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = " ".join(p.extract_text() or "" for p in pdf.pages[:3])
                word_count = len(text.split())

            if word_count < args.min_words:
                empty.append(pdf_path)
            else:
                ok.append((pdf_path, word_count))
        except Exception as e:
            corrupt.append((pdf_path, str(e)))

    # Report
    print(f"\n✓ Extractable ({len(ok)} files):")
    for p, wc in ok[:15]:
        print(f"   {p.relative_to(docs_dir)} — ~{wc} words")
    if len(ok) > 15:
        print(f"   ... and {len(ok) - 15} more")

    print(f"\n⚠  Empty / scanned ({len(empty)} files) — will produce no chunks:")
    for p in empty:
        print(f"   {p.relative_to(docs_dir)}")

    print(f"\n✗  Corrupt / unreadable ({len(corrupt)} files):")
    for p, e in corrupt:
        print(f"   {p.relative_to(docs_dir)}: {e}")

    print(f"\nSummary: {len(ok)} ok, {len(empty)} empty, {len(corrupt)} corrupt")

    if empty:
        print("\nFor scanned PDFs, options:")
        print("  1. Skip them (simplest)")
        print("  2. OCR with pytesseract: pip install pytesseract && lang='ell'")


if __name__ == "__main__":
    main()
