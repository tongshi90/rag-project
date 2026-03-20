import React, { useState, useEffect } from 'react';
import { useConfirmDialog } from './ConfirmDialog';
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

  // 确认弹窗
  const { confirm, DialogComponent } = useConfirmDialog();

  // 树形展开状态
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  // 新建文件/文件夹模态框
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileType, setNewFileType] = useState<'file' | 'folder'>('file');
  const [parentFolder, setParentFolder] = useState<SkillFile | null>(null);
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

        // 构建树形结构
        const tree = buildTreeStructure(response.data);

        // 递归收集所有文件夹路径
        const collectFolderPaths = (nodes: SkillFile[]): string[] => {
          const paths: string[] = [];
          nodes.forEach(node => {
            if (!node.isFile) {
              paths.push((node as any).originalPath || node.path);
            }
            if (node.children && node.children.length > 0) {
              paths.push(...collectFolderPaths(node.children));
            }
          });
          return paths;
        };

        const allFolderPaths = collectFolderPaths(tree);
        setExpandedFolders(new Set(allFolderPaths));
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

  // 切换文件夹展开/折叠状态
  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  // 判断文件夹是否展开
  const isFolderExpanded = (path: string) => expandedFolders.has(path);

  // 递归标记系统文件
  const markSystemFiles = (nodes: SkillFile[]): void => {
    nodes.forEach(node => {
      // 标记 SKILL.md 为系统文件
      if (node.name === 'SKILL.md') {
        (node as any).isSystemFile = true;
      }
      // 递归处理子节点
      if (node.children && node.children.length > 0) {
        markSystemFiles(node.children);
      }
    });
  };

  // 构建树形结构数据（如果后端返回的是平铺数据）
  const buildTreeStructure = (fileList: SkillFile[]): SkillFile[] => {
    // 如果已经有 children 属性，说明后端已经返回树形结构，标记系统文件后直接使用
    if (fileList.some(f => f.children)) {
      markSystemFiles(fileList);
      return fileList;
    }

    const map = new Map<string, SkillFile>();
    const roots: SkillFile[] = [];

    // 初始化所有节点，保持原始 path
    fileList.forEach(file => {
      map.set(file.path, { ...file, children: [], originalPath: file.path });
    });

    // 确保所有中间文件夹都存在
    fileList.forEach(file => {
      const parts = file.path.split('/');
      // 创建所有中间文件夹路径
      for (let i = 0; i < parts.length; i++) {
        const partialPath = parts.slice(0, i + 1).join('/');
        if (!map.has(partialPath)) {
          // 创建中间文件夹节点
          const isFile = i === parts.length - 1 ? file.isFile : false;
          const folderNode: SkillFile = {
            name: parts[i],
            path: partialPath,
            isFile: isFile,
            size: 0,
            modifiedTime: Date.now(),
            children: [],
            originalPath: partialPath
          };
          map.set(partialPath, folderNode);
        }
      }
    });

    // 更新叶子节点的属性
    fileList.forEach(file => {
      const node = map.get(file.path)!;
      node.size = file.size;
      node.modifiedTime = file.modifiedTime;
      node.isFile = file.isFile;
      // 标记系统文件（SKILL.md）
      node.isSystemFile = file.name === 'SKILL.md' || (file as any).isSystemFile;
    });

    // 构建树形结构
    fileList.forEach(file => {
      const node = map.get(file.path)!;
      const parts = file.path.split('/');
      if (parts.length > 1) {
        // 有父路径
        const parentPath = parts.slice(0, -1).join('/');
        const parent = map.get(parentPath);
        if (parent && parent !== node) {
          if (!parent.children) parent.children = [];
          if (!parent.children.includes(node)) {
            parent.children.push(node);
          }
        }
      }
    });

    // 收集所有根节点
    map.forEach(node => {
      const parts = node.path.split('/');
      if (parts.length === 1) {
        roots.push(node);
      }
    });

    return roots;
  };

  const treeFiles = buildTreeStructure(files);

  // 递归渲染树节点
  const renderTreeNode = (node: SkillFile, level: number = 0): React.ReactNode => {
    // 使用原始路径来检查展开状态（如果有的话）
    const pathToCheck = (node as any).originalPath || node.path;
    const isExpanded = isFolderExpanded(pathToCheck);
    const hasChildren = node.children && node.children.length > 0;
    const paddingLeft = level * 20;

    return (
      <div key={node.path} className="tree-node">
        <div
          className={`file-item ${isReadOnly ? 'read-only' : ''} ${node.isFile ? 'file-type' : 'folder-type'}`}
          style={{ paddingLeft: `${paddingLeft + 12}px` }}
          onClick={() => node.isFile && openViewModal(node)}
        >
          {/* 展开/折叠按钮 */}
          {!node.isFile && (
            <button
              className="expand-button"
              onClick={(e) => {
                e.stopPropagation();
                const pathToCheck = (node as any).originalPath || node.path;
                toggleFolder(pathToCheck);
              }}
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </button>
          )}

          {/* 文件占位空间，与文件夹的展开按钮对齐 */}
          {node.isFile && <div className="expand-spacer"></div>}

          {/* 文件/文件夹图标 */}
          <div className="file-icon">
            {node.isFile ? (
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

          {/* 文件名 */}
          <span className={`file-name ${(node as any).isSystemFile ? 'system-file' : ''}`}>
            {node.name}
            {(node as any).isSystemFile && (
              <svg className="system-file-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10 5 10 5v2H2v-2l10-10Z"></path>
              </svg>
            )}
          </span>

          {/* 操作按钮 */}
          {!isReadOnly && (
            <div className="file-actions" onClick={(e) => e.stopPropagation()}>
              {node.isFile ? (
                <>
                  <button className="file-action-button view-button" onClick={() => openViewModal(node)} title="查看">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </button>
                  <button className="file-action-button edit-button" onClick={() => openEditModal(node)} title="编辑内容">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 20h9"></path>
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                    </svg>
                  </button>
                </>
              ) : (
                <>
                  <button className="file-action-button add-child-button" onClick={() => openAddFileModal(node)} title="添加文件">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="12" y1="19" x2="12" y2="12"></line>
                      <line x1="9" y1="16" x2="15" y2="16"></line>
                    </svg>
                  </button>
                  <button className="file-action-button add-child-button" onClick={() => openAddFolderModal(node)} title="添加子文件夹">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                      <line x1="12" y1="11" x2="12" y2="17"></line>
                      <line x1="9" y1="14" x2="15" y2="14"></line>
                    </svg>
                  </button>
                </>
              )}
              {/* 非系统文件才显示重命名和删除按钮 */}
              {!(node as any).isSystemFile && (
                <>
                  <button className="file-action-button rename-button" onClick={() => openRenameModal(node)} title="重命名">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                      <path d="M9 10h6"></path>
                      <path d="M9 14h6"></path>
                    </svg>
                  </button>
                  <button className="file-action-button delete-button" onClick={() => handleDelete(node)} title="删除">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* 递归渲染子节点 */}
        {!node.isFile && hasChildren && isExpanded && (
          <div className="tree-children">
            {node.children!.map(child => renderTreeNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  // 创建文件或文件夹
  const handleCreate = async () => {
    if (!newFileName.trim()) {
      await confirm('提示', newFileType === 'file' ? '请输入文件名' : '请输入文件夹名', { confirmText: '确定', type: 'info' });
      return;
    }

    // 构建完整路径（如果有父文件夹）
    const fullPath = parentFolder ? `${parentFolder.path}/${newFileName}` : newFileName;

    setCreateLoading(true);
    try {
      const response = await apiService.createSkillFile(skill.id, fullPath, '', newFileType === 'folder');
      if (response.code === 0) {
        setShowCreateModal(false);
        setNewFileName('');
        setNewFileType('file');
        setParentFolder(null);
        await loadFiles();
      } else {
        await confirm('创建失败', response.message || '创建失败，请稍后重试', { confirmText: '确定', type: 'info' });
      }
    } catch (err) {
      await confirm('创建失败', '网络错误，请稍后重试', { confirmText: '确定', type: 'info' });
      console.error('Failed to create file:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  // 在文件夹下添加文件
  const openAddFileModal = (folder: SkillFile) => {
    setParentFolder(folder);
    setNewFileType('file');
    setNewFileName('');
    setShowCreateModal(true);
  };

  // 在文件夹下添加子文件夹
  const openAddFolderModal = (folder: SkillFile) => {
    setParentFolder(folder);
    setNewFileType('folder');
    setNewFileName('');
    setShowCreateModal(true);
  };

  // 删除文件或文件夹
  const handleDelete = async (file: SkillFile) => {
    const itemType = file.isFile ? '文件' : '文件夹';
    const confirmed = await confirm(
      `删除${itemType}`,
      `确定要删除${itemType} "${file.name}" 吗？此操作不可恢复。`,
      {
        confirmText: '删除',
        cancelText: '取消',
        type: 'danger'
      }
    );
    if (!confirmed) return;

    try {
      const response = await apiService.deleteSkillFile(skill.id, file.path);
      if (response.code === 0) {
        await loadFiles();
      } else {
        await confirm('删除失败', response.message || '删除失败，请稍后重试', {
          confirmText: '确定',
          type: 'info'
        });
      }
    } catch (err) {
      await confirm('删除失败', '网络错误，请稍后重试', {
        confirmText: '确定',
        type: 'info'
      });
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
      const response = await apiService.getSkillFileContent(skill.id, file.path);
      if (response.code === 0) {
        setViewingContent(response.data.content);
      } else {
        await confirm('加载失败', response.message || '加载文件内容失败', { confirmText: '确定', type: 'info' });
        setShowViewModal(false);
      }
    } catch (err) {
      await confirm('加载失败', '网络错误，请稍后重试', { confirmText: '确定', type: 'info' });
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
      const response = await apiService.getSkillFileContent(skill.id, file.path);
      if (response.code === 0) {
        setEditingContent(response.data.content);
      } else {
        await confirm('加载失败', response.message || '加载文件内容失败', { confirmText: '确定', type: 'info' });
        setShowEditModal(false);
      }
    } catch (err) {
      await confirm('加载失败', '网络错误，请稍后重试', { confirmText: '确定', type: 'info' });
      console.error('Failed to load file content:', err);
      setShowEditModal(false);
    }
  };

  // 保存文件内容
  const handleSaveContent = async () => {
    if (!editingFile) return;

    setEditLoading(true);
    try {
      const response = await apiService.updateSkillFile(skill.id, editingFile.path, undefined, editingContent);
      if (response.code === 0) {
        setShowEditModal(false);
        setEditingFile(null);
        await loadFiles();
      } else {
        await confirm('保存失败', response.message || '保存失败，请稍后重试', { confirmText: '确定', type: 'info' });
      }
    } catch (err) {
      await confirm('保存失败', '网络错误，请稍后重试', { confirmText: '确定', type: 'info' });
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
      await confirm('提示', '请输入新文件名', { confirmText: '确定', type: 'info' });
      return;
    }

    setRenameLoading(true);
    try {
      // 构建新路径：保持原有的目录结构，只替换文件名
      const oldPath = renamingFile.path;
      const lastSlashIndex = oldPath.lastIndexOf('/');
      const newPath = lastSlashIndex >= 0
        ? oldPath.substring(0, lastSlashIndex + 1) + renamingFileName.trim()
        : renamingFileName.trim();

      const response = await apiService.updateSkillFile(skill.id, renamingFile.path, newPath);
      if (response.code === 0) {
        setShowRenameModal(false);
        setRenamingFile(null);
        await loadFiles();
      } else {
        await confirm('重命名失败', response.message || '重命名失败，请稍后重试', { confirmText: '确定', type: 'info' });
      }
    } catch (err) {
      await confirm('重命名失败', '网络错误，请稍后重试', { confirmText: '确定', type: 'info' });
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
          <div className="file-tree">
            {treeFiles.map(file => renderTreeNode(file))}
          </div>
        )}
      </div>

      {/* 新建文件模态框 - 仅未发布状态 */}
      {!isReadOnly && showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {parentFolder ? (
                  <span>{newFileType === 'file' ? '添加文件' : '添加子文件夹'} <span style={{ fontSize: '14px', color: '#9ca3af', fontWeight: 'normal' }}>(在 {parentFolder.name} 下)</span></span>
                ) : (
                  <span>{newFileType === 'file' ? '新建文件' : '新建文件夹'}</span>
                )}
              </h2>
              <button className="modal-close-button" onClick={() => {
                setShowCreateModal(false);
                setNewFileType('file');
                setParentFolder(null);
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              {parentFolder && (
                <div className="form-group">
                  <label>父文件夹</label>
                  <div className="parent-path-display">{parentFolder.name}</div>
                </div>
              )}
              {!parentFolder && (
                <div className="form-group">
                  <label>类型</label>
                  <div className="type-selector">
                    <div
                      className={`type-option ${newFileType === 'file' ? 'active' : ''}`}
                      onClick={() => setNewFileType('file')}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                      </svg>
                      文件
                    </div>
                    <div
                      className={`type-option ${newFileType === 'folder' ? 'active' : ''}`}
                      onClick={() => setNewFileType('folder')}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                      </svg>
                      文件夹
                    </div>
                  </div>
                </div>
              )}
              <div className="form-group">
                <label htmlFor="new-file-name">{newFileType === 'file' ? '文件名' : '文件夹名'}</label>
                <input
                  id="new-file-name"
                  type="text"
                  className="form-input"
                  placeholder={newFileType === 'file' ? "例如: config.yaml 或 readme.txt" : "例如: docs 或 configs"}
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                />
                <span className="form-hint">
                  {parentFolder
                    ? `将在 ${parentFolder.name} 下创建`
                    : (newFileType === 'file' ? '支持创建多级路径，例如: folder/file.txt' : '支持创建多级路径，例如: parent/child')
                  }
                </span>
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-button modal-button-secondary" onClick={() => {
                setShowCreateModal(false);
                setNewFileType('file');
                setParentFolder(null);
              }} disabled={createLoading}>
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
        <div className="modal-overlay">
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
        <div className="modal-overlay">
          <div className="modal-content modal-large">
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
        <div className="modal-overlay">
          <div className="modal-content">
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

      <DialogComponent />
    </div>
  );
};
