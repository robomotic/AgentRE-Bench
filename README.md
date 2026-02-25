# AgentRE-Bench

A benchmark for evaluating LLM agents on **long-horizon reverse engineering tasks** with deterministic scoring.

> **Platform:** Linux/Unix (ELF x86-64). **Partial macOS support** (9/13 MACH-O binaries - see [MACHO_BUILD_NOTES.md](MACHO_BUILD_NOTES.md)). Windows PE support planned for future release.

AgentRE-Bench gives an LLM agent a compiled ELF binary and a set of Linux static analysis tools (strings, objdump, readelf, etc.), then measures how well it can identify C2 infrastructure, encoding schemes, anti-analysis techniques, and communication protocols — all without human guidance.

## Why This Benchmark?

### Why Synthetic?

All 13 binaries are compiled from purpose-built C sources with known ground truths. This gives us:

- **Deterministic judging** — every field has an exact expected answer, no ambiguity
- **Controlled difficulty progression** — from plaintext TCP shells (level 1) to metamorphic droppers with RC4 encryption (level 13)
- **Reproducibility** — anyone can compile identical binaries and verify scores

Real malware would require subjective expert judgment and introduce licensing, ethics, and reproducibility issues. Synthetic samples eliminate all of that while testing the same analytical capabilities.

### Why Agentic?

Traditional RE benchmarks ask a model a question and check the answer. AgentRE-Bench requires the agent to:

- **Plan** which tools to use and in what order
- **Interpret** raw tool output (hex dumps, disassembly, symbol tables)
- **Synthesize** findings across multiple tool calls into a structured analysis
- **Manage a budget** of 25 tool calls — wasting calls on redundant queries means running out before finding the answer

This tests reasoning, tool selection, and information synthesis — not just pattern matching.

### Why Long-Horizon?

Simple RE questions ("What architecture is this binary?") don't differentiate models. The hard problems require chains of 10-25 tool calls where each call's output informs the next decision. Level 13 requires the agent to:

1. Identify encrypted strings via entropy analysis
2. Locate the encryption key in the binary
3. Determine the key storage mechanism (XOR mask)
4. Decode the actual C2 URL
5. Identify 18 distinct techniques across anti-debugging, process injection, and network evasion

This is where agent capability differences become visible.

### Why Deterministic Judging?

Every agent answer is scored against a fixed ground truth with weighted fields and Jaccard overlap for set comparisons. There is no LLM-as-judge, no subjective rubric, no human grader variance. The same answer always produces the same score.

Hallucinations are penalized: claiming a technique not present in the binary costs -0.05 per false claim. This means models can't game scores by guessing everything.

## Task Difficulty Progression

| Level | Task | Techniques | Difficulty |
|-------|------|-----------|------------|
| 1 | TCP Reverse Shell | Plaintext C2, socket connect, dup2, execve | Trivial |
| 2 | XOR Encoded Strings | XOR encoding, string obfuscation | Easy |
| 3 | Anti-Debugging Shell | ptrace detection, timing checks | Easy |
| 4 | Polymorphic Shell | Self-modifying code, runtime decryption | Medium |
| 5 | Multistage Shell | Staged payload delivery | Medium |
| 6 | ICMP Covert Channel | ICMP protocol C2, covert channel | Medium |
| 7 | DNS Tunnel Shell | DNS-based C2 tunneling | Medium |
| 8 | Process Hollowing | Process injection, memory manipulation | Hard |
| 9 | Shared Object Injection | .so injection, dlopen/dlsym | Hard |
| 10 | AES Encrypted Shell | AES encryption, key recovery | Hard |
| 11 | Fork Bomb Shell | Process evasion, fork techniques | Hard |
| 12 | JIT Compiled Shellcode | Runtime code generation, JIT | Very Hard |
| 13 | Metamorphic Dropper | RC4 encryption, anti-analysis, metamorphic code | Bonus |

Levels 1-12 are **standard tasks** (averaged to 1.0 pt max). Level 13 is a **bonus task** with a deeper rubric (1.0 pt max). **Total possible: 2.0 points.**

## Scoring Model

### Standard Levels (1-12)

Each task is scored across 5 weighted fields:

| Field | Weight | Scoring |
|-------|--------|---------|
| `decoded_c2` | 0.40 | Exact match = 1.0, host-only match = 0.5 |
| `techniques` | 0.30 | Jaccard overlap between predicted and ground truth sets |
| `file_type` | 0.10 | Exact match (case-insensitive) |
| `encoded_strings` | 0.10 | Exact match (boolean) |
| `c2_protocol` | 0.10 | Exact match (case-insensitive) |

**Hallucination penalty**: -0.05 per technique claimed but not in ground truth.

### Bonus Level (13)

10 weighted fields including encryption algorithm, key, key storage mechanism, decoded strings, and anti-analysis techniques. Lighter hallucination penalty (-0.03) given the larger technique set.

### Aggregate Scoring

```
Main Score  = average(level_1_score, ..., level_12_score)    # 0.0 - 1.0
Bonus Score = level_13_score                                  # 0.0 - 1.0
Total Score = Main Score + Bonus Score                        # 0.0 - 2.0
```

## Benchmark Metrics

Beyond correctness, AgentRE-Bench records research-grade metrics for every task:

**Per-Task Metrics:**

| Metric | Description |
|--------|-------------|
| `score` | Final weighted score after hallucination penalty |
| `field_scores` | Per-field breakdown (decoded_c2, techniques, etc.) |
| `tool_calls_total` | Number of tool calls used |
| `tool_calls_by_type` | Distribution across tool types |
| `redundant_tool_calls` | Identical tool calls repeated (same name + args) |
| `invalid_tool_calls` | Tool calls that returned errors |
| `invalid_json_attempts` | Times the agent responded with text instead of a tool call |
| `hallucinated_techniques` | Techniques claimed but not in ground truth |
| `missing_techniques` | Ground truth techniques the agent failed to identify |
| `steps_to_answer` | Tool calls before submitting final answer |
| `max_steps_hit` | Whether the agent exhausted its 25-call budget |
| `wall_time_seconds` | End-to-end wall clock time |
| `input_tokens` / `output_tokens` | Token consumption |
| `error_occurred` | Whether an error occurred during task execution |
| `error_type` | Type of error: `context_overflow`, `timeout`, `http_error`, or `other` |
| `error_message` | Human-readable error description with extracted details |
| `http_status_code` | HTTP status code if applicable (0 otherwise) |

**Aggregate Metrics:**

| Metric | Description |
|--------|-------------|
| `success_rate` | Fraction of tasks with a valid submitted answer |
| `avg_tool_calls_per_task` | Mean tool calls across all tasks |
| `avg_tool_calls_per_success` | Mean tool calls for tasks that got an answer |
| `avg_hallucination_rate` | Mean hallucinated technique count per task |
| `episode_length_*` | Wall time distribution (min/max/mean/median) |
| `tool_usage_distribution` | Which tools models prefer across all tasks |
| `max_steps_hit_count` | How often agents exhaust their budget |
| `total_errors` | Total number of tasks with errors |
| `errors_by_type` | Count of each error type (`context_overflow`, `timeout`, etc.) |
| `errors_by_http_status` | Count of HTTP errors by status code (`400`, `500`, etc.) |
| `context_overflow_errors` | Quick count of context window overflow errors |
| `timeout_errors` | Quick count of timeout errors |

**Error Tracking:** Every task failure is automatically classified and logged with detailed error information, including context overflow detection (with token counts), timeout identification, and HTTP error codes. This enables precise debugging and optimization recommendations.

These metrics enable **failure taxonomy** — categorizing failures into:
- Byte-level reasoning failure
- Control-flow misinterpretation
- API hallucination
- Tool misuse
- Early termination
- JSON format violation

## Architecture

```
run_benchmark.py              CLI entry point
  |
  v
harness/
  config.py                   Configuration (dataclass, .env loading)
  runner.py                   Orchestrator (load tasks, run agent, score, report)
  agent.py                    Provider-agnostic agent loop (tool calling)
  tools.py                    Tool schemas + ToolExecutor dispatch
  sandbox.py                  PathValidator + DockerRunner / SubprocessRunner
  metrics.py                  TaskMetrics + AggregateMetrics collection
  providers/
    base.py                   Abstract AgentProvider + ProviderResponse
    anthropic.py              Claude (raw HTTP to Messages API)
    openai_provider.py        GPT (raw HTTP to Chat Completions API)
    gemini.py                 Gemini (raw HTTP to GenerativeAI API)
    deepseek.py               DeepSeek (extends OpenAI-compatible provider)

scorer.py                     Deterministic scorer (standalone + used by harness)
tasks.json                    Task manifest (13 entries)
build_binaries.sh             Docker cross-compile script
Dockerfile.tools              Sandboxed tool execution image
```

**Zero Python dependencies.** All LLM provider calls use Python's built-in `urllib.request`. No SDKs required.

### Tool Sandbox

All tools execute inside Docker containers with strict isolation:

```
docker run --rm --platform linux/amd64 \
  --network=none --read-only --memory=512m --cpus=1 \
  -v binaries:/workspace:ro \
  agentre-bench-tools:latest <command>
```

- `--network=none` — no network access
- `--read-only` — immutable filesystem
- `--memory=512m` — memory cap
- Workspace mounted read-only

### Available Tools

Tools are conditionally provided based on binary format:

| Tool | Universal | ELF | MACHO | PE | Description |
|------|-----------|-----|-------|----|----|
| `file` | ✓ | ✓ | ✓ | ✓ | File type identification |
| `strings` | ✓ | ✓ | ✓ | ✓ | Extract printable strings |
| `hexdump` | ✓ | ✓ | ✓ | ✓ | Hex + ASCII dump |
| `xxd` | ✓ | ✓ | ✓ | ✓ | Hex dump (alternative) |
| `entropy` | ✓ | ✓ | ✓ | ✓ | Shannon entropy detection |
| `readelf` | | ✓ | | | ELF headers, sections, symbols |
| `objdump` | | ✓ | | | Disassembly, symbol tables |
| `nm` | | ✓ | ✓ | | Symbol listing |
| `pefile` | | | | ✓ | PE headers, imports, exports |

Plus `final_answer` — a structured submission tool the agent calls when done.

**Platform Support:**
- **ELF x86-64 binaries (Linux/Unix)** - fully supported with 13 benchmark tasks
- **MACHO binaries (macOS)** - experimental support with universal tools + nm
- **Windows PE binaries** - tooling ready (pefile), benchmark tasks planned

## Setup

### Prerequisites

- Python 3.10+
- **Linux x86-64**: gcc, binutils, file, xxd, python3 (for local builds and `--no-docker` mode)
- **macOS**: Docker (for cross-compilation and sandboxed tool execution)

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/AgentRE-Bench.git
cd AgentRE-Bench

# Create .env with your API key(s)
cp .env.example .env
# Edit .env — add at least one provider key
# Optional: add Langfuse keys to enable task/LLM/tool tracing
# Optional: configure OPENAI_BASE_URL for custom/local LLM endpoints
```

### 2. Build Binaries

```bash
chmod +x build_binaries.sh
./build_binaries.sh
```

On **Linux x86-64**: uses local gcc directly (install with `apt install gcc` if needed — no Docker required).
On **macOS / Apple Silicon**: uses Docker with `--platform linux/amd64` to cross-compile.

### 3. Build Tools Image

```bash
docker build --platform linux/amd64 -t agentre-bench-tools:latest -f Dockerfile.tools .
```

### 4. Run

```bash
# Single task with verbose output
python run_benchmark.py --task level1_TCPServer -v

# Full benchmark
python run_benchmark.py --all

# Different providers
python run_benchmark.py --all --provider anthropic --model claude-opus-4-6
python run_benchmark.py --all --provider openai --model gpt-4o
python run_benchmark.py --all --provider openrouter --model openai/gpt-4o
python run_benchmark.py --all --provider gemini --model gemini-2.0-flash
python run_benchmark.py --all --provider deepseek --model deepseek-chat

# OpenRouter note: requests include HTTP-Referer and X-Title headers automatically.

# Custom output directory
python run_benchmark.py --all --report results/opus_run1/
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--all` | | Run all 13 tasks |
| `--task ID` | | Run a single task by ID |
| `--provider` | `anthropic` | `anthropic`, `openai`, `openrouter`, `gemini`, `deepseek` |
| `--model` | per-provider | Model name |
| `--api-key` | from .env | API key override |
| `--openai-base-url` | from .env | Custom OpenAI API base URL |
| `--report DIR` | `results/` | Output directory |
| `--max-tool-calls` | `25` | Tool call budget per task |
| `--max-tokens` | `4096` | Max tokens per LLM response |
| `--no-docker` | | Run tools via local subprocess |
| `-v` | | Verbose: show agent reasoning + tool I/O live |

### Optional: Custom OpenAI Base URL

For connecting to OpenAI-compatible endpoints (local LLMs, custom proxies, or AWS Bedrock):

```bash
# In .env file
OPENAI_BASE_URL=http://localhost:1234/v1
IS_BEDROCK_ANTHROPIC=true  # Only if endpoint returns finish_reason="stop" with tool calls
```

Or via command line:

```bash
python run_benchmark.py --all --provider openai --model your-model \
  --openai-base-url http://localhost:1234/v1
```

**IS_BEDROCK_ANTHROPIC flag**: Some OpenAI-compatible endpoints (like AWS Bedrock with Anthropic models) return `finish_reason="stop"` even when tool calls are present. Set this to `true` to enable compatibility mode. Standard OpenAI endpoints should leave this `false` (default).

**Common use cases:**
- **LM Studio**: `http://localhost:1234/v1`
- **Ollama**: `http://localhost:11434/v1`
- **vLLM server**: `http://your-server:8000/v1`
- **AWS Bedrock (Anthropic)**: Set base URL + `IS_BEDROCK_ANTHROPIC=true`

### Optional: Langfuse Logging

Langfuse logging is automatically enabled when both of these are present in `.env` or your environment:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`

Optional:

- `LANGFUSE_HOST` (default: `https://cloud.langfuse.com`)

When enabled, the benchmark logs task-level traces plus model-call and tool-call spans, including prompts and tool I/O metadata.

## Output

```
results/
  agent_outputs/              Raw agent JSON answers (one per task)
  transcripts/                Per-task scoring, metrics, and full message logs
  benchmark_report.json       Aggregate report with all metrics and scores
```

## Standalone Scorer

The scorer works independently of the agent harness:

```bash
# Single sample
python scorer.py -g ground_truths/level1_TCPServer.json \
                 -a agent_outputs/level1_TCPServer.json

# Batch
python scorer.py -G ground_truths/ -A agent_outputs/ -r report.json
```

## Querying Error Information

The benchmark automatically tracks and classifies all errors. Query error information from `benchmark_report.json`:

```bash
# View aggregate error statistics
jq '.aggregate_metrics | {total_errors, errors_by_type, context_overflow_errors, timeout_errors}' benchmark_report.json

# Find all tasks that had errors
jq '.task_metrics[] | select(.error_occurred == true) | {task_id, error_type, error_message}' benchmark_report.json

# List tasks with context overflow errors
jq '.task_metrics[] | select(.error_type == "context_overflow") | {task_id, error_message, tool_calls_total}' benchmark_report.json

# Check HTTP error breakdown
jq '.aggregate_metrics.errors_by_http_status' benchmark_report.json
```

**Error types tracked:**
- `context_overflow` — Prompt exceeds model's context window (extracts token count)
- `timeout` — Request timed out
- `http_error` — HTTP error with extracted status code
- `other` — Unclassified errors

See [ERROR_TRACKING.md](ERROR_TRACKING.md) for detailed documentation (if available in local setup).

## Known Limitations

- **Static analysis only** — no dynamic execution, debugging, or sandboxed runtime. Tests static RE reasoning specifically.
- **Synthetic samples** — designed to test real RE skills, but production malware has additional complexity (packers, anti-VM, polymorphism at scale) not fully represented.
- **Fixed tool set** — agents can't install tools, write scripts, or use Ghidra/IDA. Standardizes evaluation but limits agent creativity.
- **Single-agent** — no multi-agent collaboration or human-in-the-loop.
- **Token cost** — a full 13-task run uses ~5-10M tokens on frontier models. Budget accordingly.
- **Platform support** — primary focus is ELF x86-64 (Linux/Unix) with 13 benchmark tasks. MACHO support is experimental (9/13 binaries buildable, see [MACHO_BUILD_NOTES.md](MACHO_BUILD_NOTES.md)). Windows PE tooling (pefile) is available but benchmark tasks are not yet developed. No ARM or MIPS samples yet.

## Roadmap

- **Failure taxonomy** — systematic categorization of failure modes across models
- **Baseline comparisons** — published results for Claude, GPT, Gemini, and open models
- **Dynamic analysis tools** — strace, ltrace, sandboxed execution
- **Windows PE support** — Windows binaries, ARM targets, packed samples
- **Multi-turn refinement** — tasks requiring iterative hypothesis refinement
- **Public leaderboard** — model comparison across providers and versions

## License

MIT
