"""
API Routes Blueprint
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them with the blueprint
from app.api import files, chat, graph, open, skills, skill_files, public_skills
