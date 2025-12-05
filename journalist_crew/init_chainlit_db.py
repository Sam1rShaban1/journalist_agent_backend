import sqlite3

# DB_FILE = "data/chainlit.db"
DB_FILE = "chainlit.db"

def init_db():
    # os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print(f"🔧 Manually creating UPDATED schema in {DB_FILE}...")

    # 1. Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            "id" TEXT NOT NULL PRIMARY KEY,
            "identifier" TEXT NOT NULL UNIQUE,
            "createdAt" TEXT NOT NULL,
            "metadata" TEXT NOT NULL
        );
    """)

    # 2. Threads
    c.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            "id" TEXT NOT NULL PRIMARY KEY,
            "createdAt" TEXT NOT NULL,
            "name" TEXT,
            "userId" TEXT,
            "userIdentifier" TEXT,
            "tags" TEXT,
            "metadata" TEXT,
            FOREIGN KEY("userId") REFERENCES users("id") ON DELETE CASCADE
        );
    """)

    # 3. Steps (Fixed: Added defaultOpen)
    c.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            "id" TEXT NOT NULL PRIMARY KEY,
            "name" TEXT NOT NULL,
            "type" TEXT NOT NULL,
            "threadId" TEXT NOT NULL,
            "parentId" TEXT,
            "disableFeedback" BOOLEAN NOT NULL DEFAULT 0,
            "streaming" BOOLEAN NOT NULL DEFAULT 0,
            "waitForAnswer" BOOLEAN DEFAULT 0,
            "isError" BOOLEAN DEFAULT 0,
            "metadata" TEXT,
            "tags" TEXT,
            "input" TEXT,
            "output" TEXT,
            "createdAt" TEXT,
            "start" TEXT,
            "end" TEXT,
            "generation" TEXT,
            "showInput" TEXT,
            "language" TEXT,
            "indent" INTEGER,
            "defaultOpen" BOOLEAN DEFAULT 0, 
            FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
        );
    """)

    # 4. Elements (Fixed: Added props)
    c.execute("""
        CREATE TABLE IF NOT EXISTS elements (
            "id" TEXT NOT NULL PRIMARY KEY,
            "threadId" TEXT,
            "type" TEXT,
            "url" TEXT,
            "chainlitKey" TEXT,
            "name" TEXT NOT NULL,
            "display" TEXT,
            "objectKey" TEXT,
            "size" TEXT,
            "page" INTEGER,
            "language" TEXT,
            "forId" TEXT,
            "mime" TEXT,
            "props" TEXT,
            FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
        );
    """)

    # 5. Feedbacks
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            "id" TEXT NOT NULL PRIMARY KEY,
            "forId" TEXT NOT NULL,
            "threadId" TEXT NOT NULL,
            "value" INTEGER NOT NULL,
            "comment" TEXT,
            FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized with correct schema.")

if __name__ == "__main__":
    init_db()