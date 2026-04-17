import sqlite3
import os
from datetime import datetime

def create_database():
    db_path = "D:/teste/database/memory.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tabela para armazenar histórico de conversas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_input TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            context_data TEXT
        )
    ''')

    # Tabela para armazenar preferências do usuário
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference_key TEXT UNIQUE NOT NULL,
            preference_value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # Tabela para armazenar memórias episódicas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            importance_score REAL DEFAULT 0.5
        )
    ''')

    conn.commit()
    conn.close()
    print("Database created successfully at D:/teste/database/memory.db")

if __name__ == "__main__":
    create_database()