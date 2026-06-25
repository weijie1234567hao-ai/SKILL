#!/usr/bin/env python3
"""
Post-processor for Markdown files converted from PDFs.
Specifically optimized for embedded/MCU register manuals.

Standalone usage:
    python md_cleaner.py input.md [-o output.md] [--aggressive] [--report]
"""

import argparse
import os
import re
import sys
from pathlib import Path
from collections import Counter

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ─── Header/Footer Detection (Adaptive) ───────────────────────────────

def detect_repeated_lines(content: str, min_repeats: int = 3) -> set:
    """
    Detect lines that repeat across the document (likely headers/footers).
    These are lines appearing >= min_repeats times.
    """
    lines = content.split("\n")
    line_counts = Counter()
    for line in lines:
        stripped = line.strip()
        # Only consider short lines (typical of headers/footers)
        if 1 < len(stripped) < 100:
            line_counts[stripped] += 1

    repeated = {line for line, count in line_counts.items() if count >= min_repeats}
    return repeated


def detect_page_patterns(content: str) -> list:
    """Detect page-number-like patterns."""
    patterns = [
        r"(?m)^\s*\d{1,4}\s*/\s*\d{1,4}\s*$",
        r"(?m)^\s*-\s*\d{1,4}\s*-\s*$",
        r"(?m)^\s*Page\s+\d+.*$",
        r"(?m)^\s*\d{1,4}\s*$",  # standalone number = page number
    ]
    return patterns


# ─── Embedded Manual Specific Patterns ─────────────────────────────────

# Known MCU/SoC vendor names that appear as page headers
VENDOR_NAMES = {
    "STMicroelectronics", "STM", "NXP", "Texas Instruments", "TI",
    "Microchip", "Renesas", "Nordic Semiconductor", "Atmel",
    "Cypress", "Infineon", "ON Semiconductor", "Analog Devices",
    "Silicon Labs", "Espressif", "GigaDevice", "HDSC", "MindMotion",
    "Megawin", "Holtek", "WCH", "SinoWealth", "Fortior", "Jingxin",
    "VOFA+", "Allwinner", "Rockchip", "MediaTek", "Realtek",
    "Broadcom", "Qualcomm", "Maxim", " Linear Technology",
    "ST", "Freescale", "Intel", "AMD", "Zilog", "Microsemi",
}

# Manual title patterns
MANUAL_TITLE_PATTERNS = [
    r"(?m)^(Reference Manual|Datasheet|User Manual|Programming Manual|"
    r"Technical Reference Manual|TRM|Data Brief|Application Note)\s*$",
    r"(?m)^(RM\d+|DS\d+|PM\d+|AN\d+|TN\d+|UM\d+|SPS\d+)\s*$",
]


def build_cleanup_patterns(repeated_lines: set, aggressive: bool = True) -> list:
    """Build regex patterns for cleanup based on detected repeated lines."""
    patterns = []

    # Add detected repeated lines (escape regex special chars)
    for line in repeated_lines:
        escaped = re.escape(line)
        patterns.append((f"Detected repeated: {line[:40]}...", rf"(?m)^{escaped}\s*$"))

    # Standard patterns
    standard = [
        ("Page numbers", r"(?m)^\s*\d{1,4}\s*/\s*\d{1,4}\s*$"),
        ("Page numbers (dash)", r"(?m)^\s*-\s*\d{1,4}\s*-\s*$"),
        ("Page labels", r"(?m)^\s*Page\s+\d+\s*(of\s+\d+)?\s*$"),
        ("Revision stamps", r"(?m)^\s*Rev\.?\s*[\d.]+\s*$"),
        ("Copyright", r"(?m)^©\s*\d{4}.*$"),
        ("Copyright (text)", r"(?m)^Copyright\s+©.*$"),
        ("Confidential notices", r"(?m)^(Proprietary|Confidential|Preliminary)\s*$"),
        ("Vendor URLs", r"(?m)^https?://(www\.)?(st\.com|nxp\.com|ti\.com|microchip\.com|renesas\.com|espressif\.com)\b.*$"),
    ]

    # Vendor name lines (standalone)
    for vendor in VENDOR_NAMES:
        standard.append((f"Vendor: {vendor}", rf"(?m)^{re.escape(vendor)}\s*$"))

    # Manual title patterns
    for pat in MANUAL_TITLE_PATTERNS:
        standard.append(("Manual title", pat))

    patterns.extend(standard)

    if aggressive:
        patterns.extend([
            ("TOC section", r"(?m)^#{1,3}\s*(Contents|Table of Contents|目录)\s*\n(.*?)(?=\n#{1,3}|\Z)"),
            ("Revision history", r"(?m)^#{1,3}\s*(Revision History|修改历史|版本历史)\s*\n.*?(?=\n#{1,3}|\Z)"),
            ("Empty table rows", r"(?m)^\|(\s*\|)+\s*$"),
        ])

    return patterns


# ─── Table Repair ──────────────────────────────────────────────────────

def repair_tables(content: str) -> str:
    """Fix common table formatting issues from PDF conversion."""
    lines = content.split("\n")
    repaired = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect table row
        if stripped.startswith("|"):
            repaired.append(line)

            # Check if next line is also a table row but NOT a separator
            # Only insert separator after the FIRST table row (header) if missing
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                is_separator = bool(re.match(r"^\|[\s\-:]+(\|[\s\-:]+)*\|?\s*$", next_stripped))
                if next_stripped.startswith("|") and not is_separator:
                    # Check if we just started a new table (previous line was not a table row)
                    prev_was_table = len(repaired) > 1 and repaired[-2].strip().startswith("|")
                    if not prev_was_table:
                        # This is a table header -> insert separator after it
                        col_count = stripped.count("|") - 1
                        if col_count > 0:
                            sep = "|" + "|".join(["---"] * col_count) + "|"
                            repaired.append(sep)
        else:
            repaired.append(line)
        i += 1

    # Remove empty lines within tables
    content = "\n".join(repaired)
    lines = content.split("\n")
    result = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            result.append(line)
        elif stripped == "" and in_table:
            # Skip empty lines in tables
            continue
        else:
            in_table = False
            result.append(line)

    return "\n".join(result)


# ─── Register Table Enhancement ────────────────────────────────────────

def normalize_unicode_math(content: str) -> str:
    """Replace Unicode math symbols with ASCII equivalents for MCU manuals."""
    replacements = {
        "\u00d7": "x",    # × → x (multiply)
        "\u00f7": "/",    # ÷ → /
        "\u00b1": "+/-",  # ± → +/-
        "\u2212": "-",    # − → - (minus sign)
        "\u2013": "-",    # – → - (en dash)
        "\u2014": "-",    # — → - (em dash)
        "\u2018": "'",    # ' → '
        "\u2019": "'",    # ' → '
        "\u201c": '"',    # " → "
        "\u201d": '"',    # " → "
        "\u2026": "...",  # … → ...
        "\u00a0": " ",    # non-breaking space → space
        "\u2192": "->",   # → → ->
        "\u2190": "<-",   # ← → <-
        "\u2194": "<->",  # ↔ → <->
        "\u2264": "<=",   # ≤ → <=
        "\u2265": ">=",   # ≥ → >=
        "\u2260": "!=",   # ≠ → !=
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def standardize_bit_fields(content: str) -> str:
    """Standardize bit-field notation for consistency."""
    # bit[3:0] → bits 3-0
    content = re.sub(r"\bbit\[(\d+):(\d+)\]", r"bits \1-\2", content)
    # [3:0] in table cells stays as-is (standard notation)
    return content


def clean_register_access_symbols(content: str) -> str:
    """Normalize register access type symbols (R/W, RC_W1, etc.)."""
    # Common access types in MCU manuals: R, W, R/W, RC_W1, RS, WS, R_W1C, etc.
    # Just ensure consistent spacing
    content = re.sub(r"\b(R/W|R\\W|R-only|W-only|RC_W1|RC_w1|RS|WS|R_W1C|RO|WO|RW)\b",
                     lambda m: m.group(1).upper(), content)
    return content


def enhance_register_tables(content: str) -> str:
    """
    Enhance register table readability:
    - Ensure consistent column formatting
    - Add code formatting to hex addresses and register names
    - Normalize Unicode math symbols
    - Standardize bit-field notation
    """
    # 1. Normalize Unicode
    content = normalize_unicode_math(content)

    # 2. Format hex addresses (0x40010800) as inline code
    content = re.sub(r"(?<!`)(\b0x[0-9A-Fa-f]{4,8}\b)(?!`)", r"`\1`", content)

    # 3. Format register names (e.g., GPIOx_CRH, USART_SR) - common MCU patterns
    reg_pattern = (
        r"(?<!`)(\b"
        r"(?:GPIO|USART|UART|SPI|I2C|TIM|ADC|DMA|EXTI|NVIC|RCC|FLASH|PWR|RTC|"
        r"WWDG|IWDG|CAN|USB|ETH|CRC|DBG|SYSCFG|AFIO|BKP|DAC|FSMC|SDIO|HASH|"
        r"RNG|DCMI|CRS|MDIOS|SAI|SWPMI|TFM|LPTIM|LPUART|VREF|COMP|OPAMP|"
        r"FPU|SCB|MPU|STK|SysTick|DWT|ITM|TPIU|DCB|DIB|nIRQ|mIRQ)"
        r"[A-Z0-9_]*"
        r"\b)(?!`)"
    )
    content = re.sub(reg_pattern, r"`\1`", content)

    # 4. Standardize bit fields
    content = standardize_bit_fields(content)

    # 5. Normalize access symbols
    content = clean_register_access_symbols(content)

    return content


# ─── Main Cleaning Function ────────────────────────────────────────────

def clean_markdown(content: str, aggressive: bool = True, report: bool = False) -> tuple:
    """
    Clean markdown content from PDF conversion artifacts.
    Returns (cleaned_content, stats_dict).
    """
    original_len = len(content)
    original_lines = content.count("\n")
    stats = {"removed_lines": 0, "patterns_applied": 0, "tables_repaired": 0}

    # 1. Detect repeated header/footer lines
    repeated = detect_repeated_lines(content, min_repeats=3)
    if report and repeated:
        print(f"  📊 Detected {len(repeated)} repeated header/footer lines:")
        for line in sorted(repeated)[:10]:
            print(f"     → \"{line[:60]}\"")
        if len(repeated) > 10:
            print(f"     ... and {len(repeated) - 10} more")

    # 2. Build and apply cleanup patterns
    patterns = build_cleanup_patterns(repeated, aggressive)
    for name, pattern in patterns:
        new_content = re.sub(pattern, "", content)
        if new_content != content:
            stats["patterns_applied"] += 1
        content = new_content

    # 3. Collapse excessive blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    # 4. Remove trailing whitespace
    content = re.sub(r"(?m)[ \t]+$", "", content)

    # 5. Remove leading whitespace on table rows
    content = re.sub(r"(?m)^\s+\|", "|", content)

    # 6. Repair tables
    content_before_repair = content
    content = repair_tables(content)
    if content != content_before_repair:
        stats["tables_repaired"] = 1

    # 7. Enhance register tables
    content = enhance_register_tables(content)

    # 8. Remove duplicate consecutive lines
    lines = content.split("\n")
    deduped = []
    for i, line in enumerate(lines):
        if i > 0 and line.strip() == lines[i-1].strip() and line.strip() != "":
            continue
        deduped.append(line)
    content = "\n".join(deduped)

    # Calculate stats
    new_lines = content.count("\n")
    stats["removed_lines"] = original_lines - new_lines
    stats["original_chars"] = original_len
    stats["cleaned_chars"] = len(content)
    stats["reduction_pct"] = round((1 - len(content) / max(original_len, 1)) * 100, 1)

    return content.strip() + "\n", stats


# ─── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Clean Markdown files converted from PDF (optimized for embedded/MCU manuals)"
    )
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("-o", "--output", help="Output file (default: input_cleaned.md)")
    parser.add_argument("--aggressive", action="store_true", default=True, help="Aggressive cleanup")
    parser.add_argument("--report", action="store_true", help="Print detailed report")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ File not found: {args.input}")
        sys.exit(1)

    output = args.output or str(Path(args.input).with_suffix("")) + "_cleaned.md"

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"📄 Input: {args.input} ({len(content):,} chars)")
    cleaned, stats = clean_markdown(content, aggressive=args.aggressive, report=args.report)

    with open(output, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ Output: {output} ({len(cleaned):,} chars)")
    print(f"📊 Stats: {stats['reduction_pct']}% reduction, {stats['removed_lines']} lines removed, {stats['patterns_applied']} patterns applied")


if __name__ == "__main__":
    main()
