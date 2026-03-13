"""
Skill Card Management API Routes
"""
import time
import re
import os
import shutil
import zipfile
from pathlib import Path
from flask import request, jsonify

from app.api import api_bp
from app.models.skill_card import skill_card_db, SkillCard
from app.config.paths import SKILLS_PATH


def get_publish_dir():
    """Get the published skills directory (for zip files)"""
    publish_dir = SKILLS_PATH / '_published'
    publish_dir.mkdir(parents=True, exist_ok=True)
    return publish_dir


def create_skill_zip(skill_code: str) -> str:
    """
    Create a zip file for the skill

    Args:
        skill_code: The skill code

    Returns:
        Path to the created zip file
    """
    skill_folder = SKILLS_PATH / skill_code
    publish_dir = get_publish_dir()
    zip_path = publish_dir / f"{skill_code}.zip"

    # Delete existing zip if any
    if zip_path.exists():
        zip_path.unlink()

    # Create new zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in skill_folder.rglob('*'):
            if file_path.is_file():
                # Calculate relative path from skill folder
                arcname = file_path.relative_to(skill_folder)
                zipf.write(file_path, arcname)

    return str(zip_path)


def get_skills_dir():
    """Get the skills directory path"""
    skills_dir = SKILLS_PATH
    # Ensure skills directory exists
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def validate_skill_code(skill_code: str) -> bool:
    """
    Validate skill code format
    Only allows alphanumeric characters, underscores, and hyphens (中划线)
    """
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, skill_code))


def generate_skill_card_id():
    """Generate unique skill card ID using timestamp"""
    return str(int(time.time() * 1000))


@api_bp.route('/skills', methods=['GET'])
def get_skills():
    """
    Get all skill cards or search by keyword

    Query params:
        - search: keyword to search in title and description
    """
    keyword = request.args.get('search', '').strip()

    if keyword:
        skill_cards = skill_card_db.search_skill_cards(keyword)
    else:
        skill_cards = skill_card_db.get_all_skill_cards()

    return jsonify({
        'code': 0,
        'data': skill_cards,
        'message': 'Success'
    })


@api_bp.route('/skills/<card_id>', methods=['GET'])
def get_skill(card_id):
    """Get a specific skill card by ID"""
    skill_card = skill_card_db.get_skill_card_by_id(card_id)

    if skill_card:
        return jsonify({
            'code': 0,
            'data': skill_card.to_dict(),
            'message': 'Success'
        })
    else:
        return jsonify({
            'code': 404,
            'error': 'Skill card not found',
            'message': 'Skill card not found'
        }), 404


@api_bp.route('/skills', methods=['POST'])
def create_skill():
    """
    Create a new skill card

    Request body:
        - title: skill title (required)
        - description: skill description (required)
        - skillCode: skill code (required, alphanumeric + underscore only)
        - published: whether the skill is published (optional, default false)
    """
    data = request.get_json()

    # Validation
    if not data:
        return jsonify({
            'code': 400,
            'error': 'Request body is required',
            'message': 'Request body is required'
        }), 400

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    skill_code = data.get('skillCode', '').strip()
    published = data.get('published', False)

    if not title:
        return jsonify({
            'code': 400,
            'error': 'Title is required',
            'message': 'Title is required'
        }), 400

    if not description:
        return jsonify({
            'code': 400,
            'error': 'Description is required',
            'message': 'Description is required'
        }), 400

    if not skill_code:
        return jsonify({
            'code': 400,
            'error': 'Skill Code is required',
            'message': 'Skill Code is required'
        }), 400

    if not validate_skill_code(skill_code):
        return jsonify({
            'code': 400,
            'error': 'Skill Code can only contain letters, numbers, underscores, and hyphens',
            'message': 'Skill Code can only contain letters, numbers, underscores, and hyphens'
        }), 400

    # Check if skill code already exists
    if skill_card_db.is_skill_code_exists(skill_code):
        return jsonify({
            'code': 400,
            'error': 'Skill Code already exists',
            'message': 'Skill Code already exists'
        }), 400

    # Create skill card
    card_id = generate_skill_card_id()
    skill_card = SkillCard(
        id=card_id,
        title=title,
        description=description,
        skill_code=skill_code,
        published=published
    )

    skill_card_db.insert_skill_card(skill_card)

    # Create skill folder
    skills_dir = get_skills_dir()
    skill_folder = skills_dir / skill_code
    print(f'[DEBUG] Skills directory: {skills_dir}')
    print(f'[DEBUG] Skill folder: {skill_folder}')
    print(f'[DEBUG] Skill folder exists: {skill_folder.exists()}')
    try:
        skill_folder.mkdir(parents=True, exist_ok=True)
        print(f'[DEBUG] Folder created successfully')
    except Exception as e:
        # If folder creation fails, rollback database insert
        print(f'[ERROR] Failed to create folder: {str(e)}')
        skill_card_db.delete_skill_card(card_id)
        return jsonify({
            'code': 500,
            'error': f'Failed to create skill folder: {str(e)}',
            'message': f'Failed to create skill folder: {str(e)}'
        }), 500

    return jsonify({
        'code': 0,
        'data': skill_card.to_dict(),
        'message': 'Skill card created successfully'
    }), 201


@api_bp.route('/skills/<card_id>', methods=['PUT'])
def update_skill(card_id):
    """
    Update a skill card

    Request body:
        - title: skill title (optional)
        - description: skill description (optional)
        Note: skillCode cannot be modified after creation
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'code': 400,
            'error': 'Request body is required',
            'message': 'Request body is required'
        }), 400

    # Check if skill card exists
    existing_card = skill_card_db.get_skill_card_by_id(card_id)
    if not existing_card:
        return jsonify({
            'code': 404,
            'error': 'Skill card not found',
            'message': 'Skill card not found'
        }), 404

    # Check if skill is published - cannot modify published skill info
    if existing_card.published:
        return jsonify({
            'code': 403,
            'error': 'Cannot modify published skill',
            'message': 'Published skills cannot be modified. Please unpublish first.'
        }), 403

    # Update skill card (only title and description can be modified)
    title = data.get('title')
    description = data.get('description')

    skill_card_db.update_skill_card(
        card_id=card_id,
        title=title if title else None,
        description=description if description else None
    )

    # Return updated card
    updated_card = skill_card_db.get_skill_card_by_id(card_id)

    return jsonify({
        'code': 0,
        'data': updated_card.to_dict(),
        'message': 'Skill card updated successfully'
    })


@api_bp.route('/skills/<card_id>', methods=['DELETE'])
def delete_skill(card_id):
    """Delete a skill card by ID"""
    # Check if skill card exists
    existing_card = skill_card_db.get_skill_card_by_id(card_id)
    if not existing_card:
        return jsonify({
            'code': 404,
            'error': 'Skill card not found',
            'message': 'Skill card not found'
        }), 404

    # Check if skill is published
    if existing_card.published:
        return jsonify({
            'code': 400,
            'error': 'Cannot delete published skill',
            'message': 'Cannot delete published skill. Please unpublish first.'
        }), 400

    # Get skill code before deleting from database
    skill_code = existing_card.skill_code

    # Delete from database
    skill_card_db.delete_skill_card(card_id)

    # Delete skill folder
    if skill_code:
        skills_dir = get_skills_dir()
        skill_folder = skills_dir / skill_code
        if skill_folder.exists():
            try:
                shutil.rmtree(skill_folder)
            except Exception as e:
                # Log error but don't fail the deletion
                print(f'Warning: Failed to delete skill folder {skill_folder}: {str(e)}')

    return jsonify({
        'code': 0,
        'message': 'Skill card deleted successfully'
    })


@api_bp.route('/skills', methods=['DELETE'])
def delete_all_skills():
    """Delete all skill cards"""
    skill_card_db.delete_all_skill_cards()

    return jsonify({
        'code': 0,
        'message': 'All skill cards deleted successfully'
    })


@api_bp.route('/skills/<card_id>/publish', methods=['PUT'])
def publish_skill(card_id):
    """Publish a skill card"""
    # Check if skill card exists
    existing_card = skill_card_db.get_skill_card_by_id(card_id)
    if not existing_card:
        return jsonify({
            'code': 404,
            'error': 'Skill card not found',
            'message': 'Skill card not found'
        }), 404

    # Create zip package before publishing
    try:
        zip_path = create_skill_zip(existing_card.skill_code)
        print(f'[INFO] Created zip package for skill {existing_card.skill_code}: {zip_path}')
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'Failed to create skill package: {str(e)}',
            'message': f'Failed to create skill package: {str(e)}'
        }), 500

    skill_card_db.update_skill_card(card_id, published=True)

    # Return updated card
    updated_card = skill_card_db.get_skill_card_by_id(card_id)

    return jsonify({
        'code': 0,
        'data': updated_card.to_dict(),
        'message': 'Skill card published successfully'
    })


@api_bp.route('/skills/<card_id>/unpublish', methods=['PUT'])
def unpublish_skill(card_id):
    """Unpublish a skill card"""
    # Check if skill card exists
    existing_card = skill_card_db.get_skill_card_by_id(card_id)
    if not existing_card:
        return jsonify({
            'code': 404,
            'error': 'Skill card not found',
            'message': 'Skill card not found'
        }), 404

    skill_card_db.update_skill_card(card_id, published=False)

    # Remove zip package if exists
    publish_dir = get_publish_dir()
    zip_path = publish_dir / f"{existing_card.skill_code}.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
            print(f'[INFO] Removed zip package for skill {existing_card.skill_code}')
        except Exception as e:
            print(f'[WARNING] Failed to remove zip package: {str(e)}')

    # Return updated card
    updated_card = skill_card_db.get_skill_card_by_id(card_id)

    return jsonify({
        'code': 0,
        'data': updated_card.to_dict(),
        'message': 'Skill card unpublished successfully'
    })
