import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'expoepics-secret-key-2026-usmp')
    DB_HOST     = os.environ.get('DB_HOST',     'localhost')
    DB_USER     = os.environ.get('DB_USER',     'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'FiaTdbd20261@')
    DB_NAME     = os.environ.get('DB_NAME',     'ExpoEpics')
    DB_PORT     = int(os.environ.get('DB_PORT', 3306))
