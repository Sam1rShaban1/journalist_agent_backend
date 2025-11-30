import sqlite3
import json
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
        
        # Table 1: The Research (The "Brain")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dossiers (
                topic TEXT PRIMARY KEY,
                data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table 2: The Articles (The "Output")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                content TEXT,
                instructions TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(topic) REFERENCES dossiers(topic)
            )
        ''')
        self.conn.commit()

    def save_dossier(self, dossier: ResearchDossier):
        cursor = self.conn.cursor()
        json_data = dossier.model_dump_json()
        cursor.execute('''
            INSERT OR REPLACE INTO dossiers (topic, data, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (dossier.topic.lower(), json_data))
        self.conn.commit()

    def load_dossier(self, topic: str) -> Optional[ResearchDossier]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT data FROM dossiers WHERE topic = ?', (topic.lower(),))
        row = cursor.fetchone()
        if row:
            return ResearchDossier.model_validate_json(row['data'])
        return None

    def list_topics(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT topic FROM dossiers ORDER BY last_updated DESC')
        return [row['topic'] for row in cursor.fetchall()]

    def save_article(self, topic: str, content: str, instructions: str, lang: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO articles (topic, content, instructions, language)
            VALUES (?, ?, ?, ?)
        ''', (topic.lower(), content, instructions, lang))
        self.conn.commit()

    def get_article_history(self, topic: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, content, instructions, language, created_at 
            FROM articles 
            WHERE topic = ? 
            ORDER BY created_at DESC
        ''', (topic.lower(),))
        return [dict(row) for row in cursor.fetchall()]