#!/usr/bin/env python3
"""
Batch processor: convert all PDFs in a directory to cleaned Markdown.
Optimized for embedded/MCU programming manuals.

Usage:
    python batch_convert.py <input_dir> [--output-dir ./output] [--backend all|docling|pymupdf4llm]
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from pdf2md_multi import (
    BACKEND_FUNCS, BACKENDS, clean_markdown,
    evaluate_with_llm
)
from md_cleaner import clean_markdown as deep_clean


def batch_convert(input_dir: str, output_dir: str, backends: list, deep_clean_flag: bool = True):
    """Convert all PDFs in directory."""
    pdf_files = sorted(Path(input_dir).glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {input_dir}")
        return

    print(f"📚 Found {len(pdf_files)} PDF files")
    print(f"🔧 Backends: {', '.join(backends)}")
    print(f"🧹 Deep clean: {deep_clean_flag}")
    print("="*60)

    all_results = {}

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        pdf_output = os.path.join(output_dir, pdf_path.stem)
        os.makedirs(pdf_output, exist_ok=True)

        pdf_results = {}
        for backend in backends:
            print(f"  ▶ [{backend}] Converting...")
            start = time.time()
            backend_dir = os.path.join(pdf_output, backend)
            os.makedirs(backend_dir, exist_ok=True)

            func = BACKEND_FUNCS[backend]
            md_path = func(str(pdf_path), backend_dir)
            elapsed = time.time() - start

            if md_path:
                print(f"  ✅ [{backend}] {elapsed:.1f}s")

                if deep_clean_flag:
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    cleaned, stats = deep_clean(content, aggressive=True, report=False)
                    cleaned_path = os.path.join(backend_dir, f"{pdf_path.stem}_{backend}_cleaned.md")
                    with open(cleaned_path, "w", encoding="utf-8") as f:
                        f.write(cleaned)
                    print(f"  🧹 Cleaned: {stats['reduction_pct']}% reduction")
                    pdf_results[backend] = cleaned_path
                else:
                    pdf_results[backend] = md_path
            else:
                print(f"  ❌ [{backend}] Failed")
                pdf_results[backend] = None

        all_results[pdf_path.name] = pdf_results

    # Summary
    print("\n" + "="*60)
    print("📋 BATCH SUMMARY")
    print("="*60)
    for pdf_name, results in all_results.items():
        print(f"\n  {pdf_name}:")
        for backend, path in results.items():
            status = "✅" if path else "❌"
            print(f"    {status} {backend}: {path or 'Failed'}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Batch PDF to Markdown converter")
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    parser.add_argument("--backend", "-b", default="pymupdf4llm",
                        choices=["all", "mineru", "marker", "docling", "pymupdf4llm"])
    parser.add_argument("--deep-clean", "-d", action="store_true", default=True)
    args = parser.parse_args()

    if args.backend == "all":
        backends = list(BACKENDS.keys())
    else:
        backends = [args.backend]

    batch_convert(args.input_dir, args.output_dir, backends, args.deep_clean)


if __name__ == "__main__":
    main()
