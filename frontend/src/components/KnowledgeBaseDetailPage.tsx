import React, { useState, useEffect } from 'react';
import { RetrievalTestPanel } from './RetrievalTestPanel';
import { useConfirmDialog } from './ConfirmDialog';
import { apiService } from '../services/api';
import type { FileInfo, KnowledgeBase, RetrievalTestHistory } from '../types';
import { ChunkListDrawer } from './ChunkListDrawer';
import './KnowledgeBaseDetailPage.css';

interface KnowledgeBaseDetailPageProps {
  kb: KnowledgeBase;
  onBackToHome: () => void;
}

export const KnowledgeBaseDetailPage: React.FC<KnowledgeBaseDetailPageProps> = ({ kb }) => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const pollingIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Chunk 抽屉状态
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);
  const [showChunkDrawer, setShowChunkDrawer] = useState(false);

  // 召回测试历史记录
  const [retrievalHistory, setRetrievalHistory] = useState<RetrievalTestHistory[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const retrievalInputRef = React.useRef<{ setQuery: (query: string) => void }>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyTotalPages, setHistoryTotalPages] = useState(0);
  const itemsPerPage = 10;
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // 确认弹窗
  const { confirm, DialogComponent } = useConfirmDialog();

  // 加载知识库文件
  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.getKnowledgeBaseFiles(kb.id);
      if (response.success && response.data) {
        const newFiles = response.data.files;
        setFiles(newFiles);

        // 检查是否有正在解析的文件
        const hasParsingFiles = newFiles.some(f => f.status === 'parsing');

        if (hasParsingFiles && !pollingIntervalRef.current) {
          // 开始轮询
          startPolling();
        } else if (!hasParsingFiles && pollingIntervalRef.current) {
          // 停止轮询
          stopPolling();
        }
      }
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 开始轮询
  const startPolling = () => {
    if (pollingIntervalRef.current) return;

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await apiService.getKnowledgeBaseFiles(kb.id);
        if (response.success && response.data) {
          const updatedFiles = response.data.files;
          setFiles(updatedFiles);

          // 如果没有正在解析的文件，停止轮询
          if (!updatedFiles.some(f => f.status === 'parsing')) {
            stopPolling();
          }
        }
      } catch (error) {
        console.error('Failed to poll file status:', error);
      }
    }, 3000);
  };

  // 停止轮询
  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  // 加载召回测试历史记录
  const loadRetrievalHistory = async (page: number = 1) => {
    setIsLoadingHistory(true);
    try {
      const response = await apiService.getRetrievalTestHistory(kb.id, page, itemsPerPage);
      if (response.success && response.data) {
        setRetrievalHistory(response.data.histories);
        setHistoryTotal(response.data.total);
        setHistoryTotalPages(response.data.totalPages);
        setCurrentPage(response.data.page);
      }
    } catch (error) {
      console.error('Failed to load retrieval history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadFiles();
    loadRetrievalHistory();

    // 组件卸载时停止轮询
    return () => stopPolling();
  }, [kb.id]);

  // 处理文件上传
  const handleUploadFiles = async (selectedFiles: File[]) => {
    for (const file of selectedFiles) {
      try {
        const response = await apiService.uploadToKnowledgeBase(kb.id, file);
        if (response.success && response.data) {
          setFiles(prev => [response.data!, ...prev]);
          // 上传成功后立即开始轮询（因为新文件状态是parsing）
          startPolling();
        }
      } catch (error) {
        console.error('Failed to upload file:', error);
        alert(`上传文件 ${file.name} 失败`);
      }
    }
  };

  // 处理模态框上传
  const handleModalUpload = async (selectedFiles: File[]) => {
    await handleUploadFiles(selectedFiles);
    setShowUploadModal(false);
  };

  // 处理文件删除
  const handleDeleteFile = async (fileId: string, fileName: string) => {
    const confirmed = await confirm('删除文件', `确定要删除文件 "${fileName}" 吗？此操作不可恢复。`, {
      confirmText: '删除',
      cancelText: '取消',
      type: 'danger'
    });
    if (!confirmed) return;

    try {
      const response = await apiService.deleteKnowledgeBaseFile(kb.id, fileId);
      if (response.success) {
        setFiles(prev => prev.filter(f => f.id !== fileId));
      } else {
        await confirm('删除失败', response.error || '删除文件失败，请稍后重试', {
          confirmText: '确定',
          type: 'info'
        });
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
      await confirm('删除失败', '删除文件失败，请稍后重试', {
        confirmText: '确定',
        type: 'info'
      });
    }
  };

  // 处理清空所有文件
  const handleClearAllFiles = async () => {
    if (files.length === 0) return;
    const confirmed = await confirm(
      '清空所有文件',
      `确定要删除知识库中的所有 ${files.length} 个文件吗？此操作不可恢复。`,
      {
        confirmText: '清空',
        cancelText: '取消',
        type: 'danger'
      }
    );
    if (!confirmed) return;

    try {
      const response = await apiService.deleteAllKnowledgeBaseFiles(kb.id);
      if (response.success) {
        setFiles([]);
        await confirm('清空成功', `已删除 ${response.data?.deletedCount || 0} 个文件`, {
          confirmText: '确定',
          type: 'info'
        });
      } else {
        await confirm('清空失败', response.error || '清空文件失败，请稍后重试', {
          confirmText: '确定',
          type: 'info'
        });
      }
    } catch (error) {
      console.error('Failed to clear all files:', error);
      await confirm('清空失败', '清空文件失败，请稍后重试', {
        confirmText: '确定',
        type: 'info'
      });
    }
  };

  // 格式化日期
  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  // 格式化时间
  const formatTime = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  // 添加到历史记录
  const addToHistory = async (query: string) => {
    try {
      const response = await apiService.addRetrievalTestHistory(kb.id, query);
      if (response.success) {
        // 重新加载第一页
        loadRetrievalHistory(1);
      }
    } catch (error) {
      console.error('Failed to save retrieval history:', error);
    }
  };

  // 处理历史记录点击
  const handleHistoryClick = (record: RetrievalTestHistory) => {
    setSelectedHistoryId(record.id);
    // 通过 ref 设置输入框的值
    retrievalInputRef.current?.setQuery(record.query);
  };

  // 删除历史记录
  const handleDeleteHistory = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await apiService.deleteRetrievalTestHistory(id);
      if (response.success) {
        if (selectedHistoryId === id) {
          setSelectedHistoryId(null);
        }
        // 重新加载当前页
        loadRetrievalHistory(currentPage);
      }
    } catch (error) {
      console.error('Failed to delete retrieval history:', error);
    }
  };

  // 清空历史记录
  const handleClearHistory = async () => {
    if (historyTotal === 0) return;
    const confirmed = await confirm(
      '清空测试记录',
      '确定要清空所有召回测试记录吗？此操作不可恢复。',
      {
        confirmText: '清空',
        cancelText: '取消',
        type: 'danger'
      }
    );
    if (!confirmed) return;

    try {
      const response = await apiService.clearRetrievalTestHistory(kb.id);
      if (response.success) {
        setRetrievalHistory([]);
        setSelectedHistoryId(null);
        setHistoryTotal(0);
        setHistoryTotalPages(0);
        setCurrentPage(1);
      }
    } catch (error) {
      console.error('Failed to clear retrieval history:', error);
    }
  };

  // 处理文件点击 - 打开 chunk 列表
  const handleFileClick = (file: FileInfo) => {
    if (file.status === 'completed') {
      setSelectedFile(file);
      setShowChunkDrawer(true);
    }
  };

  // 关闭 chunk 抽屉
  const handleCloseChunkDrawer = () => {
    setShowChunkDrawer(false);
  };

  return (
    <div className="kb-detail-page">
      <div className="kb-detail-content">
        <div className="kb-detail-sidebar">
          <h2 className="kb-detail-sidebar-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            知识文件
            <span className="kb-detail-sidebar-actions">
              <button
                className="kb-detail-upload-btn"
                onClick={() => setShowUploadModal(true)}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                上传文件
              </button>
              {files.length > 0 && (
                <button
                  className="kb-detail-clear-btn"
                  onClick={handleClearAllFiles}
                  title="清空所有文件"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                  清空
                </button>
              )}
            </span>
          </h2>

          {isLoading ? (
            <div className="kb-detail-loading">加载中...</div>
          ) : files.length === 0 ? (
            <div className="kb-detail-empty">
              <div className="kb-detail-empty-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <div className="kb-detail-empty-text">暂无文件</div>
              <div className="kb-detail-empty-hint">点击上方按钮上传PDF文件</div>
            </div>
          ) : (
            <div className="kb-file-list">
              {files.map(file => (
                <div
                  key={file.id}
                  className={`kb-file-item ${file.status === 'completed' ? 'kb-file-item-clickable' : ''}`}
                  onClick={() => handleFileClick(file)}
                  title={file.status === 'completed' ? '点击查看分块详情' : undefined}
                >
                  <div className="kb-file-icon">
                    {file.type.includes('pdf') ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                      </svg>
                    )}
                  </div>
                  <div className="kb-file-info">
                    <div className="kb-file-name" title={file.name}>{file.name}</div>
                    <div className="kb-file-meta">
                      <span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        {formatFileSize(file.size)}
                      </span>
                      <span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '4px'}}>
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                          <line x1="16" y1="2" x2="16" y2="6"></line>
                          <line x1="8" y1="2" x2="8" y2="6"></line>
                          <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        {formatDate(file.uploadTime)}
                      </span>
                    </div>
                  </div>
                  <div className="kb-file-right">
                    {file.status === 'parsing' && <span className="status-tag status-parsing">解析中</span>}
                    {file.status === 'completed' && <span className="status-tag status-completed">已完成</span>}
                    {file.status === 'failed' && <span className="status-tag status-failed">失败</span>}
                    <button
                      className="kb-file-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteFile(file.id, file.name);
                      }}
                      title="删除"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="kb-detail-main">
          <div className="kb-detail-main-content">
            <RetrievalTestPanel
              kbId={kb.id}
              onTestSubmit={addToHistory}
              ref={retrievalInputRef}
            />
          </div>
          <div className="kb-detail-history-sidebar">
            <div className="kb-history-header">
              <h3 className="kb-history-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                召回测试记录
              </h3>
              {retrievalHistory.length > 0 && (
                <button
                  className="kb-history-clear-btn"
                  onClick={handleClearHistory}
                  title="清空历史"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              )}
            </div>
            <div className="kb-history-list">
              {isLoadingHistory ? (
                <div className="kb-history-empty">
                  <span>加载中...</span>
                </div>
              ) : retrievalHistory.length === 0 ? (
                <div className="kb-history-empty">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                  </svg>
                  <span>暂无召回测试记录</span>
                </div>
              ) : (
                <>
                  {retrievalHistory.map(record => (
                    <div
                      key={record.id}
                      className={`kb-history-item ${selectedHistoryId === record.id ? 'selected' : ''}`}
                      onClick={() => handleHistoryClick(record)}
                    >
                      <div className="kb-history-content">
                        <div className="kb-history-query" title={record.query}>{record.query}</div>
                        <div className="kb-history-time">{formatTime(record.timestamp)}</div>
                      </div>
                      <button
                        className="kb-history-delete-btn"
                        onClick={(e) => handleDeleteHistory(record.id, e)}
                        title="删除"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>
                    </div>
                  ))}
                  {historyTotalPages > 1 && (
                    <div className="kb-history-pagination">
                      <button
                        className="kb-history-page-btn"
                        onClick={() => loadRetrievalHistory(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                      </button>
                      <span className="kb-history-page-info">
                        {currentPage} / {historyTotalPages}
                      </span>
                      <button
                        className="kb-history-page-btn"
                        onClick={() => loadRetrievalHistory(currentPage + 1)}
                        disabled={currentPage === historyTotalPages}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {showUploadModal && (
        <div className="kb-upload-modal-overlay">
          <div className="kb-upload-modal">
            <h2 className="kb-upload-modal-title">上传文件到 {kb.name}</h2>
            <p className="kb-upload-modal-hint">支持 PDF、Word（.docx/.doc）格式文件</p>
            <div className="kb-upload-modal-actions">
              <button
                className="kb-upload-modal-btn"
                onClick={() => document.getElementById('kb-file-input')?.click()}
              >
                选择文件
              </button>
              <button
                className="kb-upload-modal-btn kb-upload-modal-btn-secondary"
                onClick={() => setShowUploadModal(false)}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        id="kb-file-input"
        type="file"
        multiple
        accept=".pdf,.docx,.doc"
        style={{ display: 'none' }}
        onChange={async (e) => {
          const selectedFiles = Array.from(e.target.files || []);
          if (selectedFiles.length === 0) return;
          await handleModalUpload(selectedFiles);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }}
      />

      {/* Chunk 列表抽屉 */}
      {selectedFile && (
        <ChunkListDrawer
          isOpen={showChunkDrawer}
          kbId={kb.id}
          fileId={selectedFile.id}
          fileName={selectedFile.name}
          onClose={handleCloseChunkDrawer}
        />
      )}

      <DialogComponent />
    </div>
  );
};

// 工具函数
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
