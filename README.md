# 🚀 Axiom – AI‑Driven Web Data Analysis System

**Axiom** is a command‑line tool that turns a natural‑language question and a URL into a complete data analysis report – with **15+ insights** and **labelled visualisations** – automatically.

> *“From raw data to actionable insights with one command.”*

---

## ✨ Key Features

- 🔍 **Smart Scraping** – Works with **Direct HTTP** (simple sites) and **Bright Data** (anti‑bot bypass, e.g., Amazon).  
- 🧠 **AI Query Parsing** – Gemini 3.6 Flash reads your question and decides what to analyse.  
- 📊 **Self‑Healing Code** – Gemini writes Python analysis code; if it fails, it automatically fixes itself (up to 3 retries).  
- 🔒 **Privacy First** – Raw data **never leaves your machine** – the sandbox runs with `--network none`; only summaries go to the LLM.  
- 📈 ** Insights + Charts** – The final report contains a rich set of statistics and labelled graphs.  
- ⏱️ **Smart Estimation** – For Bright Data, it samples the scrape rate and fetches exactly the number of records you ask for – saving credits.  
- 🎛️ **Component Toggles** – Run only the parts you need (`Sc` = Scraper, `Db` = Database, `Sb` = Sandbox, `Ai` = AI).

---

## 🧠 How It Works

```text
User Query + URL
       ↓
Orchestrator (main.py)
       ↓
┌─────────────────────────────────────────────────┐
│ 1. Query Parsing (Gemini)                       │
│ 2. Scraping (Direct / Bright Data)              │
│ 3. Injection Defense (sanitises HTML)           │
│ 4. Extraction & Storage (DuckDB)                │
│ 5. Profiling (schema, stats, correlations)      │
│ 6. Audit Engine (deterministic)                 │
│ 7. Visualisation Planning (chart specs)         │
│ 8. Code Generation (Gemini writes Python)       │
│ 9. Sandbox Execution (Docker, --network none)   │
│10. Report Generation (Gemini writes markdown)   │
└─────────────────────────────────────────────────┘
       ↓
results/report.md  +  insight_*.png  +  analysis_output.txt
```

---

## 📦 Installation

### Prerequisites

- **Python 3.11+** (with pip)
- **Node.js** (for Bright Data CLI via `npx`)
- **Docker Desktop** (for sandbox execution)
- Bright Data API token (optional, but required for Amazon)
- Gemini API key (for AI features)

### Steps

1. **Clone the repository**

```bash
git clone https://github.com/KRISHNA111311/Axiom---Ai--automated-web-data-analytical-agent.git
cd Axiom
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# or
venv\Scripts\activate           # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Build the Docker image** (for sandbox execution)

```bash
docker build -t ai-analysis-sandbox .
```

5. **Create a `.env` file** with your API keys:

```env
GOOGLE_API_KEY=your_gemini_api_key
BRIGHTDATA_API_TOKEN=your_brightdata_token   # optional
```

6. **Update the model** (optional) – edit `config.py` if you want a different Gemini model (default is `gemini-3.6-flash`).

---

## 🚀 Usage

### Basic Command

```bash
python main.py --query "your question" --target "URL" [options]
```

### Example: Amazon India (Bright Data)

```bash
python main.py --query "Analyze the relationship between the price of smartphones and their customer ratings on Amazon India. Show the distribution of prices and how ratings vary across different price ranges, with labelled visualizations." --target "https://www.amazon.in/All-Mobile-Phones/s?k=All+Mobile+Phones&page=1" --components ScDbSbAi --mode autonomous --scraper brightdata --target-records 20
```

### Example: Books.toscrape.com (Direct HTTP)

```bash
python main.py --query "analyze books and tell me the relationship between category and price with visualizations" --target books.toscrape.com --components ScDbSbAi --mode autonomous --scraper direct --max-pages 1 --fields "book_name,price,category"
```

---

## ⚙️ Command‑Line Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--query` | Natural‑language question | required |
| `--target` | Target URL or domain | `books.toscrape.com` |
| `--components` | Component toggles: `Sc` (Scraper), `Db` (Database), `Sb` (Sandbox), `Ai` (AI) | `ScDbSbAi` |
| `--mode` | `autonomous`, `assisted`, `semi_autonomous`, `interactive` | `autonomous` |
| `--scraper` | `direct` or `brightdata` | `direct` |
| `--output-dir` | Output directory | `results` |
| `--max-retries` | Self‑healing retries | `3` |
| `--max-pages` | Max pages per category (direct scraper) | `1` |
| `--target-records` | Exact number of records (estimation mode) | – |
| `--fields` | Comma‑separated field names (auto‑detected if omitted) | – |
| `--interactive` | Pause at each stage for review/backtracking | `False` |
| `--test-injection` | Run the injection defense test harness | `False` |

---

## 📁 Output

All outputs are saved in the `--output-dir` (default: `results/`).

| File | Description |
|------|-------------|
| `report.md` | Final markdown report with **15+ insights** and embedded labelled charts. |
| `insight_*.png` | 15+ visualisations (one per insight). |
| `analysis_output.txt` | Raw stdout from the sandbox (statistics, etc.). |
| `data.duckdb` | DuckDB database of the ingested records. |
| `snapshot.parquet` | Read‑only Parquet snapshot used by the sandbox. |
| `failure_report.md` | Generated if the pipeline fails after all retries. |

### Example Insight from `report.md`

```markdown
## Insight 1: Highest Average Rating Observed at Specific Price Point
The analysis indicates that the highest average rating observed across the evaluated price points is 3.93, occurring at price point 80.

- Supporting visualization: bar_chart.png
```

Every insight is accompanied by a labelled chart – proof of the analysis.

---

## 🛠️ Configuration

- **Model** – change `DEFAULT_MODEL` in `config.py` to any supported Gemini model (e.g., `gemini-3.6-flash`).
- **Sample Durations** – edit `sample_durations` in `scraper_adapters.py` or pass via `config.sample_durations` to adjust the estimation phase.
- **Number of Insights** – modify the prompt in `execution/code_synthesis.py` to request a different number; the fallback script already generates 15.

---

## 🔒 Privacy & Security

- **No raw data** is sent to the LLM – only schema, summary statistics, and a 5‑row sample.
- **Privacy Broker** (M4) ensures that raw rows never leave the DuckDB process.
- **Docker sandbox** runs with `--network none` – zero internet access.
- **Injection Defense** (M2) scans scraped HTML for prompt‑injection patterns and neutralises them.

---

## 🐞 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Bright Data returns 0 records** | Increase `sample_durations`; ensure the collector is active; try a different URL. |
| **Gemini quota exceeded (429)** | Wait for reset, or use a paid key. Fallback scripts will still generate some output. |
| **Sandbox cannot find `/data/snapshot.parquet`** | Ensure `provision_sandbox_view` returns an absolute path; rebuild the Docker image. |
| **`npx` not found** | Install Node.js and add it to your PATH; on Windows, ensure `npx.cmd` is available. |
| **Threading `ValueError: I/O operation on closed file`** | Fixed in the latest `scraper_adapters.py` – update your file. |

---

## 🤝 Contributing

We welcome issues and pull requests. Please ensure your code is clean and well‑documented.

---


## 🌟 Acknowledgements

- Built with **Bright Data** for reliable scraping.
- Powered by **Gemini 3.6 Flash** for intelligent code generation and reasoning.
- Uses **DuckDB**, **Docker**, and **pandas**.

---

**Start your analysis today – one command is all it takes.** 🚀
