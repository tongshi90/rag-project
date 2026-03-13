import React, { useState, useEffect } from 'react';
import './SkillListPage.css';
import { apiService } from '../services/api';
import type { SkillCard, SkillCardCreateRequest, SkillCardUpdateRequest } from '../types';

interface SkillListPageProps {
  onBackToHome: () => void;
  onSelectSkill?: (skill: SkillCard) => void;
}

export const SkillListPage: React.FC<SkillListPageProps> = ({ onBackToHome, onSelectSkill }) => {
  const [skills, setSkills] = useState<SkillCard[]>([]);
  const [filteredSkills, setFilteredSkills] = useState<SkillCard[]>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 创建模态框状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSkill, setNewSkill] = useState<SkillCardCreateRequest>({
    title: '',
    description: '',
    skillCode: '',
  });
  const [createLoading, setCreateLoading] = useState(false);

  // 编辑模态框状态
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingSkill, setEditingSkill] = useState<SkillCard | null>(null);
  const [editLoading, setEditLoading] = useState(false);

  // 技能 Code 格式验证（只允许英文、数字、下划线、中划线）
  const handleSkillCodeChange = (value: string) => {
    const filtered = value.replace(/[^a-zA-Z0-9_-]/g, '');
    setNewSkill({ ...newSkill, skillCode: filtered });
  };

  // 加载技能卡片列表
  const loadSkills = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getSkillCards();
      if (response.code === 0) {
        setSkills(response.data);
        setFilteredSkills(response.data);
      } else {
        setError(response.message || '加载失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
      console.error('Failed to load skills:', err);
    } finally {
      setLoading(false);
    }
  };

  // 搜索技能卡片
  const handleSearch = async (keyword: string) => {
    setSearchKeyword(keyword);
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getSkillCards(keyword);
      if (response.code === 0) {
        setFilteredSkills(response.data);
      } else {
        setError(response.message || '搜索失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
      console.error('Failed to search skills:', err);
    } finally {
      setLoading(false);
    }
  };

  // 打开编辑模态框
  const openEditModal = (skill: SkillCard) => {
    setEditingSkill(skill);
    setShowEditModal(true);
  };

  // 创建技能卡片
  const handleCreateSkill = async () => {
    if (!newSkill.title.trim()) {
      alert('请输入技能标题');
      return;
    }
    if (!newSkill.description.trim()) {
      alert('请输入技能描述');
      return;
    }
    if (!newSkill.skillCode.trim()) {
      alert('请输入技能 Code');
      return;
    }

    setCreateLoading(true);
    try {
      const response = await apiService.createSkillCard(newSkill);
      if (response.code === 0) {
        setShowCreateModal(false);
        setNewSkill({ title: '', description: '', skillCode: '' });
        await loadSkills();
      } else {
        alert(response.message || '创建失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to create skill:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  // 更新技能卡片
  const handleUpdateSkill = async () => {
    if (!editingSkill) return;

    if (!editingSkill.title.trim()) {
      alert('请输入技能标题');
      return;
    }
    if (!editingSkill.description.trim()) {
      alert('请输入技能描述');
      return;
    }

    setEditLoading(true);
    try {
      const updateRequest: SkillCardUpdateRequest = {
        title: editingSkill.title,
        description: editingSkill.description,
      };
      const response = await apiService.updateSkillCard(editingSkill.id, updateRequest);
      if (response.code === 0) {
        setShowEditModal(false);
        setEditingSkill(null);
        await loadSkills();
      } else {
        alert(response.message || '更新失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to update skill:', err);
    } finally {
      setEditLoading(false);
    }
  };

  // 删除技能卡片
  const handleDelete = async (cardId: string) => {
    // 检查技能是否已发布
    const skill = skills.find(s => s.id === cardId);
    if (skill && skill.published) {
      alert('已发布的技能不能删除，请先取消发布');
      return;
    }

    if (!confirm('确定要删除这个技能卡片吗？')) {
      return;
    }

    try {
      const response = await apiService.deleteSkillCard(cardId);
      if (response.code === 0) {
        await loadSkills();
      } else {
        alert(response.message || '删除失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to delete skill:', err);
    }
  };

  // 发布技能
  const handlePublish = async (cardId: string) => {
    try {
      const response = await apiService.publishSkillCard(cardId);
      if (response.code === 0) {
        await loadSkills();
      } else {
        alert(response.message || '发布失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to publish skill:', err);
    }
  };

  // 取消发布技能
  const handleUnpublish = async (cardId: string) => {
    try {
      const response = await apiService.unpublishSkillCard(cardId);
      if (response.code === 0) {
        await loadSkills();
      } else {
        alert(response.message || '取消发布失败');
      }
    } catch (err) {
      alert('网络错误，请稍后重试');
      console.error('Failed to unpublish skill:', err);
    }
  };

  // 组件挂载时加载数据
  useEffect(() => {
    loadSkills();
  }, []);

  return (
    <div className="skill-list-page">
      <header className="skill-header">
        <button className="back-button" onClick={onBackToHome}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"></path>
          </svg>
          返回首页
        </button>
        <h1 className="skill-title">Skill 技能列表</h1>
        <button className="add-skill-button" onClick={() => setShowCreateModal(true)}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加技能
        </button>
      </header>

      <div className="skill-content">
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
              placeholder="搜索技能标题或描述..."
              value={searchKeyword}
              onChange={(e) => handleSearch(e.target.value)}
            />
            {searchKeyword && (
              <button
                className="clear-button"
                onClick={() => handleSearch('')}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* 技能卡片列表 */}
        <div className="skill-cards-container">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>加载中...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <p>{error}</p>
              <button className="retry-button" onClick={loadSkills}>重试</button>
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                  <polyline points="2 17 12 22 22 17"></polyline>
                  <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
              </div>
              <h2 className="empty-title">
                {searchKeyword ? '未找到匹配的技能' : '暂无技能'}
              </h2>
              <p className="empty-description">
                {searchKeyword ? '请尝试其他关键词' : '点击上方"添加技能"按钮创建第一个技能'}
              </p>
            </div>
          ) : (
            <div className="skill-cards-grid">
              {filteredSkills.map((skill) => (
                <div key={skill.id} className="skill-card" onClick={() => {
                  console.log('Card clicked:', skill.title);
                  if (onSelectSkill) {
                    onSelectSkill(skill);
                  }
                }}>
                  <div className="skill-card-header">
                    <h3 className="skill-card-title">{skill.title}</h3>
                    <div className="skill-card-actions" onClick={(e) => e.stopPropagation()}>
                      {skill.published ? (
                        <button
                          className="unpublish-button"
                          onClick={() => handleUnpublish(skill.id)}
                          title="取消发布"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                          </svg>
                          已发布
                        </button>
                      ) : (
                        <button
                          className="publish-button"
                          onClick={() => handlePublish(skill.id)}
                          title="发布"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polygon points="12 2 15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2"/>
                          </svg>
                          发布
                        </button>
                      )}
                      <button
                        className="edit-button"
                        onClick={() => openEditModal(skill)}
                        title="编辑"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                      <button
                        className={`delete-button ${skill.published ? 'disabled' : ''}`}
                        onClick={() => handleDelete(skill.id)}
                        title={skill.published ? '已发布技能不能删除' : '删除'}
                        disabled={skill.published}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                  <p className="skill-card-description">{skill.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 统计信息 */}
        {skills.length > 0 && (
          <div className="skill-stats">
            共 {filteredSkills.length} 个技能
            {searchKeyword && ` (搜索: "${searchKeyword}")`}
          </div>
        )}
      </div>

      {/* 创建技能模态框 */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>添加技能</h2>
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
              <div className="form-group">
                <label htmlFor="skill-title">技能标题 *</label>
                <input
                  id="skill-title"
                  type="text"
                  className="form-input"
                  placeholder="请输入技能标题"
                  value={newSkill.title}
                  onChange={(e) => setNewSkill({ ...newSkill, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label htmlFor="skill-description">技能描述 *</label>
                <textarea
                  id="skill-description"
                  className="form-textarea"
                  placeholder="请输入技能描述"
                  rows={4}
                  value={newSkill.description}
                  onChange={(e) => setNewSkill({ ...newSkill, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label htmlFor="skill-code">技能 Code *</label>
                <input
                  id="skill-code"
                  type="text"
                  className="form-input"
                  placeholder="仅限英文、数字、下划线、中划线"
                  value={newSkill.skillCode}
                  onChange={(e) => handleSkillCodeChange(e.target.value)}
                />
                <span className="form-hint">只能输入英文、数字、下划线、中划线（不区分大小写），创建后不可修改</span>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="modal-button modal-button-secondary"
                onClick={() => setShowCreateModal(false)}
                disabled={createLoading}
              >
                取消
              </button>
              <button
                className="modal-button modal-button-primary"
                onClick={handleCreateSkill}
                disabled={createLoading}
              >
                {createLoading ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑技能模态框 */}
      {showEditModal && editingSkill && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>编辑技能</h2>
              <button
                className="modal-close-button"
                onClick={() => setShowEditModal(false)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="edit-skill-title">技能标题 *</label>
                <input
                  id="edit-skill-title"
                  type="text"
                  className="form-input"
                  placeholder="请输入技能标题"
                  value={editingSkill.title}
                  onChange={(e) => setEditingSkill({ ...editingSkill, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label htmlFor="edit-skill-description">技能描述 *</label>
                <textarea
                  id="edit-skill-description"
                  className="form-textarea"
                  placeholder="请输入技能描述"
                  rows={4}
                  value={editingSkill.description}
                  onChange={(e) => setEditingSkill({ ...editingSkill, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>技能 Code</label>
                <input
                  type="text"
                  className="form-input"
                  value={editingSkill.skillCode}
                  disabled
                />
                <span className="form-hint">技能 Code 创建后不可修改</span>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="modal-button modal-button-secondary"
                onClick={() => setShowEditModal(false)}
                disabled={editLoading}
              >
                取消
              </button>
              <button
                className="modal-button modal-button-primary"
                onClick={handleUpdateSkill}
                disabled={editLoading}
              >
                {editLoading ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
