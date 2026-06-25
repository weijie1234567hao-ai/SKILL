#!/usr/bin/env python3
"""
LLM Evaluator for PDF-to-Markdown conversion quality.
Uses NVIDIA API (deepseek-ai/deepseek-v4-flash) to evaluate and rank multiple markdown outputs.

Usage:
    python llm_evaluate.py --files backend1.md backend2.md --api-key KEY [--model deepseek-ai/deepseek-v4-flash]
    python llm_evaluate.py --dir ./output --api-key KEY  # evaluate all .md in directory
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def read_md_sample(path: str, max_chars: int = 4000) -> str:
    """Read markdown file, return first max_chars as sample."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if len(content) > max_chars:
        return content[:max_chars] + "\n\n[... truncated ...]"
    return content


def build_eval_prompt(samples: dict) -> str:
    """Build evaluation prompt for LLM."""
    prompt = """You are an expert evaluator for PDF-to-Markdown conversion quality, specifically for embedded systems / MCU / motion controller programming manuals.

Evaluate each markdown sample on these criteria (0-10 each):

1. **Table Quality**: Are register tables, memory maps, and pin configuration tables intact with proper Markdown table syntax (| col | col |)?
2. **Structure Preservation**: Are document headings (H1-H6), sections, and hierarchical structure preserved?
3. **Cleanliness**: Are page headers, footers, company names, manual titles, page numbers, and revision stamps removed?
4. **Register Data Integrity**: Are register addresses (0x40010800), bit field definitions, reset values, and read/write attributes preserved correctly?
5. **Readability**: Is the overall markdown clean, consistent, and readable?

Scoring:
- 9-10: Excellent, production-ready
- 7-8: Good, minor issues
- 5-6: Acceptable, needs some cleanup
- 3-4: Poor, significant issues
- 0-2: Unusable

Total score: 0-50

Respond ONLY in this JSON format:
```json
{
  "scores": {
    "backend_name": {
      "table": N,
      "structure": N,
      "cleanliness": N,
      "register_data": N,
      "readability": N,
      "total": N
    }
  },
  "best": "backend_name",
  "reason": "2-3 sentence explanation",
  "recommendations": {
    "backend_name": "specific improvement suggestion"
  }
}
```

Here are the markdown samples to evaluate:

"""
    for name, sample in samples.items():
        prompt += f"\n{'='*60}\n## Backend: {name}\n{'='*60}\n\n{sample}\n"

    return prompt


def call_llm_api(prompt: str, api_key: str, model: str) -> dict:
    """Call NVIDIA API for LLM evaluation."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a technical document quality evaluator specializing in embedded systems, MCU datasheets, and motion controller programming manuals. You respond only in valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 3000,
        "top_p": 0.9,
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

            # Extract JSON from response
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                # Try to find raw JSON
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(response_text[json_start:json_end])
                return {"error": "Could not parse JSON from response", "raw": response_text}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"❌ HTTP {e.code}: {error_body[:500]}")
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="LLM-based Markdown quality evaluator")
    parser.add_argument("--files", nargs="+", help="Markdown files to evaluate")
    parser.add_argument("--dir", help="Directory containing markdown files")
    parser.add_argument("--api-key", default=os.environ.get("NVIDIA_API_KEY", ""), help="NVIDIA API key")
    parser.add_argument("--model", default="deepseek-ai/deepseek-v4-flash", help="LLM model")
    parser.add_argument("--output", "-o", default="evaluation_report.json", help="Output report file")
    parser.add_argument("--sample-chars", type=int, default=4000, help="Max chars per sample")
    args = parser.parse_args()

    # Collect files
    files = {}
    if args.dir:
        for md_path in sorted(Path(args.dir).rglob("*.md")):
            name = md_path.stem
            files[name] = str(md_path)
    elif args.files:
        for f in args.files:
            name = Path(f).stem
            files[name] = f
    else:
        print("❌ Provide --files or --dir")
        sys.exit(1)

    if not args.api_key:
        print("❌ API key required (use --api-key or NVIDIA_API_KEY env)")
        sys.exit(1)

    if not files:
        print("❌ No markdown files found")
        sys.exit(1)

    print(f"📊 Evaluating {len(files)} markdown files with {args.model}")
    print(f"📁 Files: {list(files.keys())}")
    print("="*60)

    # Read samples
    samples = {}
    for name, path in files.items():
        samples[name] = read_md_sample(path, args.sample_chars)
        print(f"  📄 {name}: {len(samples[name]):,} chars sampled")

    # Build prompt and call LLM
    prompt = build_eval_prompt(samples)
    print(f"\n🤖 Calling LLM API ({len(prompt):,} chars prompt)...")

    result = call_llm_api(prompt, args.api_key, args.model)

    if "error" in result:
        print(f"❌ Evaluation failed: {result['error']}")
        sys.exit(1)

    # Print results
    print("\n" + "="*60)
    print("📊 EVALUATION RESULTS")
    print("="*60)

    scores = result.get("scores", {})
    for backend, s in sorted(scores.items(), key=lambda x: x[1].get("total", 0), reverse=True):
        print(f"\n  {backend}:")
        print(f"    Table Quality:      {s.get('table', 0)}/10")
        print(f"    Structure:          {s.get('structure', 0)}/10")
        print(f"    Cleanliness:        {s.get('cleanliness', 0)}/10")
        print(f"    Register Data:      {s.get('register_data', 0)}/10")
        print(f"    Readability:        {s.get('readability', 0)}/10")
        print(f"    ────────────────────────")
        print(f"    TOTAL:              {s.get('total', 0)}/50")

    print(f"\n🏆 BEST: {result.get('best', 'N/A')}")
    print(f"📝 REASON: {result.get('reason', 'N/A')}")

    recs = result.get("recommendations", {})
    if recs:
        print("\n💡 RECOMMENDATIONS:")
        for backend, rec in recs.items():
            print(f"  {backend}: {rec}")

    # Save report
    report_path = args.output
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Report saved: {report_path}")

    return result


if __name__ == "__main__":
    main()
