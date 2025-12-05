# 📰 AI Journalist Studio

**AI Journalist Studio** is a professional-grade, persistent multi-agent system designed for deep investigative research and high-quality news writing.

Unlike standard AI chatbots, this system uses a **Split-Brain Architecture**: it separates **Deep Research** (Time-intensive, Tool-heavy) from **Writing** (Fast, Iterative). It stores all research findings in a structured local database ("Dossiers"), allowing you to generate infinite article variations without re-running expensive searches.

## 🚀 Key Features

*   **🧠 Persistent Context:** Research findings are saved to `journalist_studio.db`. You can close the app, return days later, and continue where you left off.
*   **🖥️ Professional UI:** Built with **Chainlit**, featuring:
    *   **Chat History:** Sidebar with past research sessions.
    *   **Multi-User Auth:** Secure login system.
    *   **Localization:** Full support for **English (en-US)** and **Albanian (sq-AL)** interfaces.
    *   **Custom Styling:** "Newsroom" Dark Mode and High-Contrast Light Mode.
*   **🔍 Deep-Dive Tools:** Agents use specialized tools to find facts:
    *   **PDF Search:** Reads official government reports/contracts.
    *   **YouTube Search:** Finds direct quotes from political speeches/interviews.
    *   **Website Search:** Scrapes specific news archives.
*   **⚡ Cost-Efficient RAG:** Uses **Google Gemini Embeddings** (Free Tier) for vector search, saving significant OpenAI costs.
*   **🔄 "Dig Deeper" Workflow:**
    *   Research specific missing details (e.g., *"Find the 2023 budget numbers"*) and **merge** them into the existing dossier.
    *   Generate articles with specific instructions (Tone, Language, Length) via the Settings panel.

## 📂 Project Structure

```text
journalist_crew/
├── .chainlit/               # UI Config & Translations
│   ├── translations/        # en-US.json, sq-AL.json
│   └── config.toml          # UI Settings
├── public/                  # Assets (Logos, Avatars, CSS)
├── src/
│   └── journalist_crew/
│       ├── config/          # Agent Roles (YAML)
│       ├── tools/           # Custom Tool Logic
│       ├── crew.py          # The Brain (LLMs, Tools, Logic)
│       ├── ui.py            # The Frontend (Chainlit Logic)
│       ├── models.py        # Data Schemas (Pydantic)
│       └── storage.py       # Database Layer (SQLite)
├── journalist_studio.db     # Research Data (Dossiers)
├── chainlit.db              # Chat History & Users
├── .env                     # API Keys
└── pyproject.toml           # Dependencies (uv)
```

## 🛠️ Prerequisites

*   **Python 3.12+**
*   **uv** (Recommended package manager)
*   **Google AI Studio Key** (Free)
*   **OpenRouter Key** (For LLM inference)

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd journalist_crew
    ```

2.  **Install dependencies:**
    ```powershell
    uv sync
    # Or manually:
    uv add crewai "crewai[tools]" duckduckgo-search langdetect pydantic chromadb chainlit sqlalchemy aiosqlite
    ```

3.  **Configure Environment (`.env`):**
    Create a `.env` file in the root directory:

    ```ini
    # --- LLM KEYS ---
    # Get key: https://openrouter.ai/keys
    OPENROUTER_API_KEY=sk-or-v1-...

    # Get key: https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY=AIzaSy-...

    # Get key: https://serper.dev/
    SERPER_API_KEY=...

    # --- APP SECURITY ---
    # Generate with: chainlit create-secret
    CHAINLIT_AUTH_SECRET=your_secret_string

    # Users (JSON Format)
    CHAINLIT_USERS={"admin": "admin123", "editor": "news2025"}
    ```

## 🏃‍♂️ How to Run

### Local Development
Start the Chainlit server with auto-reload enabled:

```powershell
chainlit run src/journalist_crew/ui.py -w
```

Access the app at **`http://localhost:8000`**.

### Docker Deployment
The project is fully containerized.

1.  **Build and Run:**
    ```powershell
    docker-compose up --build -d
    ```
2.  **Access:**
    Go to **`http://localhost`** (Nginx handles the routing).

*(Note: Docker will automatically initialize the database schema on the first run.)*

## 🧩 Workflow Guide

1.  **Start:** Log in. Type a **Topic Name** (e.g., "Corridor 8").
2.  **Phase 1 (Research):** The agents will scour the web. A "Thinking" animation will appear.
3.  **View Dossier:** Once done, a formatted Dossier (Summary, Timeline, Key Figures) appears.
4.  **Phase 2 (Writing):**
    *   Click **"✍️ Write Article"**.
    *   Provide instructions (e.g., *"Focus on the environmental impact"*).
    *   The Writer Agent generates a long-form draft instantly using the saved dossier.
5.  **Dig Deeper:** To update the research, just type your question in the chat bar (e.g., *"Who was the minister in 2019?"*). The system will find the info and **update** the dossier.

## 🛡️ Troubleshooting

*   **`database is locked`**: Close any DBeaver/SQLite viewers or restart the app.
*   **`RateLimitError`**: The free OpenRouter models are busy. Wait a minute or switch to a paid model in `crew.py`.
*   **UI Issues**: If buttons look wrong, perform a **Hard Refresh** (`Ctrl+F5`) to reload the custom CSS.

## 📄 License
MIT
```
