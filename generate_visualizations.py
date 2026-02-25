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


def load_benchmark_report(path: Path) -> Dict[str, Any]:
    """Load a single benchmark report and add metadata."""
    with open(path) as f:
        data = json.load(f)

    # Add label extracted from directory name
    dir_name = path.parent.name
    data['label'] = extract_model_label(dir_name)

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
