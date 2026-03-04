// AgentRE-Bench Visualizations - Client-Side Application
// Zero-dependency vanilla JavaScript with Chart.js for plotting

// ═══════════════════════════════════════════════════════════════════════════
// Data Model
// ═══════════════════════════════════════════════════════════════════════════

class ComparisonDataset {
  constructor() {
    this.models = [];
    this.taskLookup = new Map();
    this.aggregateLookup = new Map();
  }

  loadFromEmbedded() {
    const dataElement = document.getElementById('benchmark-data');
    if (!dataElement) {
      console.error('No benchmark data found in page');
      return false;
    }

    try {
      this.models = JSON.parse(dataElement.textContent);
      this._buildLookups();
      return true;
    } catch (error) {
      console.error('Failed to parse benchmark data:', error);
      return false;
    }
  }

  _buildLookups() {
    // Build task lookup: task_id → [model1_metrics, model2_metrics, ...]
    const taskMap = {};
    this.models.forEach(model => {
      model.task_metrics.forEach(task => {
        if (!taskMap[task.task_id]) {
          taskMap[task.task_id] = [];
        }
        taskMap[task.task_id].push({ ...task, modelLabel: model.label });
      });
    });
    this.taskLookup = new Map(Object.entries(taskMap));

    // Build aggregate lookup: model_label → aggregate_metrics
    this.models.forEach(model => {
      this.aggregateLookup.set(model.label, model.aggregate_metrics);
    });
  }

  getModels() {
    return this.models;
  }

  getTasksByLevel() {
    // Return tasks sorted by level 1-13
    const allTasks = Array.from(this.taskLookup.keys());
    return allTasks.sort((a, b) => {
      const levelA = parseInt(a.match(/level(\d+)/)[1]);
      const levelB = parseInt(b.match(/level(\d+)/)[1]);
      return levelA - levelB;
    });
  }

  getTaskMetricsForModel(modelLabel) {
    const model = this.models.find(m => m.label === modelLabel);
    if (!model) return [];

    // Sort by level
    return model.task_metrics.sort((a, b) => {
      const levelA = parseInt(a.task_id.match(/level(\d+)/)[1]);
      const levelB = parseInt(b.task_id.match(/level(\d+)/)[1]);
      return levelA - levelB;
    });
  }

  getAggregateMetrics(modelLabel) {
    return this.aggregateLookup.get(modelLabel);
  }
}

// Global dataset instance
const dataset = new ComparisonDataset();

// ═══════════════════════════════════════════════════════════════════════════
// Chart Renderers
// ═══════════════════════════════════════════════════════════════════════════

class ChartRenderer {
  constructor() {
    this.charts = new Map(); // Track chart instances for cleanup
  }

  destroy(containerId) {
    const chart = this.charts.get(containerId);
    if (chart) {
      chart.destroy();
      this.charts.delete(containerId);
    }
  }

  destroyAll() {
    this.charts.forEach(chart => chart.destroy());
    this.charts.clear();
  }

  renderLeaderboard(canvasId, models) {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Sort models by total_score descending
    const sorted = [...models].sort((a, b) =>
      b.aggregate_metrics.total_score - a.aggregate_metrics.total_score
    );

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sorted.map(m => m.label),
        datasets: [{
          label: 'Total Score',
          data: sorted.map(m => m.aggregate_metrics.total_score),
          backgroundColor: '#00d4aa',
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            callbacks: {
              label: (context) => `Score: ${context.parsed.x.toFixed(3)}`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            max: 2.0,
            grid: { color: '#1e1e2a' },
            ticks: { color: '#8888a0' }
          },
          y: {
            grid: { display: false },
            ticks: { color: '#8888a0', font: { size: 11 } }
          }
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const modelLabel = sorted[index].label;
            const modelId = dataset.models.findIndex(m => m.label === modelLabel);
            router.navigate(`model/${modelId}`);
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }

  renderTaskProgression(canvasId, modelLabel, chartType = 'line') {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const tasks = dataset.getTaskMetricsForModel(modelLabel);
    const levels = tasks.map(t => {
      const match = t.task_id.match(/level(\d+)/);
      return match ? parseInt(match[1]) : 0;
    });

    const chart = new Chart(ctx, {
      type: chartType,
      data: {
        labels: levels.map(l => `L${l}`),
        datasets: [{
          label: 'Score',
          data: tasks.map(t => t.score),
          borderColor: '#00d4aa',
          backgroundColor: chartType === 'bar' ? '#00d4aa' : 'rgba(0, 212, 170, 0.1)',
          borderWidth: 2,
          pointRadius: chartType === 'line' ? 4 : 0,
          pointHoverRadius: chartType === 'line' ? 6 : 0,
          tension: 0.2,
          fill: chartType === 'line'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            callbacks: {
              title: (items) => {
                const index = items[0].dataIndex;
                return tasks[index].task_id;
              },
              label: (context) => `Score: ${context.parsed.y.toFixed(3)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1.0,
            grid: { color: '#1e1e2a' },
            ticks: { color: '#8888a0' }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#8888a0' }
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }

  renderTaskProgressionComparison(canvasId, models, currentModelIndex, chartType = 'line') {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const colors = [
      '#00d4aa', '#6366f1', '#f59e0b', '#22c55e',
      '#ef4444', '#06b6d4', '#eab308', '#ec4899'
    ];

    // Build datasets for all models, with current model first and highlighted
    const datasets = models.map((model, index) => {
      const tasks = dataset.getTaskMetricsForModel(model.label);
      const isCurrent = index === currentModelIndex;
      const color = colors[index % colors.length];

      return {
        label: model.label,
        data: tasks.map(t => t.score),
        borderColor: color,
        backgroundColor: chartType === 'bar' ? color : (color + (isCurrent ? '30' : '10')),
        borderWidth: chartType === 'line' ? (isCurrent ? 3 : 2) : 0,
        pointRadius: chartType === 'line' ? (isCurrent ? 4 : 3) : 0,
        pointHoverRadius: chartType === 'line' ? (isCurrent ? 6 : 5) : 0,
        tension: 0.2,
        fill: chartType === 'line' && isCurrent,
        order: isCurrent ? 0 : 1  // Current model on top
      };
    });

    // Move current model to front of array
    const currentDataset = datasets[currentModelIndex];
    datasets.splice(currentModelIndex, 1);
    datasets.unshift(currentDataset);

    const maxTasks = Math.max(...models.map(m => m.task_metrics.length));
    const labels = Array.from({ length: maxTasks }, (_, i) => `L${i + 1}`);

    const chart = new Chart(ctx, {
      type: chartType,
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#e0e0e8',
              padding: 8,
              font: { size: 10 },
              usePointStyle: true,
              generateLabels: (chart) => {
                const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                // Highlight current model in legend
                original.forEach((label, index) => {
                  if (index === 0) {  // Current model is first
                    label.fontStyle = 'bold';
                    label.text = '★ ' + label.text;
                  }
                });
                return original;
              }
            },
            onClick: (e, legendItem, legend) => {
              const index = legendItem.datasetIndex;
              const chart = legend.chart;
              const meta = chart.getDatasetMeta(index);

              // Toggle visibility
              meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
              chart.update();
            },
            onHover: (e, legendItem, legend) => {
              e.native.target.style.cursor = 'pointer';
            },
            onLeave: (e, legendItem, legend) => {
              e.native.target.style.cursor = 'default';
            }
          },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1.0,
            grid: { color: '#1e1e2a' },
            ticks: { color: '#8888a0' }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#8888a0' }
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }

  renderToolUsage(canvasId, toolDistribution) {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const tools = Object.keys(toolDistribution);
    const counts = Object.values(toolDistribution);

    const colors = [
      '#00d4aa', '#6366f1', '#22c55e', '#f59e0b',
      '#ef4444', '#06b6d4', '#eab308', '#ec4899'
    ];

    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: tools,
        datasets: [{
          data: counts,
          backgroundColor: colors.slice(0, tools.length),
          borderWidth: 2,
          borderColor: '#111119'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: '#e0e0e8',
              padding: 12,
              font: { size: 11 }
            }
          },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }

  renderCumulativeTokens(canvasId, task) {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Get token breakdown data
    const tokenData = task.token_breakdown;
    if (!tokenData || !tokenData.turns || tokenData.turns.length === 0) {
      console.warn('No token breakdown data available for task:', task.task_id);
      return;
    }

    const turns = tokenData.turns;
    const inputPerTurn = tokenData.input_tokens_per_turn;
    const outputPerTurn = tokenData.output_tokens_per_turn;
    const cumulative = tokenData.cumulative_tokens;

    // Check if there's a context overflow error
    const hasContextOverflow = task.error_occurred &&
                                task.error_type === 'context_overflow' &&
                                task.error_message;
    let errorTokenCount = null;

    if (hasContextOverflow) {
      // Extract token count from error message like "Context overflow: 217154 tokens"
      const match = task.error_message.match(/(\d+)\s+tokens/);
      if (match) {
        errorTokenCount = parseInt(match[1]);
      }
    }

    // Build datasets
    const datasets = [
      {
        label: 'Input Tokens',
        data: inputPerTurn,
        backgroundColor: '#6366f1',  // Indigo
        stack: 'tokens',
        order: 2
      },
      {
        label: 'Output Tokens',
        data: outputPerTurn,
        backgroundColor: '#00d4aa',  // Teal (accent)
        stack: 'tokens',
        order: 2
      },
      {
        label: 'Cumulative Total',
        data: cumulative,
        type: 'line',  // Line chart overlaid on bars
        borderColor: '#f59e0b',  // Orange
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.2,
        order: 1,  // Render on top
        yAxisID: 'y-cumulative'
      }
    ];

    // Add error point if context overflow occurred
    if (errorTokenCount) {
      datasets.push({
        label: 'Context Overflow',
        data: [...Array(turns.length).fill(null), errorTokenCount],
        type: 'scatter',
        backgroundColor: '#ef4444',  // Red
        borderColor: '#ef4444',
        pointRadius: 6,
        pointHoverRadius: 8,
        pointStyle: 'triangle',
        order: 0,  // Render on top
        yAxisID: 'y-cumulative'
      });
    }

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [...turns.map(t => `Turn ${t}`), ...(errorTokenCount ? ['Failed'] : [])],
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#e0e0e8',
              padding: 8,
              font: { size: 10 },
              usePointStyle: true,
              filter: function(item) {
                // Hide the Context Overflow from legend if there's no error
                return item.text !== 'Context Overflow' || errorTokenCount !== null;
              }
            }
          },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            callbacks: {
              title: (items) => {
                const item = items[0];
                if (item.dataset.label === 'Context Overflow') {
                  return 'Turn ' + (turns.length + 1) + ' (Failed)';
                }
                return item.label;
              },
              label: (context) => {
                if (context.dataset.label === 'Context Overflow') {
                  return `Context would overflow at ${context.parsed.y.toLocaleString()} tokens`;
                }
                return context.dataset.label + ': ' + Math.round(context.parsed.y).toLocaleString() + ' tokens';
              },
              footer: (items) => {
                const turnIndex = items[0].dataIndex;
                if (turnIndex >= cumulative.length) {
                  return 'Error occurred before this turn completed';
                }
                return `Cumulative: ${Math.round(cumulative[turnIndex]).toLocaleString()} tokens`;
              }
            }
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: {
              color: '#8888a0',
              maxRotation: 45,
              minRotation: 0,
              font: { size: 9 }
            }
          },
          y: {
            stacked: true,
            position: 'left',
            title: {
              display: true,
              text: 'Tokens per Turn',
              color: '#8888a0',
              font: { size: 11 }
            },
            grid: { color: '#1e1e2a' },
            ticks: { color: '#8888a0' }
          },
          'y-cumulative': {
            position: 'right',
            title: {
              display: true,
              text: 'Cumulative Total',
              color: '#f59e0b',
              font: { size: 11 }
            },
            grid: { display: false },
            ticks: { color: '#8888a0' }
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }

  renderMultiModelComparison(canvasId, models) {
    this.destroy(canvasId);

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const datasets = models.map((model, index) => {
      const tasks = dataset.getTaskMetricsForModel(model.label);
      const colors = ['#00d4aa', '#6366f1', '#f59e0b', '#22c55e', '#ef4444', '#06b6d4', '#eab308', '#ec4899'];
      const color = colors[index % colors.length];

      return {
        label: model.label,
        data: tasks.map(t => t.score),
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.2
      };
    });

    const maxTasks = Math.max(...models.map(m => m.task_metrics.length));
    const labels = Array.from({ length: maxTasks }, (_, i) => `L${i + 1}`);

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#e0e0e8',
              padding: 12,
              font: { size: 11 },
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: '#111119',
            titleColor: '#e0e0e8',
            bodyColor: '#e0e0e8',
            borderColor: '#1e1e2a',
            borderWidth: 1,
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1.0,
            grid: { color: '#1e1e2a' },
            ticks: { color: '#8888a0' }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#8888a0' }
          }
        }
      }
    });

    this.charts.set(canvasId, chart);
  }
}

const chartRenderer = new ChartRenderer();

// ═══════════════════════════════════════════════════════════════════════════
// View Controllers
// ═══════════════════════════════════════════════════════════════════════════

class DashboardView {
  render() {
    const models = dataset.getModels();
    if (models.length === 0) {
      return '<div class="loading">No benchmark data available</div>';
    }

    return `
      <div class="container">
        <div class="page-header">
          <h1 class="page-title">Benchmark Dashboard</h1>
          <p class="page-subtitle">Overview of all model configurations</p>
        </div>

        <div class="chart-container">
          <h2 class="chart-title">Leaderboard - Total Score</h2>
          <div class="chart-canvas" style="height: ${Math.max(300, models.length * 60)}px;">
            <canvas id="leaderboard-chart"></canvas>
          </div>
        </div>

        ${this._renderAggregateMetricsGrid(models)}
      </div>
    `;
  }

  _renderAggregateMetricsGrid(models) {
    const avgMainScore = models.reduce((sum, m) => sum + m.aggregate_metrics.main_score, 0) / models.length;
    const avgBonusScore = models.reduce((sum, m) => sum + m.aggregate_metrics.bonus_score, 0) / models.length;
    const avgSuccessRate = models.reduce((sum, m) => sum + m.aggregate_metrics.success_rate, 0) / models.length;
    const avgToolCalls = models.reduce((sum, m) => sum + m.aggregate_metrics.avg_tool_calls_per_task, 0) / models.length;
    const avgHallucinationRate = models.reduce((sum, m) => sum + m.aggregate_metrics.avg_hallucination_rate, 0) / models.length;

    // Calculate min/max statistics
    const totalScores = models.map(m => m.aggregate_metrics.total_score);
    const minTotalScore = Math.min(...totalScores);
    const maxTotalScore = Math.max(...totalScores);

    const episodeTimes = models.map(m => m.aggregate_metrics.episode_length_mean || 0);
    const minEpisodeTime = Math.min(...episodeTimes);
    const maxEpisodeTime = Math.max(...episodeTimes);
    const avgEpisodeTime = episodeTimes.reduce((sum, t) => sum + t, 0) / episodeTimes.length;

    const toolCallsPerTask = models.map(m => m.aggregate_metrics.avg_tool_calls_per_task);
    const minToolCalls = Math.min(...toolCallsPerTask);
    const maxToolCalls = Math.max(...toolCallsPerTask);

    // Aggregate errors by type across all models
    const totalErrorsByType = {};
    let totalErrors = 0;
    models.forEach(model => {
      const agg = model.aggregate_metrics;
      totalErrors += agg.total_errors || 0;
      if (agg.errors_by_type) {
        Object.entries(agg.errors_by_type).forEach(([type, count]) => {
          totalErrorsByType[type] = (totalErrorsByType[type] || 0) + count;
        });
      }
    });

    const errorBreakdown = Object.entries(totalErrorsByType)
      .map(([type, count]) => `${type}: ${count}`)
      .join(', ') || 'None';

    return `
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Avg Main Score</div>
          <div class="metric-value accent">${avgMainScore.toFixed(3)}</div>
          <div class="metric-subtitle">Levels 1-12</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Bonus Score</div>
          <div class="metric-value accent">${avgBonusScore.toFixed(3)}</div>
          <div class="metric-subtitle">Level 13</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Score Range</div>
          <div class="metric-value">${minTotalScore.toFixed(3)} - ${maxTotalScore.toFixed(3)}</div>
          <div class="metric-subtitle">Min to Max</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Success Rate</div>
          <div class="metric-value">${(avgSuccessRate * 100).toFixed(1)}%</div>
          <div class="metric-subtitle">Tasks completed</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Tool Calls</div>
          <div class="metric-value">${avgToolCalls.toFixed(1)}</div>
          <div class="metric-subtitle">Range: ${minToolCalls.toFixed(1)} - ${maxToolCalls.toFixed(1)}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Episode Time</div>
          <div class="metric-value">${avgEpisodeTime.toFixed(1)}s</div>
          <div class="metric-subtitle">Range: ${minEpisodeTime.toFixed(1)}s - ${maxEpisodeTime.toFixed(1)}s</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Hallucination</div>
          <div class="metric-value">${(avgHallucinationRate * 100).toFixed(1)}%</div>
          <div class="metric-subtitle">False techniques</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Errors</div>
          <div class="metric-value" style="color: ${totalErrors > 0 ? 'var(--red)' : 'var(--green)'};">${totalErrors}</div>
          <div class="metric-subtitle" style="font-size: 0.75rem;">${errorBreakdown}</div>
        </div>
      </div>
    `;
  }

  afterRender() {
    chartRenderer.renderLeaderboard('leaderboard-chart', dataset.getModels());
  }
}

class ModelDetailView {
  render(modelId) {
    const models = dataset.getModels();
    const model = models[modelId];

    if (!model) {
      return '<div class="loading">Model not found</div>';
    }

    const tasks = dataset.getTaskMetricsForModel(model.label);
    const agg = model.aggregate_metrics;

    return `
      <div class="container">
        <div class="page-header">
          <h1 class="page-title">${model.label}</h1>
          <p class="page-subtitle">Detailed performance analysis</p>
        </div>

        ${this._renderConfigPanel(model.config)}
        ${this._renderAggregateMetrics(agg)}

        <div class="chart-container">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h2 class="chart-title" style="margin-bottom: 0;">Task Progression (Levels 1-13)</h2>
            <div style="display: flex; gap: 16px; align-items: center;">
              <div style="display: flex; align-items: center; gap: 8px; padding: 4px 12px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 6px;">
                <span style="font-size: 0.85rem; color: var(--text-dim);">Chart type:</span>
                <button id="chart-type-line" class="chart-type-btn active" data-type="line" style="padding: 4px 12px; background: var(--accent); color: var(--bg); border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.2s;">
                  Line
                </button>
                <button id="chart-type-bar" class="chart-type-btn" data-type="bar" style="padding: 4px 12px; background: transparent; color: var(--text-dim); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; font-size: 0.85rem; transition: all 0.2s;">
                  Bar
                </button>
              </div>
              <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="compare-models-toggle" style="cursor: pointer;">
                <span style="font-size: 0.9rem; color: var(--text-dim);">Compare with other models</span>
              </label>
            </div>
          </div>
          <div id="comparison-hint" style="display: none; margin-bottom: 12px; padding: 8px 12px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 6px; font-size: 0.85rem; color: var(--text-dim);">
            💡 Click on legend items to show/hide individual models
          </div>
          <div class="chart-canvas" style="height: 300px;">
            <canvas id="task-progression-chart"></canvas>
          </div>
        </div>

        ${this._renderTaskTable(tasks)}

        <div class="chart-container">
          <h2 class="chart-title">Tool Usage Distribution</h2>
          <div class="chart-canvas" style="height: 350px;">
            <canvas id="tool-usage-chart"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  _renderConfigPanel(config) {
    // Override provider to "Anthropic" if model name starts with "claude"
    const displayProvider = config.model.toLowerCase().startsWith('claude')
      ? 'Anthropic'
      : config.provider;

    return `
      <div class="config-panel">
        <div class="config-grid">
          <div class="config-item">
            <div class="config-label">Model</div>
            <div class="config-value">${config.model}</div>
          </div>
          <div class="config-item">
            <div class="config-label">Provider</div>
            <div class="config-value">${displayProvider}</div>
          </div>
          <div class="config-item">
            <div class="config-label">Max Tool Calls</div>
            <div class="config-value">${config.max_tool_calls}</div>
          </div>
          <div class="config-item">
            <div class="config-label">Docker Sandbox</div>
            <div class="config-value">${config.use_docker ? 'Enabled' : 'Disabled'}</div>
          </div>
        </div>
      </div>
    `;
  }

  _renderAggregateMetrics(agg) {
    // Build error breakdown string
    const totalErrors = agg.total_errors || 0;
    const errorsByType = agg.errors_by_type || {};
    const errorBreakdown = Object.entries(errorsByType)
      .map(([type, count]) => `${type}: ${count}`)
      .join(', ') || 'None';

    return `
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Total Score</div>
          <div class="metric-value accent">${agg.total_score.toFixed(3)}</div>
          <div class="metric-subtitle">Main: ${agg.main_score.toFixed(3)} + Bonus: ${agg.bonus_score.toFixed(3)}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Success Rate</div>
          <div class="metric-value">${(agg.success_rate * 100).toFixed(1)}%</div>
          <div class="metric-subtitle">${agg.tasks_with_answer} / ${agg.tasks_run} tasks</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Tool Calls</div>
          <div class="metric-value">${agg.avg_tool_calls_per_task.toFixed(1)}</div>
          <div class="metric-subtitle">Per task</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Time</div>
          <div class="metric-value">${(agg.total_wall_time / 60).toFixed(1)}m</div>
          <div class="metric-subtitle">${(agg.episode_length_mean).toFixed(1)}s per task</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Hallucination Rate</div>
          <div class="metric-value">${(agg.avg_hallucination_rate * 100).toFixed(1)}%</div>
          <div class="metric-subtitle">False techniques claimed</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Tokens</div>
          <div class="metric-value">${(agg.total_tokens / 1000).toFixed(1)}K</div>
          <div class="metric-subtitle">${(agg.total_tokens / agg.tasks_run / 1000).toFixed(1)}K per task</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Errors</div>
          <div class="metric-value" style="color: ${totalErrors > 0 ? 'var(--red)' : 'var(--green)'};">${totalErrors}</div>
          <div class="metric-subtitle" style="font-size: 0.75rem;">${errorBreakdown}</div>
        </div>
      </div>
    `;
  }

  _renderTaskTable(tasks) {
    const rows = tasks.map((task, index) => {
      const level = task.task_id.match(/level(\d+)/)?.[1] || '?';
      const scoreClass = task.score >= 0.8 ? 'score-good' : task.score >= 0.5 ? 'score-medium' : 'score-poor';
      const errorBadge = task.error_occurred ? '<span class="error-badge">⚠ Error</span>' : '';

      return `
        <tr class="expandable" data-task-index="${index}">
          <td><span class="level-num">L${level}</span></td>
          <td>${task.task_id.replace(/^level\d+_/, '')}</td>
          <td><span class="score-cell ${scoreClass}">${task.score.toFixed(3)}</span></td>
          <td>${task.tool_calls_total}</td>
          <td>${task.wall_time_seconds.toFixed(1)}s</td>
          <td>${errorBadge}</td>
        </tr>
        <tr class="expanded-row" id="expanded-${index}" style="display: none;">
          <td colspan="6">
            ${this._renderExpandedContent(task)}
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="task-table-wrapper">
        <table class="task-table">
          <thead>
            <tr>
              <th>Level</th>
              <th>Task</th>
              <th>Score</th>
              <th>Tools</th>
              <th>Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderExpandedContent(task) {
    const fieldScores = Object.entries(task.field_scores || {}).map(([field, score]) => `
      <div class="field-score-item">
        <span class="label">${field}</span>
        <span class="value">${score.toFixed(3)}</span>
      </div>
    `).join('');

    // Generate unique chart ID
    const chartId = `token-chart-${task.task_id}`;

    // Check if token breakdown data exists
    const hasTokenData = task.token_breakdown &&
                         task.token_breakdown.turns &&
                         task.token_breakdown.turns.length > 0;

    return `
      <div class="expanded-content">
        <h4 style="margin-bottom: 12px; color: var(--text);">Field Scores</h4>
        <div class="field-scores">
          ${fieldScores}
        </div>

        ${hasTokenData ? `
          <!-- Token Usage Chart -->
          <div style="margin-top: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <h4 style="margin: 0; color: var(--text);">Cumulative Token Usage</h4>
              <span style="font-size: 0.75rem; color: var(--text-dim);">
                ${task.token_breakdown.turns.length} turns • ${task.tool_calls_total} tool calls • ${task.total_tokens} total tokens
              </span>
            </div>
            <div class="expanded-chart-container" style="height: 250px;">
              <canvas id="${chartId}"></canvas>
            </div>
          </div>
        ` : ''}

        ${task.error_occurred ? `
          <div style="margin-top: 16px; padding: 12px; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--red); border-radius: 6px; color: var(--text-dim); font-size: 0.85rem;">
            <strong style="color: var(--red);">Error:</strong> ${task.error_message || 'Unknown error'}
          </div>
        ` : ''}
      </div>
    `;
  }

  afterRender(modelId) {
    const model = dataset.getModels()[modelId];
    if (!model) return;

    let currentChartType = 'line';  // Track current chart type

    // Initial render with single model
    chartRenderer.renderTaskProgression('task-progression-chart', model.label, currentChartType);
    chartRenderer.renderToolUsage('tool-usage-chart', model.aggregate_metrics.tool_usage_distribution);

    // Add chart type toggle handlers
    const lineBtn = document.getElementById('chart-type-line');
    const barBtn = document.getElementById('chart-type-bar');
    const toggle = document.getElementById('compare-models-toggle');
    const hint = document.getElementById('comparison-hint');

    const updateChartTypeButtons = (type) => {
      currentChartType = type;
      if (lineBtn && barBtn) {
        if (type === 'line') {
          lineBtn.classList.add('active');
          lineBtn.style.background = 'var(--accent)';
          lineBtn.style.color = 'var(--bg)';
          lineBtn.style.border = 'none';
          barBtn.classList.remove('active');
          barBtn.style.background = 'transparent';
          barBtn.style.color = 'var(--text-dim)';
          barBtn.style.border = '1px solid var(--border)';
        } else {
          barBtn.classList.add('active');
          barBtn.style.background = 'var(--accent)';
          barBtn.style.color = 'var(--bg)';
          barBtn.style.border = 'none';
          lineBtn.classList.remove('active');
          lineBtn.style.background = 'transparent';
          lineBtn.style.color = 'var(--text-dim)';
          lineBtn.style.border = '1px solid var(--border)';
        }
      }
    };

    if (lineBtn) {
      lineBtn.addEventListener('click', () => {
        updateChartTypeButtons('line');
        if (toggle && toggle.checked) {
          const allModels = dataset.getModels();
          chartRenderer.renderTaskProgressionComparison('task-progression-chart', allModels, parseInt(modelId), 'line');
        } else {
          chartRenderer.renderTaskProgression('task-progression-chart', model.label, 'line');
        }
      });
    }

    if (barBtn) {
      barBtn.addEventListener('click', () => {
        updateChartTypeButtons('bar');
        if (toggle && toggle.checked) {
          const allModels = dataset.getModels();
          chartRenderer.renderTaskProgressionComparison('task-progression-chart', allModels, parseInt(modelId), 'bar');
        } else {
          chartRenderer.renderTaskProgression('task-progression-chart', model.label, 'bar');
        }
      });
    }

    // Add toggle handler for comparison mode
    if (toggle) {
      toggle.addEventListener('change', (e) => {
        if (e.target.checked) {
          // Render comparison mode with all models
          const allModels = dataset.getModels();
          chartRenderer.renderTaskProgressionComparison('task-progression-chart', allModels, parseInt(modelId), currentChartType);
          if (hint) hint.style.display = 'block';
        } else {
          // Render single model mode
          chartRenderer.renderTaskProgression('task-progression-chart', model.label, currentChartType);
          if (hint) hint.style.display = 'none';
        }
      });
    }

    // Add click handlers for expandable rows
    document.querySelectorAll('.task-table .expandable').forEach(row => {
      row.addEventListener('click', () => {
        const taskIndex = row.dataset.taskIndex;
        const expandedRow = document.getElementById(`expanded-${taskIndex}`);
        const isVisible = expandedRow.style.display !== 'none';

        if (!isVisible) {
          // Row is being opened - show and render chart
          expandedRow.style.display = 'table-row';

          const task = model.task_metrics[taskIndex];

          // Render token chart if data available
          if (task.token_breakdown) {
            const chartId = `token-chart-${task.task_id}`;
            setTimeout(() => {
              chartRenderer.renderCumulativeTokens(chartId, task);
            }, 50);
          }
        } else {
          // Row is being closed - hide and destroy chart
          expandedRow.style.display = 'none';
          const task = model.task_metrics[taskIndex];
          chartRenderer.destroy(`token-chart-${task.task_id}`);
        }
      });
    });
  }
}

class ComparisonView {
  render() {
    const models = dataset.getModels();
    if (models.length === 0) {
      return '<div class="loading">No models to compare</div>';
    }

    return `
      <div class="container">
        <div class="page-header">
          <h1 class="page-title">Model Comparison</h1>
          <p class="page-subtitle">Side-by-side performance analysis</p>
        </div>

        ${this._renderModelCards(models)}

        <div class="chart-container">
          <h2 class="chart-title">Multi-Model Task Progression</h2>
          <div class="chart-canvas" style="height: 400px;">
            <canvas id="multi-model-chart"></canvas>
          </div>
        </div>

        ${this._renderHeatmap(models)}
      </div>
    `;
  }

  _renderModelCards(models) {
    const cards = models.map((model, index) => {
      const agg = model.aggregate_metrics;
      return `
        <div class="model-card" onclick="router.navigate('model/${index}')">
          <div class="model-card-title">${model.label}</div>
          <div class="model-card-score">${agg.total_score.toFixed(3)}</div>
          <div class="model-card-meta">
            ${(agg.success_rate * 100).toFixed(0)}% success · ${agg.avg_tool_calls_per_task.toFixed(1)} tools/task
          </div>
        </div>
      `;
    }).join('');

    return `<div class="model-comparison-grid">${cards}</div>`;
  }

  _renderHeatmap(models) {
    const taskIds = dataset.getTasksByLevel();
    const modelLabels = models.map(m => {
      // Abbreviate model labels for heatmap headers
      const parts = m.label.split('(')[0].trim().split(' ');
      return parts.slice(0, 2).join(' ');
    });

    // Build grid
    const headers = [''].concat(modelLabels).map(label =>
      `<div class="heatmap-cell header">${label}</div>`
    ).join('');

    const rows = taskIds.map(taskId => {
      const level = taskId.match(/level(\d+)/)?.[1] || '?';
      const cells = [`<div class="heatmap-cell label">L${level}</div>`];

      models.forEach((model, modelIndex) => {
        const task = model.task_metrics.find(t => t.task_id === taskId);
        const score = task ? task.score : 0;
        const scoreLevel = Math.round(score * 10);
        cells.push(`
          <div class="heatmap-cell data" data-score="${scoreLevel}"
               onclick="router.navigate('model/${modelIndex}')"
               title="${model.label}\n${taskId}\nScore: ${score.toFixed(3)}">
            ${score.toFixed(2)}
          </div>
        `);
      });

      return `<div class="heatmap-row">${cells.join('')}</div>`;
    }).join('');

    const gridColumns = `repeat(${models.length + 1}, minmax(80px, 1fr))`;

    return `
      <div class="chart-container">
        <h2 class="chart-title">Score Heatmap (Tasks × Models)</h2>
        <div class="heatmap-container">
          <div class="heatmap" style="grid-template-columns: ${gridColumns};">
            ${headers}
            ${rows}
          </div>
        </div>
      </div>
    `;
  }

  afterRender() {
    chartRenderer.renderMultiModelComparison('multi-model-chart', dataset.getModels());
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Router
// ═══════════════════════════════════════════════════════════════════════════

class Router {
  constructor() {
    this.routes = {
      'dashboard': new DashboardView(),
      'model': new ModelDetailView(),
      'compare': new ComparisonView()
    };
    this.currentView = null;

    window.addEventListener('hashchange', () => this.handleRoute());
  }

  init() {
    this.handleRoute();
    this.bindNavigation();
    this.populateModelSelector();
  }

  handleRoute() {
    const hash = window.location.hash.slice(1) || 'dashboard';
    const [route, ...params] = hash.split('/');

    chartRenderer.destroyAll();

    const view = this.routes[route];
    if (!view) {
      this.navigate('dashboard');
      return;
    }

    const appContainer = document.getElementById('app');
    if (!appContainer) return;

    this.currentView = view;
    appContainer.innerHTML = view.render(...params);

    if (view.afterRender) {
      // Delay to ensure DOM is ready
      setTimeout(() => view.afterRender(...params), 50);
    }

    this.updateActiveTab(route);
  }

  navigate(path) {
    window.location.hash = path;
  }

  updateActiveTab(route) {
    document.querySelectorAll('.nav-tabs .tab').forEach(tab => {
      const href = tab.getAttribute('href').slice(1);
      const isActive = href === route || (href === 'dashboard' && !route);
      tab.classList.toggle('active', isActive);
    });
  }

  bindNavigation() {
    document.querySelectorAll('.nav-tabs .tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        this.navigate(tab.getAttribute('href').slice(1));
      });
    });
  }

  populateModelSelector() {
    const selector = document.getElementById('model-selector');
    if (!selector) return;

    const models = dataset.getModels();
    selector.innerHTML = models.map((model, index) =>
      `<option value="${index}">${model.label}</option>`
    ).join('');

    selector.addEventListener('change', (e) => {
      this.navigate(`model/${e.target.value}`);
    });

    // Update selector when route changes
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.slice(1);
      const match = hash.match(/^model\/(\d+)$/);
      if (match) {
        selector.value = match[1];
      }
    });
  }
}

const router = new Router();

// ═══════════════════════════════════════════════════════════════════════════
// Application Entry Point
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  const loaded = dataset.loadFromEmbedded();
  if (!loaded) {
    document.getElementById('app').innerHTML =
      '<div class="loading">Failed to load benchmark data</div>';
    return;
  }

  console.log(`Loaded ${dataset.getModels().length} model configurations`);
  router.init();
});
