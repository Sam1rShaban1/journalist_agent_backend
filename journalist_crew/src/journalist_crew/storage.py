import sqlite3
from typing import List, Dict, Optional
from journalist_crew.models import ResearchDossier

DB_FILE = "journalist_studio.db"

class StorageManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        # 1. Dossiers Table (Now keyed by UUID)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dossiers (
                id TEXT PRIMARY KEY,
                topic TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Articles Table (Links to Dossier ID, not Topic Name)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id TEXT,
                content TEXT,
                instructions TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dossier_id) REFERENCES dossiers(id)
            )
        ''')
        self.conn.commit()

    def save_dossier(self, dossier: ResearchDossier):
        """Saves or updates the dossier using its UUID."""
        cursor = self.conn.cursor()
        json_data = dossier.model_dump_json()
        
        # We use INSERT OR REPLACE so we can update existing sessions too
        cursor.execute('''
            INSERT OR REPLACE INTO dossiers (id, topic, data, created_at)
            VALUES (?, ?, ?, COALESCE((SELECT created_at FROM dossiers WHERE id = ?), CURRENT_TIMESTAMP))
        ''', (dossier.id, dossier.topic, json_data, dossier.id))
        self.conn.commit()
        print(f"💾 Dossier saved. ID: {dossier.id}")

    def load_dossier(self, dossier_id: str) -> Optional[ResearchDossier]:
        """Loads a specific research session by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT data FROM dossiers WHERE id = ?', (dossier_id,))
        row = cursor.fetchone()
        if row:
            return ResearchDossier.model_validate_json(row['data'])
        return None

    def list_dossiers(self) -> List[Dict]:
        """Returns a list of all sessions with metadata."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, topic, created_at FROM dossiers ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]

    def save_article(self, dossier_id: str, content: str, instructions: str, lang: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO articles (dossier_id, content, instructions, language)
            VALUES (?, ?, ?, ?)
        ''', (dossier_id, content, instructions, lang))
        self.conn.commit()

    def get_article_history(self, dossier_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, content, instructions, language, created_at 
            FROM articles 
            WHERE dossier_id = ? 
            ORDER BY created_at DESC
        ''', (dossier_id,))
        return [dict(row) for row in cursor.fetchall()]