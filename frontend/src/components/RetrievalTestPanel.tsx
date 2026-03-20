import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import type { RetrievalTestRequest, RetrievalTestResponse } from '../types';
import './RetrievalTestPanel.css';

interface RetrievalTestPanelProps {
  kbId: string;
  onTestSubmit?: (query: string) => void;
}

export interface RetrievalTestPanelRef {
  setQuery: (query: string) => void;
}

export const RetrievalTestPanel = forwardRef<RetrievalTestPanelRef, RetrievalTestPanelProps>(
  ({ kbId, onTestSubmit }, ref) => {
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<RetrievalTestResponse | null>(null);
    const resultsEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
      setQuery: (query: string) => {
        setInputValue(query);
      }
    }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const query = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // 通知父组件添加到历史记录
    onTestSubmit?.(query);

    try {
      const request: RetrievalTestRequest = {
        query,
        kbId,
        topK: 5,
        retrievalTopK: 20
      };

      // 调用召回测试API
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'}/api/retrieval-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      const data = await response.json();

      if (data.success && data.data) {
        setResults(data.data);
      } else {
        alert(data.error || '召回测试失败');
      }
    } catch (error) {
      console.error('Retrieval test failed:', error);
      alert('召回测试失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="retrieval-panel">
      <div className="retrieval-container" ref={containerRef}>
        {results === null && !isLoading && (
          <div className="retrieval-empty-state">
            <div className="retrieval-empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            <div className="retrieval-empty-text">输入查询文本进行召回测试</div>
            <div className="retrieval-empty-hint">
              召回测试将返回与查询相关的文档片段（chunks），帮助您评估检索效果
            </div>
          </div>
        )}

        {results && (
          <div className="retrieval-results">
            <div className="retrieval-query-header">
              <div className="retrieval-query-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
              </div>
              <div className="retrieval-query-text">{results.query}</div>
            </div>

            {results.message ? (
              <div className="retrieval-message">
                {results.message}
              </div>
            ) : (
              <>
                <div className="retrieval-count">
                  找到 {results.total} 个相关片段
                </div>
                {results.chunks.map((chunk, index) => (
                  <div key={chunk.chunkId || index} className="retrieval-chunk-card">
                    <div className="chunk-card-header">
                      <div className="chunk-card-id">
                        <span className="chunk-id-label">Chunk ID:</span>
                        <span className="chunk-id-value">{chunk.chunkId || 'N/A'}</span>
                      </div>
                      <div className="chunk-card-scores">
                        <span className="chunk-score">
                          <span className="score-label">原始分数:</span>
                          <span className="score-value">{(chunk.score ?? 0).toFixed(4)}</span>
                        </span>
                        {chunk.rerankScore !== undefined && (
                          <span className="chunk-score">
                            <span className="score-label">重排分数:</span>
                            <span className="score-value">{chunk.rerankScore.toFixed(4)}</span>
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="chunk-card-content">
                      {chunk.text || '无内容'}
                    </div>
                    <div className="chunk-card-metadata">
                      <span className="metadata-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        文档 ID: {chunk.metadata?.docId || 'N/A'}
                      </span>
                      <span className="metadata-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        页码: {chunk.metadata?.page ?? 'N/A'}
                      </span>
                      <span className="metadata-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"></path>
                        </svg>
                        序号: {chunk.metadata?.order ?? 'N/A'}
                      </span>
                      <span className="metadata-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                        类型: {chunk.metadata?.type || 'N/A'}
                      </span>
                      <span className="metadata-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        长度: {chunk.metadata?.length ?? 'N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {isLoading && (
          <div className="retrieval-loading">
            <div className="retrieval-query-header">
              <div className="retrieval-query-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
              </div>
              <div className="retrieval-query-text">{inputValue}</div>
            </div>
            <div className="retrieval-loading-spinner">
              <div className="spinner"></div>
              <div className="loading-text">正在检索相关文档片段...</div>
            </div>
          </div>
        )}
      </div>

      <div className="retrieval-input-container">
        <form className="retrieval-input-wrapper" onSubmit={handleSubmit}>
          <textarea
            className="retrieval-input"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="输入查询文本或关键字进行召回测试..."
            rows={1}
            disabled={isLoading}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            className="retrieval-send-button"
            disabled={!inputValue.trim() || isLoading}
          >
            {isLoading ? '搜索中' : '搜索'}
          </button>
        </form>
      </div>

      <div ref={resultsEndRef} style={{ height: 1 }} />
    </div>
  );
});
