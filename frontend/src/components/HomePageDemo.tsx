import React from 'react';
import './HomePageDemo.css';

interface HomePageDemoProps {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePageDemo: React.FC<HomePageDemoProps> = ({ onSelectPage }) => {
  return (
    <div className="demo-page">
      {/* Background Effects */}
      <div className="demo-bg-grid"></div>
      <div className="demo-bg-noise"></div>
      <div className="demo-bg-glow"></div>

      {/* Main Container */}
      <div className="demo-container">
        {/* Header */}
        <header className="demo-header">
          <div className="demo-logo">
            <div className="logo-cube">
              <div className="cube-face cube-front"></div>
              <div className="cube-face cube-back"></div>
              <div className="cube-face cube-right"></div>
              <div className="cube-face cube-left"></div>
              <div className="cube-face cube-top"></div>
              <div className="cube-face cube-bottom"></div>
            </div>
          </div>
          <div className="demo-title">
            <h1 className="title-main">NEXUS</h1>
            <p className="title-sub">智能助手平台</p>
          </div>
        </header>

        {/* Cards */}
        <div className="demo-cards">
          <div
            className="demo-card demo-card-skill"
            onClick={() => onSelectPage('skill')}
          >
            <div className="card-bg-gradient"></div>
            <div className="card-border-effect"></div>
            <div className="card-glow"></div>

            <div className="card-icon-wrapper">
              <div className="card-icon-ring"></div>
              <svg className="card-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>

            <div className="card-content">
              <h2 className="card-title">Skill 技能</h2>
              <p className="card-desc">技能管理 · 模块编排 · 灵活扩展</p>
              <div className="card-stats">
                <span className="stat-item">
                  <i className="stat-dot"></i>
                  即插即用
                </span>
                <span className="stat-item">
                  <i className="stat-dot"></i>
                  开放架构
                </span>
              </div>
            </div>

            <div className="card-hover-line"></div>
          </div>

          <div
            className="demo-card demo-card-kb"
            onClick={() => onSelectPage('knowledge-base')}
          >
            <div className="card-bg-gradient"></div>
            <div className="card-border-effect"></div>
            <div className="card-glow"></div>

            <div className="card-icon-wrapper">
              <div className="card-icon-ring"></div>
              <svg className="card-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5 10 5v2"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>

            <div className="card-content">
              <h2 className="card-title">知识库管理</h2>
              <p className="card-desc">多库管理 · 分组存储 · 便捷检索</p>
              <div className="card-stats">
                <span className="stat-item">
                  <i className="stat-dot"></i>
                  独立隔离
                </span>
                <span className="stat-item">
                  <i className="stat-dot"></i>
                  灵活组织
                </span>
              </div>
            </div>

            <div className="card-hover-line"></div>
          </div>
        </div>

        {/* Footer */}
        <footer className="demo-footer">
          <div className="footer-line"></div>
        </footer>
      </div>
    </div>
  );
};
