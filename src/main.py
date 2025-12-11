import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')

# Cria conexão e tabela de exemplo
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
)
''')
conn.commit()

# Insere um usuário de exemplo
cursor.execute('''
INSERT OR IGNORE INTO usuarios (nome, email) VALUES (?, ?)
''', ("Alice", "alice@example.com"))
conn.commit()

# Consulta usuários
cursor.execute('SELECT * FROM usuarios')
for row in cursor.fetchall():
    print(row)

conn.close()
