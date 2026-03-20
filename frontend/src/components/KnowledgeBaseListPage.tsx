import React, { useState, useEffect } from 'react';
import { useConfirmDialog } from './ConfirmDialog';
import { apiService } from '../services/api';
import type { KnowledgeBase } from '../types';
import './KnowledgeBaseListPage.css';

interface KnowledgeBaseListPageProps {
  onBackToHome: () => void;
  onSelectKnowledgeBase: (kb: KnowledgeBase) => void;
}

export const KnowledgeBaseListPage: React.FC<KnowledgeBaseListPageProps> = ({
  onBackToHome: _onBackToHome,
  onSelectKnowledgeBase
}) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [newKbDescription, setNewKbDescription] = useState('');
  const [editingKb, setEditingKb] = useState<KnowledgeBase | null>(null);

  // 确认弹窗
  const { confirm, DialogComponent } = useConfirmDialog();
  const [searchKeyword, setSearchKeyword] = useState('');

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.getKnowledgeBases();
      if (response.success && response.data) {
        setKnowledgeBases(response.data.knowledgeBases);
      }
    } catch (error) {
      console.error('Failed to load knowledge bases:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  // 过滤知识库
  const filteredKnowledgeBases = knowledgeBases.filter(kb =>
    kb.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
    (kb.description && kb.description.toLowerCase().includes(searchKeyword.toLowerCase()))
  );

  // 创建知识库
  const handleCreateKnowledgeBase = async () => {
    if (!newKbName.trim()) return;

    try {
      const response = await apiService.createKnowledgeBase({
        name: newKbName.trim(),
        description: newKbDescription.trim()
      });

      if (response.success && response.data) {
        setShowCreateModal(false);
        setNewKbName('');
        setNewKbDescription('');
        loadKnowledgeBases();
      } else {
        alert(response.error || '创建失败');
      }
    } catch (error) {
      console.error('Failed to create knowledge base:', error);
      alert('创建知识基失败');
    }
  };

  // 更新知识库
  const handleUpdateKnowledgeBase = async () => {
    if (!editingKb || !newKbName.trim()) return;

    try {
      const response = await apiService.updateKnowledgeBase(editingKb.id, {
        name: newKbName.trim(),
        description: newKbDescription.trim()
      });

      if (response.success && response.data) {
        setShowCreateModal(false);
        setEditingKb(null);
        setNewKbName('');
        setNewKbDescription('');
        loadKnowledgeBases();
      } else {
        alert(response.error || '更新失败');
      }
    } catch (error) {
      console.error('Failed to update knowledge base:', error);
      alert('更新知识基失败');
    }
  };

  // 删除知识库
  const handleDeleteKnowledgeBase = async (kb: KnowledgeBase) => {
    const confirmed = await confirm(
      '删除知识库',
      `确定要删除知识库 "${kb.name}" 吗？此操作不可恢复。`,
      {
        confirmText: '删除',
        cancelText: '取消',
        type: 'danger'
      }
    );
    if (!confirmed) return;

    try {
      const response = await apiService.deleteKnowledgeBase(kb.id);
      if (response.success) {
        loadKnowledgeBases();
      } else {
        await confirm('删除失败', response.error || '删除知识库失败，请稍后重试', {
          confirmText: '确定',
          type: 'info'
        });
      }
    } catch (error) {
      console.error('Failed to delete knowledge base:', error);
      await confirm('删除失败', '删除知识库失败，请稍后重试', {
        confirmText: '确定',
        type: 'info'
      });
    }
  };

  // 打开创建弹窗
  const openCreateModal = () => {
    setNewKbName('');
    setNewKbDescription('');
    setEditingKb(null);
    setShowCreateModal(true);
  };

  // 打开编辑弹窗
  const openEditModal = (kb: KnowledgeBase) => {
    setNewKbName(kb.name);
    setNewKbDescription(kb.description || '');
    setEditingKb(kb);
    setShowCreateModal(true);
  };

  // 格式化日期
  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="kb-list-page bg-cybergrid">
      {/* Background Effects */}
      <div className="bg-preview-bg"></div>
      <div className="bg-preview-glow"></div>

      <div className="kb-content">
        {/* 搜索栏 */}
        <div className="search-bar">
          <div className="search-input-wrapper">
            <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="M21 21l-4.35-4.35"></path>
            </svg>
            <input
              type="text"
              className="search-input"
              placeholder="搜索知识库名称或描述..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
            />
            {searchKeyword && (
              <button
                className="clear-button"
                onClick={() => setSearchKeyword('')}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            )}
          </div>
          <button className="add-kb-button" onClick={openCreateModal}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>创建知识库</span>
          </button>
        </div>

        {/* 知识库卡片列表 */}
        <div className="kb-cards-container">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>加载中...</p>
            </div>
          ) : filteredKnowledgeBases.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5 10 5v2"></path>
                  <path d="M2 17l10 5 10-5"></path>
                  <path d="M2 12l10 5 10-5"></path>
                </svg>
              </div>
              <h2 className="empty-title">
                {searchKeyword ? '未找到匹配的知识库' : '暂无知识库'}
              </h2>
              <p className="empty-description">
                {searchKeyword ? '请尝试其他关键词' : '点击上方"创建知识库"按钮创建第一个知识库'}
              </p>
            </div>
          ) : (
            <div className="kb-cards-grid">
              {filteredKnowledgeBases.map(kb => (
                <div
                  key={kb.id}
                  className="kb-card"
                  onClick={() => onSelectKnowledgeBase(kb)}
                >
                  <div className="card-hover-line"></div>
                  <div className="kb-card-header">
                    <h3 className="kb-card-title">{kb.name}</h3>
                    <div className="kb-card-actions" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="edit-button"
                        onClick={() => openEditModal(kb)}
                        title="编辑"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                      <button
                        className="delete-button"
                        onClick={() => handleDeleteKnowledgeBase(kb)}
                        title="删除"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                  <p className="kb-card-description" data-tooltip={kb.description}>{kb.description || '暂无描述'}</p>
                  <div className="kb-card-footer">
                    <span className="kb-card-meta">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                      </svg>
                      {kb.fileCount || 0} 个文件
                    </span>
                    <span className="kb-card-meta">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                      </svg>
                      {formatDate(kb.createdAt)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 统计信息 */}
          {knowledgeBases.length > 0 && (
            <div className="kb-stats">
              共 {filteredKnowledgeBases.length} 个知识库
              {searchKeyword && ` (搜索: "${searchKeyword}")`}
            </div>
          )}
        </div>
      </div>

      {/* 创建/编辑模态框 */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingKb ? '编辑知识库' : '创建知识库'}</h2>
              <button
                className="modal-close-button"
                onClick={() => setShowCreateModal(false)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <form onSubmit={(e) => {
                e.preventDefault();
                if (editingKb) {
                  handleUpdateKnowledgeBase();
                } else {
                  handleCreateKnowledgeBase();
                }
              }}>
                <div className="form-group">
                  <label htmlFor="kb-name">名称 *</label>
                  <input
                    id="kb-name"
                    type="text"
                    className="form-input"
                    placeholder="输入知识库名称"
                    value={newKbName}
                    onChange={(e) => setNewKbName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="kb-description">描述</label>
                  <textarea
                    id="kb-description"
                    className="form-textarea"
                    placeholder="输入知识库描述（可选）"
                    rows={4}
                    value={newKbDescription}
                    onChange={(e) => setNewKbDescription(e.target.value)}
                  />
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="modal-button modal-button-secondary"
                    onClick={() => setShowCreateModal(false)}
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="modal-button modal-button-primary"
                  >
                    {editingKb ? '保存' : '创建'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      <DialogComponent />
    </div>
  );
};
