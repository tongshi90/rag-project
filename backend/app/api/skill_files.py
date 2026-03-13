"""
Skill File Management API Routes
"""
import os
import shutil
from pathlib import Path
from flask import request, jsonify, send_file

from app.api import api_bp
from app.models.skill_card import skill_card_db
from app.config.paths import SKILLS_PATH


def get_skill_folder(skill_code: str) -> Path:
    """Get the skill folder path"""
    return SKILLS_PATH / skill_code


@api_bp.route('/skills/<skill_id>/files', methods=['GET'])
def list_skill_files(skill_id):
    """
    List all files in a skill folder

    Returns both files and directories (non-recursive)
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': 'Skill not found',
            'message': 'Skill not found'
        }), 404

    skill_folder = get_skill_folder(skill_card.skill_code)
    if not skill_folder.exists():
        return jsonify({
            'code': 0,
            'data': [],
            'message': 'Success'
        })

    files = []
    for item in skill_folder.iterdir():
        if item.is_file():
            files.append({
                'name': item.name,
                'isFile': True,
                'size': item.stat().st_size,
                'modifiedTime': item.stat().st_mtime
            })
        elif item.is_dir():
            files.append({
                'name': item.name,
                'isFile': False,
                'size': 0,
                'modifiedTime': item.stat().st_mtime
            })

    # Sort: directories first, then files
    files.sort(key=lambda x: (not x['isFile'], x['name']))

    return jsonify({
        'code': 0,
        'data': files,
        'message': 'Success'
    })


@api_bp.route('/skills/<skill_id>/files/content', methods=['GET'])
def get_skill_file_content(skill_id):
    """
    Get the content of a specific file

    Query params:
        - path: relative path from skill folder (e.g., 'config.yaml' or 'subdir/file.txt')
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': 'Skill not found',
            'message': 'Skill not found'
        }), 404

    file_path = request.args.get('path', '').strip()
    if not file_path:
        return jsonify({
            'code': 400,
            'error': 'File path is required',
            'message': 'File path is required'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': 'Invalid file path',
            'message': 'Invalid file path'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    if not full_path.exists() or not full_path.is_file():
        return jsonify({
            'code': 404,
            'error': 'File not found',
            'message': 'File not found'
        }), 404

    # Check if file is text-based (safe to read)
    # Only allow certain file extensions
    allowed_extensions = {'.txt', '.py', '.js', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.md', '.bat', '.sh', '.conf', '.cfg', '.ini'}
    if full_path.suffix.lower() not in allowed_extensions:
        return jsonify({
            'code': 400,
            'error': 'File type not supported for viewing',
            'message': 'File type not supported for viewing'
        }), 400

    try:
        content = full_path.read_text(encoding='utf-8')
        return jsonify({
            'code': 0,
            'data': {
                'name': full_path.name,
                'path': file_path,
                'content': content,
                'size': full_path.stat().st_size
            },
            'message': 'Success'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'Failed to read file: {str(e)}',
            'message': f'Failed to read file: {str(e)}'
        }), 500


@api_bp.route('/skills/<skill_id>/files', methods=['POST'])
def create_skill_file(skill_id):
    """
    Create a new file in the skill folder

    Request body:
        - path: relative path for the new file (e.g., 'newfile.txt' or 'subdir/file.txt')
        - content: file content (optional, empty string if not provided)
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': 'Skill not found',
            'message': 'Skill not found'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': 'Cannot modify published skill',
            'message': 'Published skills are read-only. Please unpublish first to modify files.'
        }), 403

    data = request.get_json()
    file_path = data.get('path', '').strip()
    content = data.get('content', '')

    if not file_path:
        return jsonify({
            'code': 400,
            'error': 'File path is required',
            'message': 'File path is required'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': 'Invalid file path',
            'message': 'Invalid file path'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file already exists
    if full_path.exists() and full_path.is_file():
        return jsonify({
            'code': 400,
            'error': 'File already exists',
            'message': 'File already exists'
        }), 400

    try:
        full_path.write_text(content, encoding='utf-8')
        return jsonify({
            'code': 0,
            'data': {
                'name': full_path.name,
                'path': file_path,
                'size': full_path.stat().st_size
            },
            'message': 'File created successfully'
        }), 201
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'Failed to create file: {str(e)}',
            'message': f'Failed to create file: {str(e)}'
        }), 500


@api_bp.route('/skills/<skill_id>/files', methods=['PUT'])
def update_skill_file(skill_id):
    """
    Update a file in the skill folder

    Request body:
        - path: relative path of the file (e.g., 'file.txt')
        - newPath: new relative path (optional, for renaming)
        - content: new file content (optional)
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': 'Skill not found',
            'message': 'Skill not found'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': 'Cannot modify published skill',
            'message': 'Published skills are read-only. Please unpublish first to modify files.'
        }), 403

    data = request.get_json()
    file_path = data.get('path', '').strip()
    new_path = data.get('newPath', '').strip()
    content = data.get('content')

    if not file_path:
        return jsonify({
            'code': 400,
            'error': 'File path is required',
            'message': 'File path is required'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': 'Invalid file path',
            'message': 'Invalid file path'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    old_full_path = skill_folder / file_path

    if not old_full_path.exists():
        return jsonify({
            'code': 404,
            'error': 'File not found',
            'message': 'File not found'
        }), 404

    try:
        # Handle renaming
        if new_path and new_path != file_path:
            if '..' in new_path or Path(new_path).is_absolute():
                return jsonify({
                    'code': 400,
                    'error': 'Invalid new file path',
                    'message': 'Invalid new file path'
                }), 400

            new_full_path = skill_folder / new_path
            # Create parent directories if needed
            new_full_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_full_path), str(new_full_path))
            file_path = new_path
            old_full_path = new_full_path

        # Handle content update
        if content is not None:
            if old_full_path.is_file():
                old_full_path.write_text(content, encoding='utf-8')
            else:
                return jsonify({
                    'code': 400,
                    'error': 'Cannot write content to a directory',
                    'message': 'Cannot write content to a directory'
                }), 400

        return jsonify({
            'code': 0,
            'data': {
                'name': old_full_path.name,
                'path': file_path,
                'size': old_full_path.stat().st_size if old_full_path.is_file() else 0
            },
            'message': 'File updated successfully'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'Failed to update file: {str(e)}',
            'message': f'Failed to update file: {str(e)}'
        }), 500


@api_bp.route('/skills/<skill_id>/files', methods=['DELETE'])
def delete_skill_file(skill_id):
    """
    Delete a file or folder in the skill folder

    Query params:
        - path: relative path of the file/folder to delete
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': 'Skill not found',
            'message': 'Skill not found'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': 'Cannot modify published skill',
            'message': 'Published skills are read-only. Please unpublish first to delete files.'
        }), 403

    file_path = request.args.get('path', '').strip()
    if not file_path:
        return jsonify({
            'code': 400,
            'error': 'File path is required',
            'message': 'File path is required'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': 'Invalid file path',
            'message': 'Invalid file path'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    if not full_path.exists():
        return jsonify({
            'code': 404,
            'error': 'File not found',
            'message': 'File not found'
        }), 404

    try:
        if full_path.is_file():
            full_path.unlink()
        elif full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            return jsonify({
                'code': 400,
                'error': 'Invalid path type',
                'message': 'Invalid path type'
            }), 400

        return jsonify({
            'code': 0,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'Failed to delete file: {str(e)}',
            'message': f'Failed to delete file: {str(e)}'
        }), 500
