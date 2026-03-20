"""
Public Skills API - Open access for published skills
"""
import os
from pathlib import Path
from flask import request, jsonify, send_file

from app.api import api_bp
from app.models.skill_card import skill_card_db
from app.config.paths import SKILLS_PATH, PROJECT_ROOT
from app.config.model_config import get_config


def get_base_url():
    """
    Get the base URL for generating download links

    Supports reverse proxy scenarios by checking proxy headers:
    - X-Forwarded-Host: the original host requested by the client
    - X-Forwarded-Proto: the original protocol (http/https)
    - X-Forwarded-Port: the original port

    Returns:
        Base URL like: http://localhost:5000 or https://example.com
    """
    # Check if SERVER_BASE_URL is configured (for Docker/production)
    configured_url = get_config('SERVER_BASE_URL', '')
    if configured_url:
        return configured_url.rstrip('/')

    # Check proxy headers for reverse proxy scenarios
    if request.headers.get('X-Forwarded-Host'):
        scheme = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('X-Forwarded-Host')
        port = request.headers.get('X-Forwarded-Port', '')

        # Build URL with port if needed
        if port and port not in ['80', '443']:
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"

    # Fall back to request.host_url (direct access)
    return request.host_url.rstrip('/')


def get_skill_folder(skill_code: str) -> Path:
    """Get the skill folder path"""
    return SKILLS_PATH / skill_code


@api_bp.route('/public/skills', methods=['GET'])
def get_published_skills():
    """
    Get list of all skills (public API)

    Query params:
        - search: keyword to search in title or skill_code (optional)

    Returns all skills with limited fields:
    - title: skill title
    - description: skill description
    - skillCode: skill code
    - status: 'published' or 'developing'
    - downloadUrl: zip package download URL (only for published skills)
    """
    keyword = request.args.get('search', '').strip()

    # Get all skill cards
    all_skills = skill_card_db.get_all_skill_cards()

    # Filter by keyword if provided
    if keyword:
        keyword_lower = keyword.lower()
        all_skills = [
            s for s in all_skills
            if keyword_lower in s.get('title', '').lower()
            or keyword_lower in s.get('skillCode', '').lower()
        ]

    # Get base URL for downloads (supports reverse proxy)
    base_url = get_base_url()

    # Return only required fields
    result = []
    for skill in all_skills:
        skill_code = skill['skillCode']
        is_published = skill.get('published', False)

        skill_data = {
            'title': skill['title'],
            'description': skill['description'],
            'skillCode': skill_code,
            'status': 'published' if is_published else 'developing'
        }

        # Only add downloadUrl for published skills
        if is_published:
            skill_data['downloadUrl'] = f"{base_url}/api/public/skills/{skill_code}/download/zip"

        result.append(skill_data)

    return jsonify({
        'code': 0,
        'data': result,
        'message': '操作成功'
    })


@api_bp.route('/public/skills/<skill_code>/files', methods=['GET'])
def get_skill_files_download(skill_code):
    """
    Get all files in a skill folder with download URLs (public API)

    This endpoint is for accessing files of published skills only.

    Returns:
        - files: list of files with name, size, and download URL
        - folders: list of subdirectories
    """
    skill_code = skill_code.strip()

    if not skill_code:
        return jsonify({
            'code': 400,
            'error': '技能代码不能为空',
            'message': '技能代码不能为空'
        }), 400

    # Check if skill exists and is published
    skill_card = skill_card_db.get_skill_card_by_code(skill_code)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    if not skill_card.published:
        return jsonify({
            'code': 403,
            'error': '技能未发布',
            'message': '技能未公开，无法访问'
        }), 403

    skill_folder = get_skill_folder(skill_code)

    if not skill_folder.exists():
        return jsonify({
            'code': 0,
            'data': {
                'files': [],
                'folders': []
            },
            'message': '未找到文件'
        })

    # Get base URL for downloads (supports reverse proxy)
    base_url = get_base_url()

    files = []
    folders = []

    for item in skill_folder.iterdir():
        if item.is_file():
            # Get relative path from skill folder
            relative_path = item.relative_to(skill_folder)
            # Generate full download URL
            download_url = f"{base_url}/api/public/skills/{skill_code}/download?path={str(relative_path)}"

            files.append({
                'name': item.name,
                'size': item.stat().st_size,
                'downloadUrl': download_url
            })
        elif item.is_dir():
            folders.append({
                'name': item.name,
                'itemCount': len(list(item.iterdir()))
            })

    # Sort: folders first, then files
    folders.sort(key=lambda x: x['name'])
    files.sort(key=lambda x: x['name'])

    return jsonify({
        'code': 0,
        'data': {
            'files': files,
            'folders': folders
        },
        'message': '操作成功'
    })


@api_bp.route('/public/skills/<skill_code>/download', methods=['GET'])
def download_skill_file(skill_code):
    """
    Download a file from skill folder (public API)

    Query params:
        - path: relative path of the file (e.g., 'config.yaml' or 'subdir/file.txt')

    This endpoint serves files for download from published skills only.
    """
    skill_code = skill_code.strip()

    if not skill_code:
        return jsonify({
            'code': 400,
            'error': '技能代码不能为空',
            'message': '技能代码不能为空'
        }), 400

    # Check if skill exists and is published
    skill_card = skill_card_db.get_skill_card_by_code(skill_code)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    if not skill_card.published:
        return jsonify({
            'code': 403,
            'error': '技能未发布',
            'message': '技能未公开，无法访问'
        }), 403

    file_path = request.args.get('path', '').strip()

    if not file_path:
        return jsonify({
            'code': 400,
            'error': '文件路径不能为空',
            'message': '文件路径不能为空'
        }), 400

    # Security: prevent path traversal (cross-platform compatible)
    from pathlib import Path as FilePath
    if '..' in file_path or FilePath(file_path).is_absolute():
        return jsonify({
            'code': 400,
            'error': '无效的文件路径',
            'message': '无效的文件路径'
        }), 400

    skill_folder = get_skill_folder(skill_code)
    file_path = skill_folder / file_path

    if not file_path.exists():
        return jsonify({
            'code': 404,
            'error': '文件不存在',
            'message': '文件不存在'
        }), 404

    if not file_path.is_file():
        return jsonify({
            'code': 400,
            'error': '路径不是文件',
            'message': '无法下载目录'
        }), 400

    # Send file for download
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'下载文件失败: {str(e)}',
            'message': f'下载文件失败: {str(e)}'
        }), 500


@api_bp.route('/public/skills/<skill_code>/download/zip', methods=['GET'])
def download_skill_zip(skill_code):
    """
    Download the complete skill package as a zip file (public API)

    This endpoint serves the pre-packaged zip file for published skills.

    The zip file contains all files in the skill folder and is automatically
    created when the skill is published.
    """
    skill_code = skill_code.strip()

    if not skill_code:
        return jsonify({
            'code': 400,
            'error': '技能代码不能为空',
            'message': '技能代码不能为空'
        }), 400

    # Check if skill exists and is published
    skill_card = skill_card_db.get_skill_card_by_code(skill_code)
    if not skill_card:
        return jsonify({
            'code': 404,
            'error': '技能不存在',
            'message': '技能不存在'
        }), 404

    if not skill_card.published:
        return jsonify({
            'code': 403,
            'error': '技能未发布',
            'message': '技能未公开，无法访问'
        }), 403

    # Get the published directory and zip file path
    publish_dir = SKILLS_PATH / '_published'
    zip_path = publish_dir / f"{skill_code}.zip"

    if not zip_path.exists():
        return jsonify({
            'code': 404,
            'error': '技能包不存在',
            'message': '技能包可能尚未创建，请联系管理员'
        }), 404

    # Send zip file for download
    try:
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{skill_code}.zip",
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({
            'code': 500,
            'error': f'下载技能包失败: {str(e)}',
            'message': f'下载技能包失败: {str(e)}'
        }), 500
