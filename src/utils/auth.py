# src/utils/auth.py
# -*- coding: utf-8 -*-
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

DB_PATH = "data/app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'admin'
);
"""

def init_db(path=DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(SCHEMA)
        conn.commit()

def create_user_if_not_exists(path, username, password, role="admin"):
    with sqlite3.connect(path) as conn:
        cur = conn.execute("SELECT id FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            ph = generate_password_hash(password)
            conn.execute("INSERT INTO users(username, password_hash, role) VALUES (?,?,?)", (username, ph, role))
            conn.commit()

def get_user_by_name(path, username):
    with sqlite3.connect(path) as conn:
        cur = conn.execute("SELECT id, username, password_hash, role FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        return User(id=row[0], username=row[1], password_hash=row[2], role=row[3])

class User(UserMixin):
    def __init__(self, id, username, password_hash, role="admin"):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def verify_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    @staticmethod
    def get(user_id):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("SELECT id, username, password_hash, role FROM users WHERE id=?", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return User(id=row[0], username=row[1], password_hash=row[2], role=row[3])
