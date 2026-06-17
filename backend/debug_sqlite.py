"""Debug SQLite shared memory URI."""
import os
os.environ['DATABASE_URL'] = 'sqlite:///file:testdb?mode=memory&cache=shared'

import sqlite3

# Test 1: shared memory URI works
conn = sqlite3.connect('file:testdb?mode=memory&cache=shared', uri=True)
conn.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)')
conn.commit()
conn.close()

conn2 = sqlite3.connect('file:testdb?mode=memory&cache=shared', uri=True)
rows = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Test 1 - Shared memory URI:', rows)
conn2.close()

# Test 2: app init
print()
print('Test 2 - App init...')
from app.database.sqlite import init_db, get_db, close_db
close_db()
init_db()
db = get_db()
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables after init_db:', [t['name'] for t in tables])
close_db()

# Test 3: get_db after close
print()
print('Test 3 - get_db after close...')
db2 = get_db()
tables2 = db2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables after get_db:', [t['name'] for t in tables2])
