API_TOKEN = '7450267454:AAGUu6Njtrm_Qp86gnJUm7gca6HQz_Kj43w'

import sqlite3

def setup_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            is_approved INTEGER DEFAULT 0
        )
    ''')

    # Create locations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            category TEXT,
            latitude REAL,
            longitude REAL,
            timestamp DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

setup_database()
