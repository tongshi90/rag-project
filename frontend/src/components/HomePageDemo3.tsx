import React from 'react';
import './HomePageDemo3.css';

interface HomePageDemo3Props {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePageDemo3: React.FC<HomePageDemo3Props> = ({ onSelectPage }) => {
  return (
    <div className="bg-preview-page bg-cybergrid">
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
