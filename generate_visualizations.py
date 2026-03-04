#!/usr/bin/env python3
"""
Generate interactive HTML visualizations from AgentRE-Bench results.

Usage:
    python generate_visualizations.py results_cs_comparison/ -o visualizations.html
    python generate_visualizations.py results/ results_cs_comparison/ --max-models 8
    python generate_visualizations.py results_cs_comparison/
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def scan_results_directory(root: Path) -> List[Path]:
    """Find all benchmark_report.json files recursively."""
    return sorted(root.glob("**/benchmark_report.json"))


def extract_model_label(dir_name: str) -> str:
    """
    Parse directory name to extract human-readable label.

    Examples:
        claude_4_5_opus_effort_high_20260225_091824
        → "Claude 4.5 Opus (effort: high, 2026-02-25)"

        openai_claude-4-6-opus
        → "OpenAI Claude-4-6-Opus"
    """
    # Try to extract timestamp if present
    timestamp_match = None
    parts = dir_name.rsplit('_', 2)
    if len(parts) == 3 and len(parts[-2]) == 8 and len(parts[-1]) == 6:
        # Has timestamp: YYYYMMDD_HHMMSS
        timestamp_str = parts[-2]
        try:
            date = datetime.strptime(timestamp_str, '%Y%m%d')
            timestamp_match = date.strftime('%Y-%m-%d')
            dir_name = '_'.join(parts[:-2])
        except ValueError:
            pass

    # Extract effort level if present
    effort_match = None
    if '_effort_' in dir_name:
        parts = dir_name.split('_effort_')
        dir_name = parts[0]
        effort_match = parts[1].split('_')[0] if len(parts) > 1 else None

    # Format model name: replace underscores with spaces, title case
    model_name = dir_name.replace('_', ' ').title()

    # Build label components
    label_parts = [model_name]
    if effort_match:
        label_parts.append(f"effort: {effort_match}")
    if timestamp_match:
        label_parts.append(timestamp_match)

    # Join with parentheses for metadata
    if len(label_parts) > 1:
        return f"{label_parts[0]} ({', '.join(label_parts[1:])})"
    return label_parts[0]


def estimate_tokens_from_content(content) -> int:
    """
    Estimate token count from message content.
    Uses ~4 characters per token heuristic.
    """
    if isinstance(content, str):
        return len(content) // 4
    elif isinstance(content, list):
        total_chars = 0
        for item in content:
            if isinstance(item, dict):
                # Handle tool_use, tool_result, text blocks
                if 'text' in item:
                    total_chars += len(item['text'])
                if 'content' in item:
                    if isinstance(item['content'], str):
                        total_chars += len(item['content'])
                if 'input' in item:
                    # Tool input parameters
                    total_chars += len(json.dumps(item['input']))
            elif isinstance(item, str):
                total_chars += len(item)
        return total_chars // 4
    return 0


def calculate_cumulative_tokens_from_transcript(
    full_transcript_path: Path,
    total_tokens: int
) -> Dict[str, List]:
    """
    Calculate cumulative token usage by analyzing full transcript.
    Uses actual per-turn data if available, otherwise falls back to estimation.

    Returns:
        {
          'turns': [1, 2, 3, ...],
          'cumulative_tokens': [394, 789, 1184, ...],
          'input_tokens_per_turn': [209, 210, 185, ...],
          'output_tokens_per_turn': [185, 184, 200, ...]
        }
    """
    if not full_transcript_path.exists():
        return None

    try:
        with open(full_transcript_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"    Warning: Failed to load full transcript {full_transcript_path.name}: {e}")
        return None

    # Check if actual per-turn token data exists (new format)
    if isinstance(data, dict) and "per_turn_tokens" in data:
        per_turn_tokens = data["per_turn_tokens"]

        if not per_turn_tokens:
            return None

        return {
            'turns': [t["turn"] for t in per_turn_tokens],
            'cumulative_tokens': [t["cumulative_tokens"] for t in per_turn_tokens],
            'input_tokens_per_turn': [t["input_tokens"] for t in per_turn_tokens],
            'output_tokens_per_turn': [t["output_tokens"] for t in per_turn_tokens],
        }

    # Fallback: Estimate from messages (for backward compatibility with old format)
    messages = data if isinstance(data, list) else data.get("messages", [])

    # Calculate estimated tokens per message
    message_token_estimates = []
    cumulative_context = []
    cumulative = 0

    for msg in messages:
        tokens = estimate_tokens_from_content(msg.get('content', ''))
        message_token_estimates.append(tokens)
        cumulative += tokens
        cumulative_context.append(cumulative)

    # Total estimated tokens
    total_estimated = sum(message_token_estimates)

    # Normalize to actual total (scale factor)
    if total_estimated > 0:
        scale_factor = total_tokens / total_estimated
        cumulative_context = [int(c * scale_factor) for c in cumulative_context]
        message_token_estimates = [int(t * scale_factor) for t in message_token_estimates]

    # Group messages by turn (assistant messages represent turns)
    # Turn structure: user (system prompt) → assistant (reasoning + tool calls) → user (tool results) → ...
    turns = []
    input_per_turn = []
    output_per_turn = []
    cumulative_per_turn = []

    turn_num = 0
    i = 0
    while i < len(messages):
        if messages[i]['role'] == 'user' and i == 0:
            # Initial system prompt (turn 0, not counted as a turn)
            i += 1
            continue

        if messages[i]['role'] == 'assistant':
            turn_num += 1
            turns.append(turn_num)

            # Assistant message = output tokens
            output_tokens = message_token_estimates[i]
            output_per_turn.append(output_tokens)

            # Next user message (tool results) = input tokens
            input_tokens = 0
            if i + 1 < len(messages) and messages[i + 1]['role'] == 'user':
                input_tokens = message_token_estimates[i + 1]
                i += 1  # Skip the user message we just counted

            input_per_turn.append(input_tokens)

            # Cumulative at end of this turn
            cumulative_per_turn.append(cumulative_context[i])

            i += 1
        else:
            i += 1

    return {
        'turns': turns,
        'cumulative_tokens': cumulative_per_turn,
        'input_tokens_per_turn': input_per_turn,
        'output_tokens_per_turn': output_per_turn
    }


def load_full_transcript(results_dir: Path, task_id: str) -> Path:
    """Get path to full transcript file."""
    return results_dir / "transcripts" / f"{task_id}_full_transcript.json"


def enrich_task_metrics_with_token_data(report_path: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich task_metrics with per-turn token data from full transcript files.
    """
    results_dir = report_path.parent

    for task_metric in report.get('task_metrics', []):
        task_id = task_metric.get('task_id')
        if not task_id:
            continue

        total_tokens = task_metric.get('total_tokens', 0)
        if total_tokens == 0:
            continue

        # Load full transcript
        full_transcript_path = load_full_transcript(results_dir, task_id)

        # Calculate cumulative tokens
        token_data = calculate_cumulative_tokens_from_transcript(
            full_transcript_path,
            total_tokens
        )

        if token_data:
            task_metric['token_breakdown'] = token_data

    return report


def load_benchmark_report(path: Path) -> Dict[str, Any]:
    """Load a single benchmark report and add metadata + token breakdown."""
    with open(path) as f:
        data = json.load(f)

    # Add label extracted from directory name
    dir_name = path.parent.name
    data['label'] = extract_model_label(dir_name)

    # Enrich with per-turn token data from full transcripts
    data = enrich_task_metrics_with_token_data(path, data)

    return data


def generate_html(reports: List[Dict[str, Any]], css_path: Path, js_path: Path) -> str:
    """Generate self-contained HTML with embedded data, CSS, and JavaScript."""

    # Read CSS and JS files
    css_content = css_path.read_text()
    js_content = js_path.read_text()

    # Embed benchmark data as JSON
    benchmark_data = json.dumps(reports, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AgentRE-Bench Results</title>
  <style>
{css_content}
  </style>
</head>
<body>
  <!-- Navigation Bar -->
  <nav class="viz-navbar">
    <div class="container">
      <div class="nav-brand">AgentRE Benchmark Results</div>
      <div class="nav-tabs">
        <a href="#/dashboard" class="tab active">Dashboard</a>
        <a href="#/compare" class="tab">Compare</a>
      </div>
      <div class="nav-selector">
        <label>Select Model:</label>
        <select id="model-selector"></select>
      </div>
    </div>
  </nav>

  <!-- Main Content Area (dynamically populated) -->
  <main id="app">
    <div class="loading">Loading...</div>
  </main>

  <!-- Embedded Benchmark Data -->
  <script id="benchmark-data" type="application/json">
{benchmark_data}
  </script>

  <!-- Chart.js Library (from CDN) -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

  <!-- Application JavaScript -->
  <script>
{js_content}
  </script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(
        description='Generate interactive HTML visualizations from benchmark results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from single directory
  python generate_visualizations.py results_cs_comparison/

  # Custom output location
  python generate_visualizations.py results_cs_comparison/ -o report.html

  # Multiple result directories
  python generate_visualizations.py results/ results_cs_comparison/

  # Limit to most recent 8 models
  python generate_visualizations.py results_cs_comparison/ --max-models 8
        """
    )

    parser.add_argument(
        'results_dirs',
        nargs='+',
        type=Path,
        help='One or more directories containing benchmark results'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output HTML file path (default: <first_results_dir>/visualizations.html)'
    )
    parser.add_argument(
        '--max-models',
        type=int,
        default=0,
        help='Maximum number of models to include (0 = all, sorted by timestamp)'
    )
    parser.add_argument(
        '--css',
        type=Path,
        default=Path(__file__).parent / 'visualizations.css',
        help='Path to CSS file (default: visualizations.css in script directory)'
    )
    parser.add_argument(
        '--js',
        type=Path,
        default=Path(__file__).parent / 'visualizations.js',
        help='Path to JavaScript file (default: visualizations.js in script directory)'
    )

    args = parser.parse_args()

    # Validate inputs
    for results_dir in args.results_dirs:
        if not results_dir.exists():
            print(f"Error: Results directory does not exist: {results_dir}")
            return 1

    if not args.css.exists():
        print(f"Error: CSS file not found: {args.css}")
        return 1

    if not args.js.exists():
        print(f"Error: JavaScript file not found: {args.js}")
        return 1

    # Scan all directories for benchmark reports
    print(f"Scanning {len(args.results_dirs)} result directories...")
    all_report_paths = []
    for results_dir in args.results_dirs:
        report_paths = scan_results_directory(results_dir)
        all_report_paths.extend(report_paths)
        print(f"  {results_dir}: found {len(report_paths)} reports")

    if not all_report_paths:
        print("Error: No benchmark_report.json files found")
        return 1

    # Load reports
    print(f"\nLoading {len(all_report_paths)} benchmark reports...")
    reports = []
    for path in all_report_paths:
        try:
            report = load_benchmark_report(path)
            reports.append(report)
            print(f"  ✓ {report['label']}")
        except Exception as e:
            print(f"  ✗ Failed to load {path}: {e}")

    if not reports:
        print("Error: Failed to load any benchmark reports")
        return 1

    # Sort by timestamp (newest first) if multiple reports
    if len(reports) > 1:
        reports.sort(key=lambda r: r.get('label', ''), reverse=True)

    # Limit number of models if requested
    if args.max_models > 0 and len(reports) > args.max_models:
        print(f"\nLimiting to {args.max_models} most recent models")
        reports = reports[:args.max_models]

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.results_dirs[0] / 'visualizations.html'

    # Generate HTML
    print(f"\nGenerating HTML with {len(reports)} models...")
    html_content = generate_html(reports, args.css, args.js)

    # Write to file
    output_path.write_text(html_content)
    file_size_kb = len(html_content) / 1024

    print(f"\n✓ Generated: {output_path}")
    print(f"  File size: {file_size_kb:.1f} KB")
    print(f"  Models included: {len(reports)}")
    print(f"\nOpen in browser:")
    print(f"  file://{output_path.absolute()}")

    return 0


if __name__ == '__main__':
    exit(main())
