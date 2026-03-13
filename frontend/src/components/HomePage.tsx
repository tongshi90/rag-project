import React from 'react';
import './HomePage.css';

interface HomePageProps {
  onSelectPage: (page: 'rag' | 'skill') => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onSelectPage }) => {
  return (
    <div className="home-page">
      <div className="home-container">
        <h1 className="home-title">智能助手平台</h1>
        <p className="home-subtitle">请选择功能模块</p>

        <div className="page-cards">
          <div
            className="page-card"
            onClick={() => onSelectPage('rag')}
          >
            <div className="card-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <h2 className="card-title">RAG 知识库</h2>
            <p className="card-description">上传文档，基于知识库内容进行智能问答</p>
            <div className="card-arrow">→</div>
          </div>

          <div
            className="page-card"
            onClick={() => onSelectPage('skill')}
          >
            <div className="card-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <h2 className="card-title">Skill 技能列表</h2>
            <p className="card-description">管理和使用各类智能技能</p>
            <div className="card-arrow">→</div>
          </div>
        </div>
      </div>
    </div>
  );
};
