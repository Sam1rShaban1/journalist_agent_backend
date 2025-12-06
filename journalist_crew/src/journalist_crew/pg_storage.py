import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from journalist_crew.models import ResearchDossier

class StorageManager:
    def __init__(self):
        # Default to localhost for local dev, Docker ENV overrides this
        self.db_url = os.getenv("DATABASE_URL", "postgresql://journalist:securepassword@localhost:5432/journalist_db")
        
        # Auto-initialize tables on startup
        self.initialize_db()

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def initialize_db(self):
        """Creates All Tables (Chainlit + Journalist) if they don't exist."""
        conn = self._get_conn()
        c = conn.cursor()
        
        try:
            # --- 1. CHAINLIT SCHEMA ---
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    "id" TEXT PRIMARY KEY,
                    "identifier" TEXT UNIQUE NOT NULL,
                    "metadata" JSONB DEFAULT '{}'::jsonb,
                    "createdAt" TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    "id" TEXT PRIMARY KEY,
                    "createdAt" TEXT DEFAULT CURRENT_TIMESTAMP,
                    "name" TEXT,
                    "userId" TEXT,
                    "userIdentifier" TEXT,
                    "tags" TEXT[],
                    "metadata" JSONB DEFAULT '{}'::jsonb,
                    FOREIGN KEY("userId") REFERENCES users("id") ON DELETE CASCADE
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS steps (
                    "id" TEXT PRIMARY KEY,
                    "name" TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    "threadId" TEXT NOT NULL,
                    "parentId" TEXT,
                    "disableFeedback" BOOLEAN DEFAULT FALSE,
                    "streaming" BOOLEAN DEFAULT FALSE,
                    "waitForAnswer" BOOLEAN DEFAULT FALSE,
                    "isError" BOOLEAN DEFAULT FALSE,
                    "metadata" JSONB DEFAULT '{}'::jsonb,
                    "tags" TEXT[],
                    "input" TEXT,
                    "output" TEXT,
                    "createdAt" TEXT DEFAULT CURRENT_TIMESTAMP,
                    "start" TEXT,
                    "end" TEXT,
                    "generation" JSONB,
                    "showInput" TEXT,
                    "language" TEXT,
                    "indent" INTEGER,
                    "defaultOpen" BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS elements (
                    "id" TEXT PRIMARY KEY,
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
                    "props" JSONB DEFAULT '{}'::jsonb,
                    FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    "id" TEXT PRIMARY KEY,
                    "forId" TEXT NOT NULL,
                    "threadId" TEXT NOT NULL,
                    "value" INTEGER NOT NULL,
                    "comment" TEXT,
                    FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
                );
            """)

            # --- 2. JOURNALIST SCHEMA ---
            c.execute("""
                CREATE TABLE IF NOT EXISTS dossiers (
                    id TEXT PRIMARY KEY,
                    topic TEXT,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    dossier_id TEXT,
                    content TEXT,
                    instructions TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(dossier_id) REFERENCES dossiers(id)
                );
            """)
            conn.commit()
            # print("✅ Database tables verified.")
        except Exception as e:
            print(f"❌ Database Init Error: {e}")
        finally:
            conn.close()

    # --- JOURNALIST LOGIC ---

    def save_dossier(self, dossier: ResearchDossier):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Use json.loads to convert Pydantic's JSON string into a Python dict
        # so psycopg2 can adapt it to JSONB correctly
        data_dict = json.loads(dossier.model_dump_json())

        cursor.execute('''
            INSERT INTO dossiers (id, topic, data, modified_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT(id) DO UPDATE SET
                topic=EXCLUDED.topic,
                data=EXCLUDED.data,
                modified_at=NOW()
        ''', (dossier.id, dossier.topic, Json(data_dict)))
        
        conn.commit()
        conn.close()
        print(f"💾 Dossier saved (PG). ID: {dossier.id}")

    def load_dossier(self, dossier_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM dossiers WHERE id = %s', (dossier_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # row[0] is already a dict because it's JSONB
            return ResearchDossier.model_validate(row[0])
        return None

    def list_dossiers(self):
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT id, topic, created_at, modified_at FROM dossiers ORDER BY modified_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def save_article(self, dossier_id: str, content: str, instructions: str, lang: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO articles (dossier_id, content, instructions, language, created_at, modified_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        ''', (dossier_id, content, instructions, lang))
        conn.commit()
        conn.close()

    def get_article_history(self, dossier_id: str):
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT id, content, instructions, language, created_at 
            FROM articles 
            WHERE dossier_id = %s 
            ORDER BY created_at DESC
        ''', (dossier_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # --- SYNC LOGIC ---

    def sync_dossiers_to_sidebar(self, user_identifier: str):
        """Pushes existing dossiers into Chainlit threads for the user."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            # 1. Get Dossiers
            cursor.execute("SELECT id, topic, created_at FROM dossiers")
            dossiers = cursor.fetchall()

            # 2. Get Existing Threads for this user
            cursor.execute('SELECT "id" FROM threads WHERE "userId" = %s', (user_identifier,))
            existing_ids = {row[0] for row in cursor.fetchall()}

            count = 0
            for doc_id, topic, created_at in dossiers:
                if doc_id not in existing_ids:
                    meta_json = Json({"dossier_id": doc_id, "topic_name": topic})
                    
                    cursor.execute("""
                        INSERT INTO threads ("id", "createdAt", "name", "userId", "userIdentifier", "metadata")
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        doc_id, 
                        created_at, 
                        topic, 
                        user_identifier, 
                        user_identifier, 
                        meta_json
                    ))
                    count += 1
            
            if count > 0:
                conn.commit()
                print(f"🔄 Synced {count} dossiers to Sidebar.")
            
            conn.close()
        except Exception as e:
            print(f"Sync Error: {e}")