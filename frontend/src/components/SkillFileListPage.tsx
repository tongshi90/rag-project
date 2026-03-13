import React, { useState, useEffect } from 'react';
import './SkillFileListPage.css';
import { apiService } from '../services/api';
import type { SkillCard, SkillFile } from '../types';

interface SkillFileListPageProps {
  skill: SkillCard;
  onBackToSkills: () => void;
}

export const SkillFileListPage: React.FC<SkillFileListPageProps> = ({ skill, onBackToSkills }) => {
  const [files, setFiles] = useState<SkillFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 新建文件/文件夹模态框
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  // 查看文件模态框（只读模式）
  const [showViewModal, setShowViewModal] = useState(false);
  const [viewingFile, setViewingFile] = useState<SkillFile | null>(null);
  const [viewingContent, setViewingContent] = useState('');
  const [viewLoading, setViewLoading] = useState(false);

  // 编辑文件模态框
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingFile, setEditingFile] = useState<SkillFile | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [editLoading, setEditLoading] = useState(false);

  // 重命名模态框
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renamingFile, setRenamingFile] = useState<SkillFile | null>(null);
  const [renamingFileName, setRenamingFileName] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);

  // 加载文件列表
  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.listSkillFiles(skill.id);
      if (response.code === 0) {
        setFiles(response.data);
      } else {
        setError(response.message || '加载失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  };

  // 创建文件或文件夹
  const handleCreate = async () => {
    if (!newFileName.trim()) {
      alert('请输入文件名');
      return;
    }

    setCreateLoading(true);
    try {
      const response = await apiService.createSkillFile(skill.id, newFileName, '');
      if (response.code === 0) {
        setShowCreateModal(false);
        setNewFileName('');
        await loadFiles();
      } else {
        alert(response.message || '创建失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to create file:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  // 删除文件或文件夹
  const handleDelete = async (file: SkillFile) => {
    const itemType = file.isFile ? '文件' : '文件夹';
    if (!confirm(`确定要删除${itemType} "${file.name}"吗？`)) {
      return;
    }

    try {
      const response = await apiService.deleteSkillFile(skill.id, file.name);
      if (response.code === 0) {
        await loadFiles();
      } else {
        alert(response.message || '删除失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to delete file:', err);
    }
  };

  // 打开查看文件模态框（只读模式）
  const openViewModal = async (file: SkillFile) => {
    if (!file.isFile) return;

    setViewingFile(file);
    setViewingContent('加载中...');
    setShowViewModal(true);
    setViewLoading(true);

    try {
      const response = await apiService.getSkillFileContent(skill.id, file.name);
      if (response.code === 0) {
        setViewingContent(response.data.content);
      } else {
        alert(response.message || '加载文件内容失败');
        setShowViewModal(false);
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to load file content:', err);
      setShowViewModal(false);
    } finally {
      setViewLoading(false);
    }
  };

  // 打开编辑文件模态框
  const openEditModal = async (file: SkillFile) => {
    if (!file.isFile) return;

    setEditingFile(file);
    setEditingContent('加载中...');
    setShowEditModal(true);

    try {
      const response = await apiService.getSkillFileContent(skill.id, file.name);
      if (response.code === 0) {
        setEditingContent(response.data.content);
      } else {
        alert(response.message || '加载文件内容失败');
        setShowEditModal(false);
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to load file content:', err);
      setShowEditModal(false);
    }
  };

  // 保存文件内容
  const handleSaveContent = async () => {
    if (!editingFile) return;

    setEditLoading(true);
    try {
      const response = await apiService.updateSkillFile(skill.id, editingFile.name, undefined, editingContent);
      if (response.code === 0) {
        setShowEditModal(false);
        setEditingFile(null);
        await loadFiles();
      } else {
        alert(response.message || '保存失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to save file:', err);
    } finally {
      setEditLoading(false);
    }
  };

  // 打开重命名模态框
  const openRenameModal = (file: SkillFile) => {
    setRenamingFile(file);
    setRenamingFileName(file.name);
    setShowRenameModal(true);
  };

  // 保存重命名
  const handleRename = async () => {
    if (!renamingFile || !renamingFileName.trim()) {
      alert('请输入新文件名');
      return;
    }

    setRenameLoading(true);
    try {
      const response = await apiService.updateSkillFile(skill.id, renamingFile.name, renamingFileName);
      if (response.code === 0) {
        setShowRenameModal(false);
        setRenamingFile(null);
        await loadFiles();
      } else {
        alert(response.message || '重命名失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to rename file:', err);
    } finally {
      setRenameLoading(false);
    }
  };

  // 组件挂载时加载数据
  useEffect(() => {
    loadFiles();
  }, []);

  // 是否为只读模式（已发布）
  const isReadOnly = skill.published;

  return (
    <div className="skill-file-list-page">
      <header className="file-header">
        <button className="back-button" onClick={onBackToSkills}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"></path>
          </svg>
          返回技能列表
        </button>
        <div className="skill-info">
          <h1 className="skill-title">{skill.title}</h1>
          <span className={`skill-code ${isReadOnly ? 'published' : ''}`}>
            {skill.skillCode}
            {isReadOnly && <span className="published-badge">已发布</span>}
          </span>
        </div>
        {/* 只在未发布状态显示新建按钮 */}
        {!isReadOnly && (
          <button className="add-file-button" onClick={() => setShowCreateModal(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            新建
          </button>
        )}
      </header>

      <div className="file-content">
        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>加载中...</p>
          </div>
        ) : error ? (
          <div className="error-state">
            <p>{error}</p>
            <button className="retry-button" onClick={loadFiles}>重试</button>
          </div>
        ) : files.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <h2 className="empty-title">暂无文件</h2>
            <p className="empty-description">
              {isReadOnly ? '该技能暂无文件' : '点击上方"新建"按钮创建第一个文件'}
            </p>
          </div>
        ) : (
          <div className="file-list">
            {files.map((file) => (
              <div
                key={file.name}
                className={`file-item ${isReadOnly ? 'read-only' : ''}`}
                onClick={() => file.isFile && openViewModal(file)}
              >
                <div className="file-icon">
                  {file.isFile ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="16" y1="13" x2="8" y2="13"></line>
                      <line x1="16" y1="17" x2="8" y2="17"></line>
                      <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                  )}
                </div>
                <span className="file-name">{file.name}</span>
                {/* 只在未发布状态显示操作按钮 */}
                {!isReadOnly && (
                  <div className="file-actions" onClick={(e) => e.stopPropagation()}>
                    {file.isFile && (
                      <button
                        className="file-action-button"
                        onClick={() => openEditModal(file)}
                        title="编辑内容"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                    )}
                    <button
                      className="file-action-button"
                      onClick={() => openRenameModal(file)}
                      title="重命名"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                      </svg>
                    </button>
                    <button
                      className="file-action-button delete-button"
                      onClick={() => handleDelete(file)}
                      title="删除"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                    </button>
                  </div>
                )}
                {/* 发布状态显示查看图标 */}
                {isReadOnly && file.isFile && (
                  <div className="view-hint">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 新建文件模态框 - 仅未发布状态 */}
      {!isReadOnly && showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>新建文件</h2>
              <button className="modal-close-button" onClick={() => setShowCreateModal(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="new-file-name">文件名</label>
                <input
                  id="new-file-name"
                  type="text"
                  className="form-input"
                  placeholder="例如: config.yaml 或 readme.txt"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                />
                <span className="form-hint">支持创建多级路径，例如: folder/file.txt</span>
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-button modal-button-secondary" onClick={() => setShowCreateModal(false)} disabled={createLoading}>
                取消
              </button>
              <button className="modal-button modal-button-primary" onClick={handleCreate} disabled={createLoading}>
                {createLoading ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 查看文件模态框 - 只读模式 */}
      {showViewModal && viewingFile && (
        <div className="modal-overlay" onClick={() => setShowViewModal(false)}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>查看文件: {viewingFile.name}</h2>
              <button className="modal-close-button" onClick={() => setShowViewModal(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              {viewLoading ? (
                <div className="loading-state">
                  <div className="loading-spinner"></div>
                  <p>加载中...</p>
                </div>
              ) : (
                <pre className="file-viewer">{viewingContent}</pre>
              )}
            </div>
            <div className="modal-footer">
              <button className="modal-button modal-button-primary" onClick={() => setShowViewModal(false)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑文件模态框 - 仅未发布状态 */}
      {!isReadOnly && showEditModal && editingFile && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>编辑文件: {editingFile.name}</h2>
              <button className="modal-close-button" onClick={() => setShowEditModal(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <textarea
                className="file-editor"
                value={editingContent}
                onChange={(e) => setEditingContent(e.target.value)}
                spellCheck={false}
              />
            </div>
            <div className="modal-footer">
              <button className="modal-button modal-button-secondary" onClick={() => setShowEditModal(false)} disabled={editLoading}>
                取消
              </button>
              <button className="modal-button modal-button-primary" onClick={handleSaveContent} disabled={editLoading}>
                {editLoading ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 重命名模态框 - 仅未发布状态 */}
      {!isReadOnly && showRenameModal && renamingFile && (
        <div className="modal-overlay" onClick={() => setShowRenameModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>重命名</h2>
              <button className="modal-close-button" onClick={() => setShowRenameModal(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="rename-file-name">新名称</label>
                <input
                  id="rename-file-name"
                  type="text"
                  className="form-input"
                  value={renamingFileName}
                  onChange={(e) => setRenamingFileName(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-button modal-button-secondary" onClick={() => setShowRenameModal(false)} disabled={renameLoading}>
                取消
              </button>
              <button className="modal-button modal-button-primary" onClick={handleRename} disabled={renameLoading}>
                {renameLoading ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
