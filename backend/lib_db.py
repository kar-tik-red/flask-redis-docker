import sqlite3

conn = sqlite3.connect("/Users/sharingan/Desktop/lib.db")

cursor = conn.cursor()

cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS users(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT,
               password TEXT
               )
"""
)
conn.commit()

cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS books(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER
               title TEXT,
               author TEXT,
               genre TEXT,
               read INTEGER
               )
"""
)
conn.commit()
conn.close()
