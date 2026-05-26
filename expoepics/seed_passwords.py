"""
seed_passwords.py
Aplica bcrypt a las contraseñas existentes en la BD.
Ejecutar DESPUÉS de haber corrido 02_datos_prueba.sql en MySQL Workbench.

Uso:
    python seed_passwords.py
"""
import bcrypt
import mysql.connector
from config import Config

usuarios = [
    ('r.garcia@usmp.edu.pe',   'docente123'),
    ('j.mendoza@usmp.edu.pe',  'docente123'),
    ('v.huanca@usmp.edu.pe',   'secre123'),
    ('p.anampa@usmp.edu.pe',   'est123'),
    ('r.ccasani@usmp.edu.pe',  'est123'),
    ('a.mondalgo@usmp.edu.pe', 'est123'),
    ('j.ortiz@usmp.edu.pe',    'est123'),
    ('m.lopez@usmp.edu.pe',    'est123'),
    ('c.vega@usmp.edu.pe',     'juez123'),
    ('l.rivas@usmp.edu.pe',    'juez123'),
    ('a.torres@usmp.edu.pe',   'mkt123'),
    ('l.castro@usmp.edu.pe',   'est123'),
    ('s.rios@usmp.edu.pe',     'est123'),
    ('d.meza@usmp.edu.pe',     'est123'),
]

conn = mysql.connector.connect(
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME,
    port=Config.DB_PORT,
)
cursor = conn.cursor()

for correo, password in usuarios:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    cursor.execute(
        'UPDATE persona SET contrasena=%s WHERE correo=%s',
        (hashed.decode(), correo)
    )
    print(f'  OK {correo}')

conn.commit()
cursor.close()
conn.close()

print('\nContrasenas actualizadas con bcrypt.')
print('\nUsuarios de prueba:')
print('  Docente:    r.garcia@usmp.edu.pe   / docente123')
print('  Secretaria: v.huanca@usmp.edu.pe   / secre123')
print('  Estudiante: r.ccasani@usmp.edu.pe  / est123')
print('  Juez:       c.vega@usmp.edu.pe     / juez123')
print('  Marketing:  a.torres@usmp.edu.pe   / mkt123')
