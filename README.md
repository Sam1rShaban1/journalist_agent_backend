# 📰 AI Journalist Studio

**AI Journalist Studio** is a persistent, multi-agent system designed for deep investigative research and professional news writing.

Unlike standard AI scripts that reset every time, this system uses a **local SQLite database** to store research context ("Dossiers"). This allows you to **Research Once** (expensive/slow) and **Write Infinite Drafts** (cheap/fast) without losing context or paying for redundant searches.

## 🚀 Key Features

*   **🧠 Persistent Memory:** Research is saved to `journalist_studio.db`. You can close the app, come back days later, and generate a new article instantly.
*   **🔍 Deep-Dive Tools:** Agents are equipped with:
    *   **Serper:** For broad Google searches.
    *   **PDF Search:** To read official government reports/contracts.
    *   **YouTube Search:** To find direct quotes from political speeches/interviews.
    *   **Website Search:** To scrape specific news archives.
*   **⚡ Cost-Efficient Architecture:**
    *   **Smart Brain:** Uses **Google Gemini 2.0 Flash** (via OpenRouter) for complex reasoning.
    *   **Fast Hunter:** Uses **Grok 4.1** or **Llama 3.3** (via OpenRouter) for data gathering.
    *   **Free RAG:** Uses **Google Gemini Embeddings** to power the search tools (saving OpenAI costs).
*   **🔄 Iterative Workflow:**
    *   **Dig Deeper:** Find missing info (e.g., "Find the 2023 budget") and update the existing dossier.
    *   **History:** View every draft you've ever written for a specific topic.

## 📂 Project Structure

```text
journalist_crew/
├── .env                     # API Keys (OpenRouter, Google, Serper)
├── journalist_studio.db     # Local Database (Auto-created on first run)
├── pyproject.toml           # Dependencies managed by uv
├── src/
│   └── journalist_crew/
│       ├── config/
│       │   ├── agents.yaml  # Agent Roles & Backstories (The "Persona")
│       │   └── tasks.yaml   # Detailed Task Instructions (The "SOP")
│       ├── tools/
│       │   ├── __init__.py  # Tool package initialization
│       │   └── custom_tools.py # Logic for custom tool implementations
│       ├── crew.py          # The Brain (LLM setup, Tool initialization, Logic)
│       ├── main.py          # The Interface (CLI Menu)
│       ├── models.py        # Data Structures (Pydantic Schema)
│       └── storage.py       # Database Layer (SQLite logic)
```

## 🛠️ Prerequisites

*   **Python 3.13.5+**
*   **uv** (Python package manager - fast & efficient)

## 📦 Installation & Setup

1.  **Install uv** (if you haven't already):
    ```powershell
    pip install uv
    ```

2.  **Install Dependencies:**
    Navigate to the project root and let `uv` handle the virtual environment and packages:
    ```powershell
    uv sync
    # Or manually:
    uv add crewai[tools] duckduckgo-search langdetect pydantic chromadb
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the root directory (`journalist_crew/.env`) and add your keys:

    ```ini
    # 1. OpenRouter (For Chat/Reasoning)
    # Get key: https://openrouter.ai/keys
    OPENROUTER_API_KEY=sk-or-v1-your-key-here

    # 2. Google AI Studio (For Embeddings & RAG - FREE)
    # Get key: https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY=AIzaSy-your-google-key-here

    # 3. Serper (For Google Search Results)
    # Get key: https://serper.dev/
    SERPER_API_KEY=your-serper-key
    ```

## 🏃‍♂️ How to Run

Use `uv run` to execute the script inside the virtual environment automatically:

```powershell
uv run src/journalist_crew/main.py
```

### The Workflow

1.  **Main Menu:**
    The system checks `journalist_studio.db`.
    *   If previous research exists, it lists topics by ID/Date.
    *   To start fresh, type a **New Topic Name** (e.g., *"Corridor 8"*).

2.  **Phase 1: Research (The "Hunter"):**
    *   Runs only if the topic is new or if you choose "Dig Deeper".
    *   Agents scrape the web, PDFs, and Videos.
    *   Findings are compiled into a structured Dossier and saved to SQLite.

3.  **Phase 2: Writing (The "Editor"):**
    *   Select **Option 1: Write Draft**.
    *   Enter instructions: *"Write in Albanian, focus on the corruption angle."*
    *   The Writer Agent generates the article using the *saved* research (0 latency).
    *   The article is saved to the `articles` table in the database.

## 🧩 Customization

### Changing the "Journalist Persona"
Edit `src/journalist_crew/config/agents.yaml`.
*   Currently set to **"Balkan/North Macedonia Focus"**.
*   Change the `role` and `backstory` to fit your specific niche (e.g., Tech, Finance, Sports).

### Changing the Article Format
Edit `src/journalist_crew/config/tasks.yaml`.
*   Look for `write_task`.
*   Modify the **MANDATORY STRUCTURE** section to change how the final output looks.

### Changing Models
Edit `src/journalist_crew/crew.py`.
*   Look for `self.smart_llm` and `self.fast_llm` inside the `__init__` method.
*   You can swap the OpenRouter model strings (e.g., to `anthropic/claude-3.5-sonnet`) if you have credits.

## 🛡️ Troubleshooting

*   **`RateLimitError / 429`**: The free models on OpenRouter are busy. The system uses `max_retries=3`, but if it persists, wait a minute.
*   **`WinError 10054`**: The model generated too much text and the network timed out. The current config has `timeout=300` (5 mins) to prevent this.
*   **`ValueError: OpenAI Key not found`**: Ensure `GOOGLE_API_KEY` is set in `.env`. The tools are configured to use Google Embeddings to avoid OpenAI costs.