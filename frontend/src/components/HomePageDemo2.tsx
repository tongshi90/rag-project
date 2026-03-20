import React from 'react';
import './HomePageDemo2.css';

interface HomePageDemo2Props {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePageDemo2: React.FC<HomePageDemo2Props> = ({ onSelectPage }) => {
  return (
    <div className="abyss-page">
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
