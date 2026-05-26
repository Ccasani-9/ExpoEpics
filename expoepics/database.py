import mysql.connector
from flask import g
from config import Config


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT,
            charset='utf8mb4',
        )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, params=None, fetch_one=False, commit=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    is_select = sql.strip().upper().startswith('SELECT')
    if commit or not is_select:
        conn.commit()
        result = cursor.lastrowid
    elif fetch_one:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    cursor.close()
    return result
