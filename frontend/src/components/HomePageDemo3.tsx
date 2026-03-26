import React, { useState } from 'react';
import './HomePageDemo3.css';
import { apiService } from '../services/api';

interface HomePageDemo3Props {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePageDemo3: React.FC<HomePageDemo3Props> = ({ onSelectPage }) => {
  const [isClearing, setIsClearing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClearKnowledge = async () => {
    setIsClearing(true);
    try {
      const result = await apiService.clearKnowledgeData();
      if (result.success) {
        alert(`知识库数据已清空！\n\n已清理：\n${result.cleared.join('\n')}`);
      } else {
        alert(`清理失败：${result.errors?.join('\n') || '未知错误'}`);
      }
    } catch (error) {
      alert(`清理失败：${error}`);
    } finally {
      setIsClearing(false);
      setShowConfirm(false);
    }
  };

  return (
    <div className="bg-preview-page bg-cybergrid">
      {/* 右上角清理按钮 */}
      <button
        className="bg-preview-clear-knowledge-btn"
        onClick={() => setShowConfirm(true)}
        disabled={isClearing}
        title="清空知识库文件数据"
      >
        {isClearing ? (
          <>
            <span className="bg-preview-spinner"></span>
            清理中...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
            </svg>
            清空知识库
          </>
        )}
      </button>

      {/* 确认对话框 */}
      {showConfirm && (
        <div className="bg-preview-confirm-dialog-overlay" onClick={() => setShowConfirm(false)}>
          <div className="bg-preview-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>确认清空知识库？</h3>
            <p>此操作将删除以下内容：</p>
            <ul>
              <li>向量数据库中的所有向量</li>
              <li>知识图谱数据</li>
              <li>关键字索引</li>
              <li>所有上传的文件</li>
              <li>文件数据库记录</li>
              <li>知识库分组</li>
            </ul>
            <p className="bg-preview-confirm-note">保留：技能卡片、技能文件</p>
            <div className="bg-preview-confirm-dialog-actions">
              <button
                className="bg-preview-confirm-btn-cancel"
                onClick={() => setShowConfirm(false)}
              >
                取消
              </button>
              <button
                className="bg-preview-confirm-btn-confirm"
                onClick={handleClearKnowledge}
                disabled={isClearing}
              >
                {isClearing ? '清理中...' : '确认清空'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Background Elements */}
      <div className="bg-preview-bg"></div>
      <div className="bg-preview-glow"></div>

      {/* Main Container */}
      <div className="bg-preview-container">
        {/* Header */}
        <header className="bg-preview-header">
          <div className="bg-preview-logo">
            <div className="cube-face cube-front"></div>
            <div className="cube-face cube-back"></div>
            <div className="cube-face cube-right"></div>
            <div className="cube-face cube-left"></div>
            <div className="cube-face cube-top"></div>
            <div className="cube-face cube-bottom"></div>
          </div>
          <h1 className="bg-preview-title">NEXUS</h1>
          <p className="bg-preview-subtitle">智能助手平台</p>
        </header>

        {/* Cards */}
        <div className="bg-preview-cards">
          <div
            className="bg-preview-card bg-preview-card-skill"
            onClick={() => onSelectPage('skill')}
          >
            <div className="bg-preview-card-glow-bg"></div>
            <div className="bg-preview-card-icon-wrapper">
              <div className="bg-preview-card-icon-ring"></div>
              <svg className="bg-preview-card-icon" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <h2 className="bg-preview-card-title">Skill 技能</h2>
            <p className="bg-preview-card-desc">技能管理 · 模块编排 · 灵活扩展</p>
            <div className="bg-preview-card-stats">
              <span className="bg-preview-stat-item">
                <i className="bg-preview-stat-dot"></i>
                即插即用
              </span>
              <span className="bg-preview-stat-item">
                <i className="bg-preview-stat-dot"></i>
                开放架构
              </span>
            </div>
            <div className="bg-preview-card-hover-line"></div>
          </div>

          <div
            className="bg-preview-card bg-preview-card-kb"
            onClick={() => onSelectPage('knowledge-base')}
          >
            <div className="bg-preview-card-glow-bg"></div>
            <div className="bg-preview-card-icon-wrapper">
              <div className="bg-preview-card-icon-ring"></div>
              <svg className="bg-preview-card-icon" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5 10 5v2"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>
            <h2 className="bg-preview-card-title">知识库管理</h2>
            <p className="bg-preview-card-desc">多库管理 · 分组存储 · 便捷检索</p>
            <div className="bg-preview-card-stats">
              <span className="bg-preview-stat-item">
                <i className="bg-preview-stat-dot"></i>
                独立隔离
              </span>
              <span className="bg-preview-stat-item">
                <i className="bg-preview-stat-dot"></i>
                灵活组织
              </span>
            </div>
            <div className="bg-preview-card-hover-line"></div>
          </div>
        </div>

        {/* Footer */}
        <footer className="bg-preview-footer">
          <div className="bg-preview-footer-line"></div>
        </footer>
      </div>
    </div>
  );
};
