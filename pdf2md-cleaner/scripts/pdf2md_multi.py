#!/usr/bin/env python3
"""
PDF to Markdown Converter for Embedded/MCU Manuals
Supports multiple backends: MinerU, Marker, Docling, PyMuPDF4LLM
Optimized for register tables, removing headers/footers/company names.

Usage:
    python pdf2md_multi.py <input.pdf> [--backend all|mineru|marker|docling|pymupdf4llm] [--output-dir ./output]
    python pdf2md_multi.py input.pdf -b pymupdf4llm -o ./out --clean
    python pdf2md_multi.py input.pdf -b all -o ./out --clean --evaluate --api-key KEY
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ─── Backend Definitions ───────────────────────────────────────────────

BACKENDS = {
    "pymupdf4llm": {
        "package": "pymupdf4llm",
        "pip_install": "pip install pymupdf4llm",
        "description": "PyMuPDF4LLM - lightweight, no GPU, fast, good tables",
        "stars": "high",
    },
    "docling": {
        "package": "docling",
        "pip_install": "pip install docling",
        "description": "IBM Docling - excellent layout understanding, TableFormer",
        "stars": "29k+",
    },
    "marker": {
        "package": "marker_pdf",
        "pip_install": "pip install marker-pdf",
        "description": "VikParuchuri Marker - fast, high accuracy, multi-format",
        "stars": "21k+",
    },
    "mineru": {
        "package": "magic_pdf",
        "pip_install": 'pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com',
        "description": "OpenDataLab MinerU - best for complex layouts & tables",
        "stars": "30k+",
    },
}


def check_package(package_name: str) -> bool:
    """Check if a Python package is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {package_name.replace('-', '_')}"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


# ─── Backend Converters ────────────────────────────────────────────────

def convert_with_pymupdf4llm(pdf_path: str, output_dir: str) -> Optional[str]:
    """Convert PDF using PyMuPDF4LLM - lightweight, no GPU needed."""
    try:
        import pymupdf4llm

        md_text = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=False,
            table_formats=["markdown"],
            extract_images=False,
        )
        stem = Path(pdf_path).stem
        md_path = os.path.join(output_dir, f"{stem}_pymupdf4llm.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        return md_path
    except ImportError:
        print("[PyMuPDF4LLM] Not installed. Run: pip install pymupdf4llm")
        return None
    except Exception as e:
        print(f"[PyMuPDF4LLM] Error: {e}")
        return None


def convert_with_docling(pdf_path: str, output_dir: str) -> Optional[str]:
    """Convert PDF using IBM Docling - excellent table extraction via TableFormer."""
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(pdf_path)

        stem = Path(pdf_path).stem
        md_path = os.path.join(output_dir, f"{stem}_docling.md")
        result.document.save_as_markdown(md_path)
        return md_path
    except ImportError:
        print("[Docling] Not installed. Run: pip install docling")
        return None
    except Exception as e:
        print(f"[Docling] Error: {e}")
        return None


def convert_with_marker(pdf_path: str, output_dir: str) -> Optional[str]:
    """Convert PDF using Marker - high accuracy, GPU recommended."""
    try:
        # Try CLI first (marker-pdf provides `marker` command)
        cmd = [
            sys.executable, "-m", "marker_pdf",
            pdf_path,
            "--output_dir", output_dir,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            # Fallback: try Python API
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict

                converter = PdfConverter(artifact_dict=create_model_dict())
                rendered = converter(pdf_path)
                md_text = rendered.markdown
                stem = Path(pdf_path).stem
                md_path = os.path.join(output_dir, f"{stem}_marker.md")
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_text)
                return md_path
            except Exception as e2:
                print(f"[Marker] Both CLI and API failed: {e2}")
                return None

        # Find generated markdown
        md_files = list(Path(output_dir).rglob("*.md"))
        if md_files:
            return str(md_files[0])
        return None
    except ImportError:
        print("[Marker] Not installed. Run: pip install marker-pdf")
        return None
    except subprocess.TimeoutExpired:
        print("[Marker] Timeout (900s). PDF too large or GPU unavailable.")
        return None
    except Exception as e:
        print(f"[Marker] Error: {e}")
        return None


def convert_with_mineru(pdf_path: str, output_dir: str) -> Optional[str]:
    """Convert PDF using MinerU - most powerful, needs model weights."""
    try:
        # Try CLI: magic-pdf
        cmd = [
            "magic-pdf",
            "-p", pdf_path,
            "-o", output_dir,
            "-m", "auto",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            print(f"[MinerU] CLI error: {result.stderr[:300]}")
            return None

        # Find generated markdown
        md_files = list(Path(output_dir).rglob("*.md"))
        if md_files:
            return str(md_files[0])
        return None
    except FileNotFoundError:
        print("[MinerU] CLI not found. Run: pip install -U \"magic-pdf[full]\"")
        return None
    except subprocess.TimeoutExpired:
        print("[MinerU] Timeout (900s).")
        return None
    except Exception as e:
        print(f"[MinerU] Error: {e}")
        return None


BACKEND_FUNCS = {
    "pymupdf4llm": convert_with_pymupdf4llm,
    "docling": convert_with_docling,
    "marker": convert_with_marker,
    "mineru": convert_with_mineru,
}


# ─── Post-Processing: Clean & Optimize for Embedded Manuals ────────────

# Known MCU/SoC vendor names
VENDOR_NAMES = [
    "STMicroelectronics", "NXP", "Texas Instruments", "Microchip",
    "Renesas", "Nordic Semiconductor", "Atmel", "Cypress",
    "Infineon", "ON Semiconductor", "Analog Devices", "Silicon Labs",
    "Espressif", "GigaDevice", "HDSC", "MindMotion", "Megawin",
    "Holtek", "WCH", "SinoWealth", "Fortior", "Jingxin",
    "Allwinner", "Rockchip", "MediaTek", "Realtek", "Broadcom",
    "Qualcomm", "Maxim", "Freescale", "Intel", "AMD", "Zilog",
    "Microsemi", "VOFA+",
]

HEADER_FOOTER_PATTERNS = [
    # Page numbers
    r"(?m)^\s*\d{1,4}\s*/\s*\d{1,4}\s*$",
    r"(?m)^\s*-\s*\d{1,4}\s*-\s*$",
    r"(?m)^\s*Page\s+\d+\s*(of\s+\d+)?\s*$",
    r"(?m)^\s*\d{1,4}\s*$",  # standalone page number
    # Revision stamps
    r"(?m)^\s*Rev\.?\s*[\d.]+\s*$",
    # Copyright
    r"(?m)^©\s*\d{4}.*$",
    r"(?m)^Copyright\s+©.*$",
    # Confidential notices (standalone)
    r"(?m)^(Proprietary|Confidential|Preliminary)\s*$",
    # Doc IDs
    r"(?m)^(Doc\.\s*ID|PM\d+|AN\d+|TN\d+|UM\d+|RM\d+|DS\d+)\s*\d*\s*$",
    # Manual titles (standalone repeated)
    r"(?m)^(Reference Manual|Datasheet|User Manual|Programming Manual|Technical Reference Manual)\s*$",
    # Vendor URLs
    r"(?m)^https?://(www\.)?(st\.com|nxp\.com|ti\.com|microchip\.com|renesas\.com|espressif\.com|sllabs\.com)\b.*$",
    # Empty cross-references
    r"(?m)^(Figure|Table)\s+\d+[\s.]*$",
]

REGISTER_CLEANUP_PATTERNS = [
    # Empty table rows
    (r"(?m)^\|(\s*\|)+\s*$", ""),
    # Collapse 3+ blank lines
    (r"\n{3,}", "\n\n"),
    # Trailing whitespace
    (r"(?m)[ \t]+$", ""),
    # Leading whitespace before table rows
    (r"(?m)^\s+\|", "|"),
]


def clean_markdown(content: str, aggressive: bool = True) -> str:
    """
    Post-process markdown to remove redundant headers/footers and clean up
    formatting, optimized for embedded/MCU datasheets and programming manuals.
    """
    original_len = len(content)

    # 1. Remove vendor name lines (standalone)
    for vendor in VENDOR_NAMES:
        content = re.sub(rf"(?m)^{re.escape(vendor)}\s*$", "", content)

    # 2. Remove header/footer patterns
    for pattern in HEADER_FOOTER_PATTERNS:
        content = re.sub(pattern, "", content)

    # 3. Register-specific cleanup
    for pattern, replacement in REGISTER_CLEANUP_PATTERNS:
        content = re.sub(pattern, replacement, content)

    # 4. Aggressive cleanup
    if aggressive:
        # Remove TOC sections
        content = re.sub(
            r"(?m)^#{1,3}\s*(Contents|Table of Contents|目录)\s*\n.*?(?=\n#{1,3}|\Z)",
            "", content, flags=re.DOTALL
        )
        # Remove revision history
        content = re.sub(
            r"(?m)^#{1,3}\s*(Revision History|修改历史|版本历史)\s*\n.*?(?=\n#{1,3}|\Z)",
            "", content, flags=re.DOTALL
        )

    # 5. Fix broken tables: insert missing separators
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|"):
            # Check if previous line was a table header (has |) and current is NOT a separator
            if (len(fixed_lines) > 0 and "|" in fixed_lines[-1]
                    and "---" not in fixed_lines[-1]
                    and not re.match(r"^\|[\s\-:]+(\|[\s\-:]+)*\|?\s*$", stripped)
                    and not re.match(r"^\|[\s\-:]+(\|[\s\-:]+)*\|?\s*$", fixed_lines[-1])):
                # Insert separator based on column count
                col_count = fixed_lines[-1].count("|") - 1
                if col_count > 0:
                    sep = "|" + "|".join(["---"] * col_count) + "|"
                    fixed_lines.append(sep)
        fixed_lines.append(line)
    content = "\n".join(fixed_lines)

    # 6. Remove empty lines within tables
    lines = content.split("\n")
    result = []
    in_table = False
    for line in lines:
        if line.strip().startswith("|"):
            in_table = True
            result.append(line)
        elif line.strip() == "" and in_table:
            continue  # skip empty lines in tables
        else:
            in_table = False
            result.append(line)
    content = "\n".join(result)

    # 7. Remove duplicate consecutive lines
    lines = content.split("\n")
    deduped = []
    for i, line in enumerate(lines):
        if i > 0 and line.strip() == lines[i-1].strip() and line.strip() != "":
            continue
        deduped.append(line)
    content = "\n".join(deduped)

    removed_pct = round((1 - len(content) / max(original_len, 1)) * 100, 1)
    print(f"  [Clean] Removed {removed_pct}% redundant content ({original_len} → {len(content)} chars)")

    return content.strip() + "\n"


# ─── LLM Evaluation ────────────────────────────────────────────────────

def evaluate_with_llm(md_files: dict, api_key: str, model: str = "deepseek-ai/deepseek-v4-flash") -> dict:
    """
    Use LLM to evaluate multiple markdown outputs and select the best one.
    Returns dict with evaluation results and best backend name.
    """
    import urllib.request

    print("\n" + "="*60)
    print("  LLM Evaluation: Comparing markdown outputs")
    print("="*60)

    # Read all markdown files (sample first 4000 chars)
    samples = {}
    for backend, path in md_files.items():
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            samples[backend] = content[:4000]

    if not samples:
        print("[ERROR] No markdown files to evaluate")
        return {"best": None, "scores": {}}

    prompt = """You are evaluating PDF-to-Markdown conversion results for embedded/MCU programming manuals.
Compare the following markdown outputs from different tools and score each on:
1. Table quality (0-10): Are register tables intact with proper formatting?
2. Structure preservation (0-10): Are headings, sections, and hierarchy preserved?
3. Cleanliness (0-10): Are headers/footers/company names/page numbers removed?
4. Register data integrity (0-10): Are hex addresses, bit fields, reset values preserved?
5. Readability (0-10): Is the overall markdown readable and well-formatted?

Total score: 0-50. Respond in JSON format:
```json
{
  "scores": {
    "backend_name": {"table": N, "structure": N, "cleanliness": N, "register_data": N, "readability": N, "total": N}
  },
  "best": "backend_name",
  "reason": "brief explanation"
}
```

"""
    for backend, sample in samples.items():
        prompt += f"\n--- {backend} ---\n{sample}\n"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a technical document quality evaluator specializing in embedded systems documentation. Respond only in valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 3000,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            response_text = result["choices"][0]["message"]["content"]

            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                eval_result = json.loads(json_match.group(1))
            else:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                eval_result = json.loads(response_text[json_start:json_end])

            print(f"\n  Evaluation Results:")
            for backend, scores in eval_result.get("scores", {}).items():
                print(f"    {backend}: {scores.get('total', 0)}/50")
            print(f"\n  BEST: {eval_result.get('best', 'N/A')}")
            print(f"  Reason: {eval_result.get('reason', 'N/A')}")

            return eval_result

    except Exception as e:
        print(f"[ERROR] LLM evaluation failed: {e}")
        # Fallback: prefer docling for quality, pymupdf4llm for speed
        fallback_order = ["docling", "pymupdf4llm", "marker", "mineru"]
        for b in fallback_order:
            if b in samples:
                return {"best": b, "scores": {}, "reason": f"Fallback (LLM failed): {b}"}
        return {"best": None, "scores": {}, "reason": "All backends failed"}


# ─── Main Pipeline ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PDF to Markdown converter optimized for embedded/MCU manuals"
    )
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument(
        "--backend", "-b",
        choices=["all", "pymupdf4llm", "docling", "marker", "mineru"],
        default="pymupdf4llm",
        help="Conversion backend (default: pymupdf4llm)"
    )
    parser.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    parser.add_argument("--clean", "-c", action="store_true", default=True, help="Post-process cleanup")
    parser.add_argument("--no-clean", dest="clean", action="store_false")
    parser.add_argument("--evaluate", "-e", action="store_true", help="Use LLM to evaluate")
    parser.add_argument("--api-key", default=os.environ.get("NVIDIA_API_KEY", ""), help="NVIDIA API key")
    parser.add_argument("--model", default="deepseek-ai/deepseek-v4-flash", help="LLM model for evaluation")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] File not found: {args.input}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    pdf_stem = Path(args.input).stem

    if args.backend == "all":
        backends_to_run = list(BACKENDS.keys())
    else:
        backends_to_run = [args.backend]

    print(f"  Input:    {args.input}")
    print(f"  Output:   {args.output_dir}")
    print(f"  Backends: {', '.join(backends_to_run)}")
    print(f"  Clean:    {args.clean}")
    print(f"  Evaluate: {args.evaluate}")
    print("="*60)

    # Run conversions
    results = {}
    for backend in backends_to_run:
        print(f"\n  [{backend}] Converting...")
        start_time = time.time()

        backend_output = os.path.join(args.output_dir, backend)
        os.makedirs(backend_output, exist_ok=True)

        func = BACKEND_FUNCS[backend]
        md_path = func(args.input, backend_output)

        elapsed = time.time() - start_time
        if md_path:
            print(f"  [{backend}] Done in {elapsed:.1f}s")

            if args.clean:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                cleaned = clean_markdown(content)
                cleaned_path = os.path.join(backend_output, f"{pdf_stem}_{backend}_cleaned.md")
                with open(cleaned_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                results[backend] = cleaned_path
            else:
                results[backend] = md_path
        else:
            results[backend] = None

    # Summary
    print("\n" + "="*60)
    print("  Conversion Summary:")
    for backend, path in results.items():
        status = f"OK -> {path}" if path else "FAILED"
        print(f"    {backend}: {status}")

    # LLM Evaluation
    if args.evaluate and args.api_key:
        valid_files = {k: v for k, v in results.items() if v}
        if valid_files:
            eval_result = evaluate_with_llm(valid_files, args.api_key, args.model)
            best_backend = eval_result.get("best")
            if best_backend and best_backend in valid_files:
                final_path = os.path.join(args.output_dir, f"{pdf_stem}_final.md")
                with open(valid_files[best_backend], "r", encoding="utf-8") as f:
                    final_content = f.read()
                with open(final_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                print(f"\n  BEST backend: {best_backend}")
                print(f"  Final output: {final_path}")

                report_path = os.path.join(args.output_dir, "evaluation_report.json")
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(eval_result, f, indent=2, ensure_ascii=False)
                print(f"  Evaluation report: {report_path}")
        else:
            print("  [WARN] No valid files to evaluate")
    elif args.evaluate and not args.api_key:
        print("  [WARN] Evaluation requested but no API key (use --api-key or NVIDIA_API_KEY env)")

    return results


if __name__ == "__main__":
    main()
