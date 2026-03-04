#!/usr/bin/env python3
"""
Export AgentRE-Bench results to CSV files for Excel analysis.

Usage:
    python export_to_csv.py results_cs_last_comparison/
    python export_to_csv.py results_cs_last_comparison/ -o exports/
"""

import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Any


def scan_results_directory(root: Path) -> List[Path]:
    """Find all benchmark_report.json files recursively."""
    return sorted(root.glob("**/benchmark_report.json"))


def extract_model_label(dir_name: str) -> str:
    """Parse directory name to extract human-readable label."""
    from datetime import datetime

    # Try to extract timestamp if present
    timestamp_match = None
    parts = dir_name.rsplit('_', 2)
    if len(parts) == 3 and len(parts[-2]) == 8 and len(parts[-1]) == 6:
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

    # Format model name
    model_name = dir_name.replace('_', ' ').title()

    # Build label components
    label_parts = [model_name]
    if effort_match:
        label_parts.append(f"effort: {effort_match}")
    if timestamp_match:
        label_parts.append(timestamp_match)

    if len(label_parts) > 1:
        return f"{label_parts[0]} ({', '.join(label_parts[1:])})"
    return label_parts[0]


def export_aggregate_metrics(reports: List[Dict], output_path: Path):
    """Export aggregate metrics for all models to CSV."""
    fieldnames = [
        'model_label',
        'model',
        'provider',
        'total_score',
        'main_score',
        'bonus_score',
        'success_rate',
        'tasks_run',
        'tasks_with_answer',
        'avg_tool_calls_per_task',
        'avg_tool_calls_per_success',
        'avg_hallucination_rate',
        'total_tokens',
        'avg_tokens_per_task',
        'total_wall_time_seconds',
        'episode_length_mean',
        'episode_length_median',
        'episode_length_min',
        'episode_length_max',
        'max_steps_hit_count',
        'total_errors',
        'errors_context_overflow',
        'errors_timeout',
        'errors_other'
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for report in reports:
            agg = report['aggregate_metrics']
            errors_by_type = agg.get('errors_by_type', {})

            row = {
                'model_label': report['label'],
                'model': report['config']['model'],
                'provider': report['config']['provider'],
                'total_score': agg['total_score'],
                'main_score': agg['main_score'],
                'bonus_score': agg['bonus_score'],
                'success_rate': agg['success_rate'],
                'tasks_run': agg['tasks_run'],
                'tasks_with_answer': agg['tasks_with_answer'],
                'avg_tool_calls_per_task': agg['avg_tool_calls_per_task'],
                'avg_tool_calls_per_success': agg.get('avg_tool_calls_per_success', ''),
                'avg_hallucination_rate': agg['avg_hallucination_rate'],
                'total_tokens': agg['total_tokens'],
                'avg_tokens_per_task': agg['total_tokens'] / agg['tasks_run'] if agg['tasks_run'] > 0 else 0,
                'total_wall_time_seconds': agg['total_wall_time'],
                'episode_length_mean': agg.get('episode_length_mean', ''),
                'episode_length_median': agg.get('episode_length_median', ''),
                'episode_length_min': agg.get('episode_length_min', ''),
                'episode_length_max': agg.get('episode_length_max', ''),
                'max_steps_hit_count': agg.get('max_steps_hit_count', 0),
                'total_errors': agg.get('total_errors', 0),
                'errors_context_overflow': errors_by_type.get('context_overflow', 0),
                'errors_timeout': errors_by_type.get('timeout', 0),
                'errors_other': sum(v for k, v in errors_by_type.items() if k not in ['context_overflow', 'timeout'])
            }
            writer.writerow(row)

    print(f"  ✓ Exported aggregate metrics: {output_path.name}")


def export_task_metrics(reports: List[Dict], output_path: Path):
    """Export per-task metrics for all models to CSV."""
    fieldnames = [
        'model_label',
        'task_id',
        'level',
        'difficulty',
        'score',
        'tier',
        'decoded_c2_score',
        'techniques_score',
        'file_type_score',
        'encoded_strings_score',
        'c2_protocol_score',
        'tool_calls_total',
        'steps_to_answer',
        'wall_time_seconds',
        'total_tokens',
        'input_tokens',
        'output_tokens',
        'has_valid_answer',
        'max_steps_hit',
        'redundant_tool_calls',
        'invalid_tool_calls',
        'hallucination_count',
        'error_occurred',
        'error_type',
        'error_message'
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for report in reports:
            for task in report['task_metrics']:
                level_match = task['task_id'].split('_')[0].replace('level', '')
                field_scores = task.get('field_scores', {})

                row = {
                    'model_label': report['label'],
                    'task_id': task['task_id'],
                    'level': level_match,
                    'difficulty': task.get('difficulty', ''),
                    'score': task['score'],
                    'tier': task.get('tier', ''),
                    'decoded_c2_score': field_scores.get('decoded_c2', ''),
                    'techniques_score': field_scores.get('techniques', ''),
                    'file_type_score': field_scores.get('file_type', ''),
                    'encoded_strings_score': field_scores.get('encoded_strings', ''),
                    'c2_protocol_score': field_scores.get('c2_protocol', ''),
                    'tool_calls_total': task['tool_calls_total'],
                    'steps_to_answer': task.get('steps_to_answer', ''),
                    'wall_time_seconds': task['wall_time_seconds'],
                    'total_tokens': task['total_tokens'],
                    'input_tokens': task['input_tokens'],
                    'output_tokens': task['output_tokens'],
                    'has_valid_answer': task['has_valid_answer'],
                    'max_steps_hit': task['max_steps_hit'],
                    'redundant_tool_calls': task.get('redundant_tool_calls', 0),
                    'invalid_tool_calls': task.get('invalid_tool_calls', 0),
                    'hallucination_count': task.get('hallucination_count', 0),
                    'error_occurred': task.get('error_occurred', False),
                    'error_type': task.get('error_type', ''),
                    'error_message': task.get('error_message', '')
                }
                writer.writerow(row)

    print(f"  ✓ Exported task metrics: {output_path.name}")


def export_token_per_turn(reports: List[Dict], output_path: Path):
    """Export per-turn token usage for all tasks."""
    fieldnames = [
        'model_label',
        'task_id',
        'level',
        'turn',
        'input_tokens',
        'output_tokens',
        'total_tokens',
        'cumulative_tokens'
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for report in reports:
            results_dir = report.get('results_dir')
            if not results_dir:
                continue

            for task in report['task_metrics']:
                # Try to load from full transcript
                transcript_path = results_dir / 'transcripts' / f"{task['task_id']}_full_transcript.json"

                if not transcript_path.exists():
                    continue

                try:
                    with open(transcript_path) as tf:
                        transcript_data = json.load(tf)

                    # Check if per_turn_tokens exists (new format)
                    per_turn_tokens = None
                    if isinstance(transcript_data, dict) and 'per_turn_tokens' in transcript_data:
                        per_turn_tokens = transcript_data['per_turn_tokens']
                    elif isinstance(transcript_data, list):
                        # Old format - skip for now
                        continue

                    if not per_turn_tokens:
                        continue

                    level_match = task['task_id'].split('_')[0].replace('level', '')

                    for turn_data in per_turn_tokens:
                        row = {
                            'model_label': report['label'],
                            'task_id': task['task_id'],
                            'level': level_match,
                            'turn': turn_data['turn'],
                            'input_tokens': turn_data['input_tokens'],
                            'output_tokens': turn_data['output_tokens'],
                            'total_tokens': turn_data['total_tokens'],
                            'cumulative_tokens': turn_data['cumulative_tokens']
                        }
                        writer.writerow(row)

                except Exception as e:
                    # Skip tasks where we can't load transcript
                    continue

    print(f"  ✓ Exported per-turn tokens: {output_path.name}")


def export_tool_usage(reports: List[Dict], output_path: Path):
    """Export tool usage distribution for all models."""
    fieldnames = ['model_label', 'tool_name', 'count', 'percentage']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for report in reports:
            tool_dist = report['aggregate_metrics'].get('tool_usage_distribution', {})
            total_tools = sum(tool_dist.values()) if tool_dist else 0

            for tool_name, count in sorted(tool_dist.items(), key=lambda x: x[1], reverse=True):
                row = {
                    'model_label': report['label'],
                    'tool_name': tool_name,
                    'count': count,
                    'percentage': (count / total_tools * 100) if total_tools > 0 else 0
                }
                writer.writerow(row)

    print(f"  ✓ Exported tool usage: {output_path.name}")


def export_score_heatmap(reports: List[Dict], output_path: Path):
    """Export task x model score matrix (heatmap data)."""
    # Get all unique tasks across all models
    all_tasks = set()
    for report in reports:
        for task in report['task_metrics']:
            all_tasks.add(task['task_id'])

    # Sort tasks by level
    sorted_tasks = sorted(all_tasks, key=lambda t: int(t.split('_')[0].replace('level', '')))

    # Build matrix
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['task_id', 'level'] + [report['label'] for report in reports]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for task_id in sorted_tasks:
            level = task_id.split('_')[0].replace('level', '')
            row = {
                'task_id': task_id,
                'level': level
            }

            for report in reports:
                task_data = next((t for t in report['task_metrics'] if t['task_id'] == task_id), None)
                row[report['label']] = task_data['score'] if task_data else ''

            writer.writerow(row)

    print(f"  ✓ Exported score heatmap: {output_path.name}")


def export_tool_calls_by_type(reports: List[Dict], output_path: Path):
    """Export tool calls breakdown by type for each task."""
    # Collect all unique tool types
    all_tools = set()
    for report in reports:
        for task in report['task_metrics']:
            tool_calls_by_type = task.get('tool_calls_by_type', {})
            all_tools.update(tool_calls_by_type.keys())

    sorted_tools = sorted(all_tools)
    fieldnames = ['model_label', 'task_id', 'level'] + sorted_tools

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for report in reports:
            for task in report['task_metrics']:
                level = task['task_id'].split('_')[0].replace('level', '')
                tool_calls_by_type = task.get('tool_calls_by_type', {})

                row = {
                    'model_label': report['label'],
                    'task_id': task['task_id'],
                    'level': level
                }

                for tool in sorted_tools:
                    row[tool] = tool_calls_by_type.get(tool, 0)

                writer.writerow(row)

    print(f"  ✓ Exported tool calls by type: {output_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description='Export benchmark results to CSV files for Excel analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'results_dir',
        type=Path,
        help='Directory containing benchmark results'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output directory for CSV files (default: <results_dir>/csv_exports/)'
    )

    args = parser.parse_args()

    # Validate input
    if not args.results_dir.exists():
        print(f"Error: Results directory does not exist: {args.results_dir}")
        return 1

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = args.results_dir / 'csv_exports'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Scan for benchmark reports
    print(f"Scanning {args.results_dir}...")
    report_paths = scan_results_directory(args.results_dir)

    if not report_paths:
        print("Error: No benchmark_report.json files found")
        return 1

    print(f"Found {len(report_paths)} reports\n")

    # Load reports
    print("Loading reports...")
    reports = []
    for path in report_paths:
        try:
            with open(path) as f:
                data = json.load(f)

            # Add label and results directory path
            dir_name = path.parent.name
            data['label'] = extract_model_label(dir_name)
            data['results_dir'] = path.parent  # Store the results directory
            reports.append(data)
            print(f"  ✓ {data['label']}")
        except Exception as e:
            print(f"  ✗ Failed to load {path}: {e}")

    if not reports:
        print("\nError: Failed to load any reports")
        return 1

    print(f"\nExporting to {output_dir}/\n")

    # Export all CSV files
    export_aggregate_metrics(reports, output_dir / 'aggregate_metrics.csv')
    export_task_metrics(reports, output_dir / 'task_metrics.csv')
    export_token_per_turn(reports, output_dir / 'tokens_per_turn.csv')
    export_tool_usage(reports, output_dir / 'tool_usage.csv')
    export_score_heatmap(reports, output_dir / 'score_heatmap.csv')
    export_tool_calls_by_type(reports, output_dir / 'tool_calls_by_type.csv')

    print(f"\n✓ Exported {len(reports)} models to 6 CSV files")
    print(f"\nFiles created:")
    print(f"  • aggregate_metrics.csv    - Overall model performance")
    print(f"  • task_metrics.csv         - Per-task detailed results")
    print(f"  • tokens_per_turn.csv      - Turn-by-turn token usage")
    print(f"  • tool_usage.csv           - Tool usage distribution")
    print(f"  • score_heatmap.csv        - Task × Model score matrix")
    print(f"  • tool_calls_by_type.csv   - Tool usage per task")

    return 0


if __name__ == '__main__':
    exit(main())
