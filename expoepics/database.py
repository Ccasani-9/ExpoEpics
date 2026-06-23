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
            autocommit=False,
        )
    else:
        try:
            g.db.ping(reconnect=True, attempts=3, delay=1)
        except Exception:
            g.db = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                port=Config.DB_PORT,
                charset='utf8mb4',
                autocommit=False,
            )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, params=None, fetch_one=False, commit=False):
    conn = get_db()
    # buffered=True: todos los resultados se traen inmediatamente a memoria,
    # evitando que queden filas "pendientes" en el servidor al reutilizar la conexión.
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(sql, params or ())
        is_select = sql.strip().upper().startswith('SELECT')
        if commit or not is_select:
            conn.commit()
            result = cursor.lastrowid
        elif fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
    finally:
        cursor.close()
    return result
