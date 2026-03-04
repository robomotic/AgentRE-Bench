# CSV Exports - AgentRE-Bench Results

This directory contains benchmark results exported to CSV format for analysis in Excel, Google Sheets, or other tools.

## Files Overview

### 1. `aggregate_metrics.csv`
**Overall performance metrics for each model configuration**

Key columns:
- `model_label`: Human-readable model name and configuration
- `total_score`: Combined score (main + bonus, max 2.0)
- `main_score`: Average score across levels 1-12 (max 1.0)
- `bonus_score`: Score on level 13 (max 1.0)
- `success_rate`: Percentage of tasks with valid answers
- `avg_tool_calls_per_task`: Average number of tool calls per task
- `total_tokens`: Total tokens used across all tasks
- `episode_length_mean`: Average time per task in seconds
- `total_errors`, `errors_context_overflow`: Error counts

**Suggested Excel charts:**
- Bar chart: `total_score` by `model_label`
- Scatter plot: `avg_tool_calls_per_task` vs `total_score`
- Line chart: `episode_length_mean` vs `success_rate`

---

### 2. `task_metrics.csv`
**Detailed per-task results for all models**

Key columns:
- `model_label`, `task_id`, `level`: Task identification
- `score`: Final score for this task (0.0 - 1.0)
- `decoded_c2_score`, `techniques_score`, etc.: Field-level scores
- `tool_calls_total`: Number of tools used
- `wall_time_seconds`: Time taken for this task
- `total_tokens`, `input_tokens`, `output_tokens`: Token usage
- `error_occurred`, `error_message`: Error information

**Suggested Excel charts:**
- Pivot table: Average score by level and model
- Line chart: Score progression across levels (filter by model)
- Scatter plot: `tool_calls_total` vs `score` (colored by model)

**Excel Pivot Table Example:**
1. Insert → PivotTable
2. Rows: `level`
3. Columns: `model_label`
4. Values: Average of `score`

---

### 3. `tokens_per_turn.csv`
**Turn-by-turn token usage breakdown**

Key columns:
- `model_label`, `task_id`, `level`, `turn`: Identifies each turn
- `input_tokens`: Tokens in the input (context + tool results)
- `output_tokens`: Tokens in the output (assistant response)
- `total_tokens`: Sum of input and output for this turn
- `cumulative_tokens`: Running total up to this turn

**Suggested Excel charts:**
- Stacked area chart: `cumulative_tokens` over `turn` (filter by task)
- Stacked column chart: `input_tokens` and `output_tokens` by `turn`

**Excel Chart Example - Cumulative Token Growth:**
1. Filter to a single task (e.g., `level4_polymorphicReverseShell`)
2. Select columns: `turn`, `cumulative_tokens`
3. Insert → Line Chart
4. Add a second series for failed turn if error occurred

---

### 4. `tool_usage.csv`
**Tool usage distribution by model**

Key columns:
- `model_label`: Model configuration
- `tool_name`: Name of the tool (e.g., `objdump`, `strings`)
- `count`: Number of times this tool was called
- `percentage`: Percentage of total tool calls

**Suggested Excel charts:**
- Pie chart: Tool distribution for a single model
- Grouped bar chart: Tool counts across all models
- 100% stacked bar chart: Tool usage proportions by model

---

### 5. `score_heatmap.csv`
**Task × Model score matrix**

Structure:
- Rows: Tasks (level1_TCPServer, level2_XorEncodedStrings, ...)
- Columns: Model configurations
- Values: Scores (0.0 - 1.0)

**Suggested Excel charts:**
- Heatmap with conditional formatting:
  1. Select the score columns
  2. Home → Conditional Formatting → Color Scales
  3. Choose Red-Yellow-Green scale (red = 0, green = 1)

---

### 6. `tool_calls_by_type.csv`
**Tool usage breakdown for each task**

Key columns:
- `model_label`, `task_id`, `level`: Task identification
- Additional columns: One per tool type (e.g., `file`, `strings`, `objdump`)
- Values: Count of how many times each tool was used in that task

**Suggested Excel charts:**
- Stacked bar chart: Tool usage across tasks (filter by model)
- Pivot table: Total tool usage by level

---

## Tips for Excel Analysis

### Creating a Model Comparison Dashboard

1. **Summary Metrics Table**
   - Use data from `aggregate_metrics.csv`
   - Create a table with key metrics side-by-side

2. **Performance Trend Chart**
   - Use `task_metrics.csv`
   - Create a line chart showing score vs level
   - Add one line per model

3. **Token Efficiency Analysis**
   - Use `tokens_per_turn.csv`
   - Calculate tokens per successful task
   - Compare across models

### Conditional Formatting for Scores

Apply to score columns in `task_metrics.csv`:
- Green: ≥ 0.8 (excellent)
- Yellow: 0.5 - 0.79 (good)
- Red: < 0.5 (needs improvement)

### Identifying Context Overflow Issues

Filter `task_metrics.csv` where:
- `error_type` = "context_overflow"
- Look at `total_tokens` and `tool_calls_total`
- Cross-reference with `tokens_per_turn.csv` to see growth pattern

---

## Example Analysis Questions

1. **Which model is most efficient?**
   - Compare `total_tokens` / `tasks_with_answer` from `aggregate_metrics.csv`

2. **Which tasks are hardest?**
   - Average `score` by `level` across all models in `task_metrics.csv`

3. **Do more tool calls lead to higher scores?**
   - Scatter plot: `tool_calls_total` vs `score` in `task_metrics.csv`

4. **Which tools are most valuable?**
   - Join `tool_usage.csv` with `aggregate_metrics.csv` by `model_label`
   - Correlate tool usage patterns with success rate

5. **Where do context overflows happen?**
   - Filter `tokens_per_turn.csv` for tasks with errors
   - Observe the turn where cumulative tokens spike

---

## Need the Interactive Visualizations?

These CSV files are complementary to the HTML visualization:
- **HTML**: Interactive charts, drill-down, at-a-glance comparison
- **CSV**: Detailed analysis, custom queries, Excel/Python integration

Open `visualizations.html` in a browser for interactive exploration.

---

## Regenerating These Files

To regenerate the CSV exports from benchmark results:

```bash
python export_to_csv.py results_cs_last_comparison/
```

The script will create a `csv_exports/` directory with all 6 files.
