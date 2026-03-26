import React, { useState } from 'react';
import './HomePageDemo2.css';
import { apiService } from '../services/api';

interface HomePageDemo2Props {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePageDemo2: React.FC<HomePageDemo2Props> = ({ onSelectPage }) => {
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
    <div className="abyss-page">
      {/* 右上角清理按钮 */}
      <button
        className="abyss-clear-knowledge-btn"
        onClick={() => setShowConfirm(true)}
        disabled={isClearing}
        title="清空知识库文件数据"
      >
        {isClearing ? (
          <>
            <span className="abyss-spinner"></span>
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
        <div className="abyss-confirm-dialog-overlay" onClick={() => setShowConfirm(false)}>
          <div className="abyss-confirm-dialog" onClick={(e) => e.stopPropagation()}>
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
            <p className="abyss-confirm-note">保留：技能卡片、技能文件</p>
            <div className="abyss-confirm-dialog-actions">
              <button
                className="abyss-confirm-btn-cancel"
                onClick={() => setShowConfirm(false)}
              >
                取消
              </button>
              <button
                className="abyss-confirm-btn-confirm"
                onClick={handleClearKnowledge}
                disabled={isClearing}
              >
                {isClearing ? '清理中...' : '确认清空'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Background Effects */}
      <div className="abyss-bg-grid"></div>
      <div className="abyss-particles">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="abyss-particle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          ></div>
        ))}
      </div>
      <div className="abyss-bg-glow"></div>

      {/* Main Container */}
      <div className="abyss-container">
        {/* Header */}
        <header className="abyss-header">
          <div className="abyss-logo">
            <svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="30" cy="30" r="28" stroke="currentColor" strokeWidth="1" opacity="0.5"/>
              <circle cx="30" cy="30" r="20" stroke="currentColor" strokeWidth="1" opacity="0.3"/>
              <circle cx="30" cy="30" r="12" fill="currentColor" opacity="0.8"/>
            </svg>
          </div>
          <div className="abyss-title">
            <h1 className="abyss-title-main">NEXUS</h1>
            <p className="abyss-title-sub">智能助手平台</p>
          </div>
        </header>

        {/* Cards */}
        <div className="abyss-cards">
          <div
            className="abyss-card"
            onClick={() => onSelectPage('skill')}
          >
            <div className="abyss-card-bg"></div>
            <div className="abyss-card-border"></div>
            <div className="abyss-card-glow"></div>

            <div className="abyss-card-icon-wrapper">
              <div className="abyss-card-icon-ring"></div>
              <svg className="abyss-card-icon" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>

            <div className="abyss-card-content">
              <h2 className="abyss-card-title">Skill 技能</h2>
              <p className="abyss-card-desc">技能管理 · 模块编排 · 灵活扩展</p>
              <div className="abyss-card-stats">
                <span className="abyss-stat-item">
                  <i className="abyss-stat-dot"></i>
                  即插即用
                </span>
                <span className="abyss-stat-item">
                  <i className="abyss-stat-dot"></i>
                  开放架构
                </span>
              </div>
            </div>

            <div className="abyss-card-hover-line"></div>
          </div>

          <div
            className="abyss-card"
            onClick={() => onSelectPage('knowledge-base')}
          >
            <div className="abyss-card-bg"></div>
            <div className="abyss-card-border"></div>
            <div className="abyss-card-glow"></div>

            <div className="abyss-card-icon-wrapper">
              <div className="abyss-card-icon-ring"></div>
              <svg className="abyss-card-icon" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5 10 5v2"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>

            <div className="abyss-card-content">
              <h2 className="abyss-card-title">知识库管理</h2>
              <p className="abyss-card-desc">多库管理 · 分组存储 · 便捷检索</p>
              <div className="abyss-card-stats">
                <span className="abyss-stat-item">
                  <i className="abyss-stat-dot"></i>
                  独立隔离
                </span>
                <span className="abyss-stat-item">
                  <i className="abyss-stat-dot"></i>
                  灵活组织
                </span>
              </div>
            </div>

            <div className="abyss-card-hover-line"></div>
          </div>
        </div>

        {/* Footer */}
        <footer className="abyss-footer">
          <div className="abyss-footer-line"></div>
        </footer>
      </div>
    </div>
  );
};
