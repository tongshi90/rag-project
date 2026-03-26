"""
API Routes Blueprint
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them with blueprint
# Note: knowledge_bases and retrieval_test don't depend on chromadb, so they should work even if chromadb fails
from app.api import knowledge_bases, retrieval_test, retrieval_test_history

# These may fail if chromadb/sqlite3 has issues, but knowledge_bases will still work
try:
    from app.api import files, graph, skills, skill_files, public_skills
    from app.api.open import ask  # /api/chat endpoint is defined here
except ImportError as e:
    import warnings
    warnings.warn(f"Some API modules failed to import: {e}")
