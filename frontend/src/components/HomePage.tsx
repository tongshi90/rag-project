import React from 'react';
import './HomePage.css';

interface HomePageProps {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onSelectPage }) => {
  return (
    <div className="home-page">
      <div className="home-container">
        <h1 className="home-title">NEXUS</h1>
        <p className="home-subtitle">智能助手平台</p>

        <div className="page-cards">
          <div
            className="page-card"
            onClick={() => onSelectPage('skill')}
          >
            <div className="card-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <h2 className="card-title">Skill 技能</h2>
            <p className="card-description">技能管理 · 模块编排 · 灵活扩展</p>
            <div className="card-arrow">→</div>
          </div>

          <div
            className="page-card page-card-kb"
            onClick={() => onSelectPage('knowledge-base')}
          >
            <div className="card-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5 10 5v2"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>
            <h2 className="card-title">知识库管理</h2>
            <p className="card-description">多库管理 · 分组存储 · 便捷检索</p>
            <div className="card-arrow">→</div>
          </div>
        </div>
      </div>
    </div>
  );
};
