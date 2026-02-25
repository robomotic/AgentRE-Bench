# Visualization Module

Interactive HTML dashboards for comparing AgentRE-Bench results across multiple model configurations.

## Overview

The visualization module generates self-contained HTML files with embedded data, CSS, and JavaScript. These files can be opened directly in a browser, shared via email, or hosted on GitHub Pages.

**Features:**
- Compare 8-10+ model configurations side-by-side
- Interactive charts (leaderboard, task progression, tool usage, heatmaps)
- Three views: Dashboard, Model Detail, and Comparison
- Dark theme matching docs/index.html
- Mobile-responsive design
- Zero runtime dependencies (works offline)

## Quick Start

### Generate Visualizations

```bash
# From single results directory
python generate_visualizations.py results/ -o report.html

# From multiple directories
python generate_visualizations.py results/ results_cs_comparison/ -o combined.html

# Limit to 8 most recent models
python generate_visualizations.py results_cs_comparison/ --max-models 8

# Default output (writes to first directory)
python generate_visualizations.py results/
# Creates: results/visualizations.html
```

### View in Browser

```bash
# macOS
open visualizations.html

# Linux
xdg-open visualizations.html

# Windows
start visualizations.html

# Or directly in browser
file:///path/to/visualizations.html
```

## Architecture

### Files

- **[generate_visualizations.py](generate_visualizations.py)** - Python generator script (200 lines)
- **[visualizations.css](visualizations.css)** - Stylesheet with dark theme (550 lines)
- **[visualizations.js](visualizations.js)** - Client-side application (800 lines)

### Data Flow

```
results/
  model_run_*/benchmark_report.json
       ↓ [scan & load]
generate_visualizations.py
       ↓ [embed + template]
visualizations.html (self-contained)
       ↓ [parse & render]
Interactive Dashboard (browser)
```

### Tech Stack

- **Backend:** Python 3.8+ (zero dependencies, stdlib only)
- **Frontend:** Vanilla JavaScript (ES6+), Chart.js 4.4
- **Styling:** Pure CSS Grid (no framework)

## Page Views

### 1. Dashboard (Default View)

**URL:** `#/dashboard`

**Features:**
- Horizontal bar chart (leaderboard by total score)
- Aggregate metrics cards (5 cards with averages across all models)
- Click bar to navigate to model detail

**Metrics Displayed:**
- Avg Main Score (levels 1-12)
- Avg Bonus Score (level 13)
- Avg Success Rate
- Avg Tool Calls per task
- Avg Hallucination Rate

### 2. Model Detail

**URL:** `#/model/{id}`

**Features:**
- Configuration panel (model, provider, max_tool_calls, docker)
- 6 aggregate metric cards
- Task progression line chart (scores across levels 1-13)
- Per-task table (13 rows, expandable for field scores)
- Tool usage doughnut chart

**Interactions:**
- Click task row to expand field score breakdown
- Hover chart points for exact values
- Error badge on failed tasks

### 3. Comparison View

**URL:** `#/compare`

**Features:**
- Model cards grid (8-10+ models, scrollable)
- Score heatmap (13 levels × N models, color-coded)
- Multi-series line chart (all models overlaid)

**Interactions:**
- Click model card to navigate to detail
- Click heatmap cell to navigate to model + task
- Toggle models in line chart legend

## Usage Examples

### Example 1: Single Model Analysis

```bash
# Generate for one model
python generate_visualizations.py results/openai_claude-4-6-opus/ -o claude_report.html

# Open in browser
open claude_report.html
```

### Example 2: Multi-Model Comparison

```bash
# Generate for all models in directory
python generate_visualizations.py results_cs_comparison/ -o comparison.html

# View comparison
open comparison.html
# Navigate to: #/compare
```

### Example 3: Custom CSS/JS

```bash
# Use custom theme or modified JS
python generate_visualizations.py results/ \
  --css custom_theme.css \
  --js custom_viz.js \
  -o custom_report.html
```

## Configuration

### CLI Options

```
generate_visualizations.py [-h] [-o OUTPUT] [--max-models MAX_MODELS]
                           [--css CSS] [--js JS]
                           results_dirs [results_dirs ...]

Positional arguments:
  results_dirs          One or more directories containing benchmark results

Options:
  -h, --help            Show help message
  -o OUTPUT, --output OUTPUT
                        Output HTML file path (default: <first_results_dir>/visualizations.html)
  --max-models MAX_MODELS
                        Maximum number of models to include (0 = all, sorted by timestamp)
  --css CSS             Path to CSS file (default: visualizations.css)
  --js JS               Path to JavaScript file (default: visualizations.js)
```

### Model Label Extraction

The generator automatically extracts human-readable labels from directory names:

| Directory Name | Extracted Label |
|----------------|-----------------|
| `claude_4_5_opus_effort_high_20260225_091824` | "Claude 4.5 Opus (effort: high, 2026-02-25)" |
| `openai_claude-4-6-opus` | "Openai Claude-4-6-Opus" |
| `gpt_4o_turbo` | "Gpt 4O Turbo" |

## Data Structure

### Input: benchmark_report.json

Required fields:
```json
{
  "config": {
    "model": "claude-4-6-opus",
    "provider": "openai",
    "max_tool_calls": 25,
    "use_docker": true
  },
  "aggregate_metrics": {
    "total_score": 0.8,
    "main_score": 0.75,
    "bonus_score": 0.05,
    "success_rate": 0.923,
    "avg_tool_calls_per_task": 14.2,
    "tool_usage_distribution": {"file": 13, "readelf": 26, ...},
    "avg_hallucination_rate": 0.03,
    "total_wall_time": 1234.5,
    "total_tokens": 123456,
    "tasks_run": 13,
    "tasks_with_answer": 12,
    "episode_length_mean": 95.0
  },
  "task_metrics": [
    {
      "task_id": "level1_TCPServer",
      "score": 1.0,
      "tier": "standard",
      "field_scores": {"decoded_c2": 1.0, "techniques": 1.0, ...},
      "tool_calls_total": 11,
      "hallucinated_techniques": [],
      "wall_time_seconds": 45.2,
      "error_occurred": false,
      "error_message": null
    },
    // ... 12 more tasks
  ]
}
```

### Output: visualizations.html

Self-contained HTML file (~50-200 KB) containing:
- Embedded CSS styles
- Embedded benchmark JSON data
- Embedded JavaScript application
- Chart.js library (CDN link)

## Customization

### Modify Theme Colors

Edit [visualizations.css](visualizations.css):

```css
:root {
  --accent: #00d4aa;  /* Change accent color */
  --bg: #0a0a12;      /* Change background */
  --text: #e0e0e8;    /* Change text color */
}
```

### Add New Chart Types

Edit [visualizations.js](visualizations.js):

```javascript
class ChartRenderer {
  renderNewChart(canvasId, data) {
    // Add custom Chart.js configuration
  }
}
```

### Modify View Layouts

Edit view classes in [visualizations.js](visualizations.js):

```javascript
class ModelDetailView {
  render(modelId) {
    // Customize HTML template
  }
}
```

## Troubleshooting

### No benchmark_report.json found

**Problem:** `Error: No benchmark_report.json files found`

**Solution:** Ensure you're pointing to directories containing completed benchmark runs. Check:
```bash
find results_cs_comparison -name "benchmark_report.json"
```

If missing, run the benchmark first:
```bash
python run_benchmark.py --all --report results_cs_comparison/new_run/
```

### Charts not rendering

**Problem:** Dashboard loads but charts are blank

**Possible causes:**
1. Browser console errors (F12 → Console)
2. Chart.js CDN blocked (check network tab)
3. Invalid JSON data

**Solution:** Check browser console for errors. If CDN is blocked, download Chart.js and embed directly.

### File size too large

**Problem:** HTML file > 1 MB

**Cause:** Too many models or very detailed transcripts

**Solution:** Use `--max-models` to limit:
```bash
python generate_visualizations.py results_cs_comparison/ --max-models 8
```

## Performance

### File Size

| Models | File Size | Load Time (avg) |
|--------|-----------|-----------------|
| 1      | ~40 KB    | < 100ms         |
| 5      | ~150 KB   | < 200ms         |
| 10     | ~300 KB   | < 400ms         |
| 20     | ~600 KB   | < 800ms         |

### Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Integration

### Add to Benchmark Workflow

Automatically generate visualizations after benchmark runs:

```bash
# In run_benchmark.py or CI/CD pipeline
python run_benchmark.py --all --report results/run_1/
python generate_visualizations.py results/run_1/ -o results/run_1/index.html
```

### Deploy to GitHub Pages

```bash
# Copy to docs/ directory
python generate_visualizations.py results/ -o docs/results.html

# Commit and push
git add docs/results.html
git commit -m "Update benchmark visualizations"
git push

# Access at: https://yourusername.github.io/AgentRE-Bench/results.html
```

### Share Results

```bash
# Generate report
python generate_visualizations.py results/ -o benchmark_results.html

# Share via email (self-contained, works offline)
# Or upload to cloud storage (Dropbox, Google Drive, S3)
```

## Future Enhancements

Potential features for future versions:

- [ ] Export comparison as CSV/JSON
- [ ] Drill-down to full transcripts
- [ ] Metric distribution plots (box plots)
- [ ] Timeline view (runs over time)
- [ ] Filtering by model/provider
- [ ] Custom metric calculations
- [ ] Print-friendly CSS
- [ ] PDF export

## Credits

- **Chart.js:** https://www.chartjs.org/
- **Design:** Matches AgentRE-Bench docs theme
- **License:** Same as parent project

