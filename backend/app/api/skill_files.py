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


def build_file_tree(base_path: Path, relative_path: str = '') -> list:
    """
    Recursively build file tree structure

    Args:
        base_path: The base skill folder path
        relative_path: Current relative path from base (empty for root)

    Returns:
        List of file/folder items with children
    """
    current_path = base_path / relative_path if relative_path else base_path

    if not current_path.exists() or not current_path.is_dir():
        return []

    items = []
    for item in current_path.iterdir():
        # Skip hidden files/folders
        if item.name.startswith('.'):
            continue

        relative_item_path = str(item.relative_to(base_path)) if relative_path else item.name

        if item.is_file():
            items.append({
                'name': item.name,
                'path': relative_item_path.replace('\\', '/'),
                'isFile': True,
                'size': item.stat().st_size,
                'modifiedTime': item.stat().st_mtime,
                'children': []
            })
        elif item.is_dir():
            children = build_file_tree(base_path, relative_item_path)
            items.append({
                'name': item.name,
                'path': relative_item_path.replace('\\', '/'),
                'isFile': False,
                'size': 0,
                'modifiedTime': item.stat().st_mtime,
                'children': children,
                'hasChildren': len(children) > 0
            })

    # Sort: directories first (isFile=False=0), then files (isFile=True=1), alphabetically
    # SKILL.md always goes to the bottom
    items.sort(key=lambda x: (x['isFile'], x['name'] == 'SKILL.md', x['name']))

    return items


@api_bp.route('/skills/<skill_id>/files', methods=['GET'])
def list_skill_files(skill_id):
    """
    List all files in a skill folder (recursive tree structure)

    Returns both files and directories with nested children
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    skill_folder = get_skill_folder(skill_card.skill_code)
    if not skill_folder.exists():
        return jsonify({
            'code': 0,
            'data': [],
            'message': '操作成功'
        })

    files = build_file_tree(skill_folder)

    return jsonify({
        'code': 0,
        'data': files,
        'message': '操作成功'
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
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    file_path = request.args.get('path', '').strip()
    if not file_path:
        return jsonify({
            'code': 400,
            'error': '文件路径不能为空',
            'message': '文件路径不能为空'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': '无效的文件路径',
            'message': '无效的文件路径'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    if not full_path.exists() or not full_path.is_file():
        return jsonify({
            'code': 404,
            'error': '文件不存在',
            'message': '文件不存在'
        }), 404

    # Check if file is text-based (safe to read)
    # Only allow certain file extensions
    # Temporarily disabled - allow all file types to be opened as text
    # allowed_extensions = {'.txt', '.py', '.js', '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css', '.md', '.bat', '.sh', '.conf', '.cfg', '.ini'}
    # if full_path.suffix.lower() not in allowed_extensions:
    #     return jsonify({
    #         'code': 400,
    #         'error': 'File type not supported for viewing',
    #         'message': 'File type not supported for viewing'
    #     }), 400

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
            'message': '操作成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'读取文件失败: {str(e)}',
            'message': f'读取文件失败: {str(e)}'
        }), 500


@api_bp.route('/skills/<skill_id>/files', methods=['POST'])
def create_skill_file(skill_id):
    """
    Create a new file or folder in the skill folder

    Request body:
        - path: relative path for the new file/folder (e.g., 'newfile.txt' or 'subdir/file.txt')
        - content: file content (optional, empty string if not provided)
        - isFolder: boolean, true to create a folder (optional, default false)
    """
    # Check if skill exists
    skill_card = skill_card_db.get_skill_card_by_id(skill_id)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': '无法修改已发布的技能',
            'message': '已发布的技能为只读状态，请先取消发布后再修改文件'
        }), 403

    data = request.get_json()
    file_path = data.get('path', '').strip()
    content = data.get('content', '')
    is_folder = data.get('isFolder', False)

    if not file_path:
        return jsonify({
            'code': 400,
            'error': '文件路径不能为空',
            'message': '文件路径不能为空'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': '无效的文件路径',
            'message': '无效的文件路径'
        }), 400

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if path already exists
    if full_path.exists():
        return jsonify({
            'code': 400,
            'error': '路径已存在',
            'message': '路径已存在'
        }), 400

    try:
        if is_folder:
            # Create folder
            full_path.mkdir(parents=True, exist_ok=True)
            return jsonify({
                'code': 0,
                'data': {
                    'name': full_path.name,
                    'path': file_path,
                    'isFile': False
                },
                'message': '文件夹创建成功'
            }), 201
        else:
            # Create file
            full_path.write_text(content, encoding='utf-8')
            return jsonify({
                'code': 0,
                'data': {
                    'name': full_path.name,
                    'path': file_path,
                    'isFile': True,
                    'size': full_path.stat().st_size
                },
                'message': '文件创建成功'
            }), 201
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'创建失败: {str(e)}',
            'message': f'创建失败: {str(e)}'
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
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': '无法修改已发布的技能',
            'message': '已发布的技能为只读状态，请先取消发布后再修改文件'
        }), 403

    data = request.get_json()
    file_path = data.get('path', '').strip()
    new_path = data.get('newPath', '').strip()
    content = data.get('content')

    if not file_path:
        return jsonify({
            'code': 400,
            'error': '文件路径不能为空',
            'message': '文件路径不能为空'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': '无效的文件路径',
            'message': '无效的文件路径'
        }), 400

    # Protect system files - SKILL.md cannot be renamed
    if file_path == 'SKILL.md' and new_path and new_path != file_path:
        return jsonify({
            'code': 403,
            'error': '无法重命名系统文件',
            'message': 'SKILL.md 是系统文件，不能重命名'
        }), 403

    skill_folder = get_skill_folder(skill_card.skill_code)
    old_full_path = skill_folder / file_path

    if not old_full_path.exists():
        return jsonify({
            'code': 404,
            'error': '文件不存在',
            'message': '文件不存在'
        }), 404

    try:
        # Handle renaming
        if new_path and new_path != file_path:
            if '..' in new_path or Path(new_path).is_absolute():
                return jsonify({
                    'code': 400,
                    'error': '无效的新文件路径',
                    'message': '无效的新文件路径'
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
                    'error': '无法向目录写入内容',
                    'message': '无法向目录写入内容'
                }), 400

        return jsonify({
            'code': 0,
            'data': {
                'name': old_full_path.name,
                'path': file_path,
                'size': old_full_path.stat().st_size if old_full_path.is_file() else 0
            },
            'message': '文件更新成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'更新文件失败: {str(e)}',
            'message': f'更新文件失败: {str(e)}'
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
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    # Check if skill is published - read-only mode
    if skill_card.published:
        return jsonify({
            'code': 403,
            'error': '无法修改已发布的技能',
            'message': '已发布的技能为只读状态，请先取消发布后再删除文件'
        }), 403

    file_path = request.args.get('path', '').strip()
    if not file_path:
        return jsonify({
            'code': 400,
            'error': '文件路径不能为空',
            'message': '文件路径不能为空'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    if '..' in file_path or Path(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': '无效的文件路径',
            'message': '无效的文件路径'
        }), 400

    # Protect system files - SKILL.md cannot be deleted
    if file_path == 'SKILL.md':
        return jsonify({
            'code': 403,
            'error': '无法删除系统文件',
            'message': 'SKILL.md 是系统文件，不能删除'
        }), 403

    skill_folder = get_skill_folder(skill_card.skill_code)
    full_path = skill_folder / file_path

    if not full_path.exists():
        return jsonify({
            'code': 404,
            'error': '文件不存在',
            'message': '文件不存在'
        }), 404

    try:
        if full_path.is_file():
            full_path.unlink()
        elif full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            return jsonify({
                'code': 400,
                'error': '无效的路径类型',
                'message': '无效的路径类型'
            }), 400

        return jsonify({
            'code': 0,
            'message': '文件删除成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'删除文件失败: {str(e)}',
            'message': f'删除文件失败: {str(e)}'
        }), 500
