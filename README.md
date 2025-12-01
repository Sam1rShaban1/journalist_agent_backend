# 📰 AI Journalist Studio (Database-Native)

**AI Journalist Studio** is a sophisticated, persistent multi-agent system designed for deep investigative research and professional news writing.

Unlike standard "one-shot" AI scripts, this system separates **Research** from **Writing**. It gathers deep context, stores it in a structured **SQLite database**, and allows you to generate infinite article drafts, revisions, and angles from a single research session without re-running expensive searches.

## 🚀 Key Features

*   **🧠 Persistent Memory (SQLite):** Research findings are saved as structured "Dossiers" (JSON/Pydantic) in a local database. You can close the app and resume research days later.
*   **🔍 Deep-Dive Research Tools:** Agents don't just read summaries. They use:
    *   **PDF Search:** To read official government reports/contracts.
    *   **YouTube Search:** To find direct quotes from speeches and interviews.
    *   **Website Search:** To scrape specific news archives.
*   **⚡ Cost-Efficient Architecture:**
    *   Uses **Google Gemini 2.0 Flash** (via OpenRouter) for high-intelligence reasoning.
    *   Uses **Grok 4.1 Fast** (via OpenRouter) for rapid data gathering.
    *   Uses **Google Generative AI** for free, high-quality RAG embeddings.
*   **✍️ Professional Output:** The Writer agent is strictly prompted to avoid emojis, buzzwords ("game-changer", "landscape"), and fluff, adhering to AP/Reuters standards.
*   **🔄 Iterative Workflow:**
    *   **Dig Deeper:** Ask agents to find specific missing details (e.g., "Find the 2023 budget figures") and update the existing dossier.
    *   **Draft History:** View and retrieve every draft you've ever generated.

## 📂 Project Structure

```text
journalist_crew/
├── .env                     # API Keys
├── journalist_studio.db     # Local Database (Auto-created)
├── pyproject.toml           # Dependencies
├── src/
│   └── journalist_crew/
│       ├── main.py          # CLI Interface (The Entry Point)
│       ├── crew.py          # The Brain (LLM, Tools, & Crew definitions)
│       ├── storage.py       # The Memory (SQLite Logic)
│       ├── models.py        # Data Structures (Pydantic)
│       └── config/
│           ├── agents.yaml  # Agent Roles & Backstories
│           └── tasks.yaml   # Detailed Task Instructions