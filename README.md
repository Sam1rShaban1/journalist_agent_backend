# 📰 AI Journalist Studio

**AI Journalist Studio** is a production-grade, scalable multi-agent system designed for deep investigative research and high-quality news writing.

Unlike standard AI chatbots, this system uses a **Split-Brain Architecture**: it separates **Deep Research** (Time-intensive, Tool-heavy) from **Writing** (Fast, Iterative). It stores all research findings in a **PostgreSQL Database**, allowing for high concurrency, data persistence, and infinite article generation without re-running expensive searches.

## 🚀 Key Features

*   **🧠 Production-Grade Persistence:** Uses **PostgreSQL** to store Research Dossiers and Chat History. No file locking issues, fully scalable.
*   **⚖️ Scalable Architecture:** Containerized with **Docker Compose**, featuring **Nginx Load Balancing** across multiple application replicas.
*   **🖥️ Professional UI:** Built with **Chainlit**, featuring:
    *   **Persistent Chat History:** Stored securely in Postgres.
    *   **Multi-User Auth:** Secure login system.
    *   **Localization:** Full support for **English (en-US)** and **Albanian (sq-AL)**.
    *   **Custom Styling:** "Newsroom" Dark Mode and High-Contrast Light Mode.
*   **🔍 Deep-Dive Tools:** Agents use specialized tools:
    *   **PDF Search:** Reads official government reports/contracts (Vector-based).
    *   **YouTube Search:** Finds direct quotes from political speeches.
    *   **Website Search:** Scrapes specific news archives.
*   **⚡ Cost-Efficient RAG:** Uses **Google Gemini Embeddings** (Free Tier) for vector search.
*   **🔄 "Dig Deeper" Workflow:**
    *   Research specific missing details (e.g., *"Find the 2023 budget numbers"*) and **merge** them into the existing dossier programmatically.
    *   Generate articles with specific instructions (Tone, Language, Length) via the Settings panel.

## 📂 Project Structure

```text
journalist_crew/
├── docker-compose.yml       # Service Orchestration (App, DB, Nginx)
├── nginx.conf               # Load Balancer & WebSocket Config
├── .env                     # API Keys & DB Connection Strings
├── pyproject.toml           # Dependencies (uv)
├── .chainlit/               # UI Config & Translations
│   ├── translations/        # en-US.json, sq-AL.json
│   └── config.toml          # UI Settings
├── public/                  # Assets (Logos, Avatars, CSS)
├── src/
│   └── journalist_crew/
│       ├── config/          # Agent Roles & Tasks (YAML)
│       ├── tools/           # Custom Tool Logic
│       ├── crew.py          # The Brain (LLMs, Tools, Logic)
│       ├── ui.py            # The Frontend (Chainlit Logic)
│       ├── models.py        # Data Schemas (Pydantic)
│       └── storage.py       # Database Layer (PostgreSQL Logic)
```

## 🛠️ Prerequisites

*   **Docker & Docker Compose**
*   **Python 3.12+** (For local development)
*   **uv** (Package manager)
*   **Google AI Studio Key** (Free)
*   **OpenRouter Key** (For LLM inference)

## 📦 Installation & Configuration

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd journalist_crew
    ```

2.  **Configure Environment (`.env`):**
    Create a `.env` file in the root directory. Ensure you set the Database URLs correctly for the container network.

    ```ini
    # --- POSTGRESQL CONFIG ---
    POSTGRES_USER=journalist
    POSTGRES_PASSWORD=secure_password
    POSTGRES_DB=journalist_db

    # Sync URL (For Business Logic)
    DATABASE_URL=postgresql://journalist:secure_password@db:5432/journalist_db

    # Async URL (For Chainlit UI)
    CHAINLIT_DATABASE_URL=postgresql+asyncpg://journalist:secure_password@db:5432/journalist_db

    # --- APP SECURITY ---
    # Generate with: chainlit create-secret
    CHAINLIT_AUTH_SECRET=your_secret_string
    CHAINLIT_USERS={"admin": "admin123", "editor": "news2025"}

    # --- LLM KEYS ---
    OPENROUTER_API_KEY=sk-or-v1-...
    GOOGLE_API_KEY=AIzaSy-...
    SERPER_API_KEY=...
    ```

## 🏃‍♂️ How to Run (Docker)

This is the recommended way to run the application. It spins up the Database, 3 Application Replicas, and the Nginx Load Balancer.

1.  **Build and Start:**
    ```powershell
    docker-compose up --build -d
    ```

2.  **Access the App:**
    Go to **`http://localhost`**
    *(Nginx listens on port 80 and forwards traffic to the available app instances).*

    *Note: The database schema is automatically initialized by `storage.py` when the containers start.*

## 🏃‍♂️ How to Run (Local Dev)

If you want to run without Docker (requires a running Postgres instance):

1.  **Install dependencies:**
    ```powershell
    uv sync
    # Or manually:
    uv add crewai "crewai[tools]" duckduckgo-search langdetect pydantic chromadb chainlit sqlalchemy asyncpg psycopg2-binary
    ```

2.  **Update `.env` for Localhost:**
    Change `@db:5432` to `@localhost:5432` in your `.env` file.

3.  **Start the UI:**
    ```powershell
    chainlit run src/journalist_crew/ui.py
    ```

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

*   **`sqlalchemy.exc.OperationalError`**: Ensure the `db` container is healthy. Run `docker-compose ps`.
*   **`RateLimitError`**: The free OpenRouter models are busy. Wait a minute or switch to a paid model in `crew.py`.
*   **UI Issues**: If buttons look wrong or text is invisible in Light Mode, perform a **Hard Refresh** (`Ctrl+F5`) to reload the custom CSS.
