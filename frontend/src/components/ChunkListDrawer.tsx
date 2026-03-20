import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { FileChunk } from '../types';
import './ChunkListDrawer.css';

interface ChunkListDrawerProps {
  isOpen: boolean;
  kbId: string;
  fileId: string;
  fileName: string;
  onClose: () => void;
}

export const ChunkListDrawer: React.FC<ChunkListDrawerProps> = ({
  isOpen,
  kbId,
  fileId,
  fileName,
  onClose
}) => {
  const [chunks, setChunks] = useState<FileChunk[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedChunk, setSelectedChunk] = useState<FileChunk | null>(null);

  // 加载 chunk 列表
  const loadChunks = async () => {
    if (!isOpen) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.getFileChunks(kbId, fileId);
      if (response.success && response.data) {
        setChunks(response.data.chunks);
      } else {
        setError(response.error || '加载失败');
      }
    } catch (err) {
      console.error('Failed to load chunks:', err);
      setError('加载 chunk 列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadChunks();
  }, [isOpen, kbId, fileId]);

  // 过滤 chunks
  const filteredChunks = chunks.filter(chunk =>
    chunk.text.toLowerCase().includes(searchKeyword.toLowerCase()) ||
    chunk.type.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  // 获取类型标签样式
  const getTypeBadgeClass = (type: string): string => {
    switch (type) {
      case 'text':
        return 'chunk-type-badge chunk-type-text';
      case 'table':
        return 'chunk-type-badge chunk-type-table';
      case 'image':
        return 'chunk-type-badge chunk-type-image';
      default:
        return 'chunk-type-badge';
    }
  };

  // 获取类型显示名称
  const getTypeDisplayName = (type: string): string => {
    switch (type) {
      case 'text':
        return '文本';
      case 'table':
        return '表格';
      case 'image':
        return '图片';
      default:
        return type;
    }
  };

  return (
    <>
      {isOpen && (
        <div className="drawer-overlay">
          <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
            {/* 头部 */}
            <div className="drawer-header">
              <div className="drawer-title-section">
                <h2 className="drawer-title">文件分块详情</h2>
                <p className="drawer-subtitle">{fileName}</p>
              </div>
              <button className="drawer-close-button" onClick={onClose}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* 统计信息 */}
            <div className="drawer-stats">
              <div className="drawer-stat-item">
                <span className="drawer-stat-value">{chunks.length}</span>
                <span className="drawer-stat-label">分块总数</span>
              </div>
              <div className="drawer-stat-item">
                <span className="drawer-stat-value">
                  {chunks.reduce((sum, c) => sum + c.length, 0).toLocaleString()}
                </span>
                <span className="drawer-stat-label">总字符数</span>
              </div>
              <div className="drawer-stat-item">
                <span className="drawer-stat-value">
                  {Math.max(...chunks.map(c => c.page))}
                </span>
                <span className="drawer-stat-label">最大页码</span>
              </div>
            </div>

            {/* 搜索栏 */}
            <div className="drawer-search">
              <div className="drawer-search-input-wrapper">
                <svg className="drawer-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="M21 21l-4.35-4.35"></path>
                </svg>
                <input
                  type="text"
                  className="drawer-search-input"
                  placeholder="搜索分块内容..."
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                />
                {searchKeyword && (
                  <button
                    className="drawer-search-clear"
                    onClick={() => setSearchKeyword('')}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                )}
              </div>
              {searchKeyword && (
                <div className="drawer-search-results">
                  找到 {filteredChunks.length} 个结果
                </div>
              )}
            </div>

            {/* Chunk 列表 */}
            <div className="drawer-chunk-list">
              {isLoading ? (
                <div className="drawer-loading">
                  <div className="drawer-loading-spinner"></div>
                  <p>加载中...</p>
                </div>
              ) : error ? (
                <div className="drawer-error">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                  <p>{error}</p>
                  <button className="drawer-retry-button" onClick={loadChunks}>
                    重试
                  </button>
                </div>
              ) : filteredChunks.length === 0 ? (
                <div className="drawer-empty">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="M21 21l-4.35-4.35"></path>
                  </svg>
                  <p>{searchKeyword ? '没有找到匹配的分块' : '该文件暂无分块数据'}</p>
                </div>
              ) : (
                <div className="drawer-chunk-items">
                  {filteredChunks.map((chunk) => (
                    <div
                      key={chunk.chunkId}
                      className="drawer-chunk-item"
                      onClick={() => setSelectedChunk(selectedChunk?.chunkId === chunk.chunkId ? null : chunk)}
                    >
                      <div className="drawer-chunk-header">
                        <div className="drawer-chunk-order">
                          <span className="drawer-chunk-number">#{chunk.order + 1}</span>
                          <span className={getTypeBadgeClass(chunk.type)}>
                            {getTypeDisplayName(chunk.type)}
                          </span>
                        </div>
                        <div className="drawer-chunk-meta">
                          <span className="drawer-chunk-page">第 {chunk.page} 页</span>
                          <span className="drawer-chunk-length">{chunk.length} 字符</span>
                        </div>
                      </div>
                      <div className="drawer-chunk-text">
                        {selectedChunk?.chunkId === chunk.chunkId
                          ? chunk.text
                          : (chunk.text.length > 150
                              ? chunk.text.substring(0, 150) + '...'
                              : chunk.text)
                        }
                      </div>
                      {chunk.text.length > 150 && selectedChunk?.chunkId !== chunk.chunkId && (
                        <div className="drawer-chunk-expand">
                          点击展开全部
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 底部信息 */}
            {chunks.length > 0 && (
              <div className="drawer-footer">
                <span>共 {filteredChunks.length} 个分块</span>
                {searchKeyword && <span>（搜索结果）</span>}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
