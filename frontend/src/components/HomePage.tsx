import React, { useState } from 'react';
import './HomePage.css';
import { apiService } from '../services/api';

interface HomePageProps {
  onSelectPage: (page: 'skill' | 'knowledge-base') => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onSelectPage }) => {
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
    <div className="home-page">
      {/* 右上角清理按钮 */}
      <button
        className="clear-knowledge-btn"
        onClick={() => setShowConfirm(true)}
        disabled={isClearing}
        title="清空知识库文件数据"
      >
        {isClearing ? (
          <>
            <span className="spinner"></span>
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
        <div className="confirm-dialog-overlay" onClick={() => setShowConfirm(false)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
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
            <p className="confirm-note">保留：技能卡片、技能文件</p>
            <div className="confirm-dialog-actions">
              <button
                className="confirm-btn-cancel"
                onClick={() => setShowConfirm(false)}
              >
                取消
              </button>
              <button
                className="confirm-btn-confirm"
                onClick={handleClearKnowledge}
                disabled={isClearing}
              >
                {isClearing ? '清理中...' : '确认清空'}
              </button>
            </div>
          </div>
        </div>
      )}

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
