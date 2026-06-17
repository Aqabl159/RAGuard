"""Quick import verification script."""
import sys
sys.path.insert(0, '.')

print("1. config...", end=" ")
from app.config import settings
print("OK:", settings.DEEPSEEK_BASE_URL)

print("2. sqlite...", end=" ")
from app.database.sqlite import get_db, init_db
init_db()
db = get_db()
tables = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"OK: {len(tables)} tables")

print("3. chroma_client...", end=" ")
from app.database.chroma_client import get_chroma_client
print("OK")

print("4. parser...", end=" ")
from app.ingestion.parser import PARSER_MAP
print(f"OK: {list(PARSER_MAP.keys())}")

print("5. chunker...", end=" ")
from app.ingestion.chunker import chunk_text
print(f"OK: {len(chunk_text('测试。' * 200))} chunks")

print("6. embedder...", end=" ")
from app.ingestion.embedder import embed_texts
print("OK")

print("7. candidate_generator...", end=" ")
from app.conflict.candidate_generator import generate_candidate_pairs
print("OK")

print("8. fact_checker...", end=" ")
from app.conflict.fact_checker import check_contradiction
print("OK")

print("9. resolution state...", end=" ")
from app.resolution.state import ResolutionState
print("OK")

print("10. resolution generator...", end=" ")
from app.resolution.generator import extract_claims
print("OK")

print("11. langgraph graph...", end=" ")
from app.resolution.graph import resolution_graph
print("OK")

print("12. qa router...", end=" ")
from app.qa.router import run_qa_pipeline
print("OK")

print("13. main app...", end=" ")
from app.main import app
print(f"OK: {app.title}")

print("\n=== ALL IMPORTS PASSED ===")
