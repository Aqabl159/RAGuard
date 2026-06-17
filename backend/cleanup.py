from app.database.sqlite import init_db, get_db

init_db()
db = get_db()
rows = db.execute("SELECT id, filename FROM documents WHERE status='processing'").fetchall()
for r in rows:
    print(f"Removing: {r['filename']}")
    db.execute("DELETE FROM documents WHERE id=?", (r['id'],))
db.commit()
print("Cleaned")
