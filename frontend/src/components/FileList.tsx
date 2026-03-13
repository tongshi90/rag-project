import React, { useEffect, useRef } from 'react';
import type { FileInfo } from '../types';
import { formatFileSize } from '../services/api';
import { apiService } from '../services/api';

interface FileListProps {
  files: FileInfo[];
  onFileUpdate?: (fileId: string, file: FileInfo) => void;
  onDelete: (fileId: string) => void;
  onDeleteAll?: () => void;
}

// 状态标签组件
const StatusBadge: React.FC<{ status: FileInfo['status'] }> = ({ status }) => {
  const statusConfig = {
    parsing: { label: '解析中', className: 'status-parsing' },
    completed: { label: '已完成', className: 'status-completed' },
    failed: { label: '解析失败', className: 'status-failed' },
  };

  const config = statusConfig[status];
  return <span className={`status-badge ${config.className}`}>{config.label}</span>;
};

export const FileList: React.FC<FileListProps> = ({ files, onFileUpdate, onDelete, onDeleteAll }) => {
  const getFileIcon = (type: string): string => {
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('text') || type.includes('markdown')) return '📃';
    if (type.includes('sheet') || type.includes('excel')) return '📊';
    return '📎';
  };

  const handleDeleteAll = () => {
    if (onDeleteAll && confirm('确定要删除所有文件吗？此操作不可恢复。')) {
      onDeleteAll();
    }
  };

  // 轮询检查解析中的文件状态
  const pollingRefs = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    // 清理所有定时器
    return () => {
      pollingRefs.current.forEach(timer => clearInterval(timer));
      pollingRefs.current.clear();
    };
  }, []);

  useEffect(() => {
    // 检查哪些文件需要轮询
    const parsingFiles = files.filter(f => f.status === 'parsing');

    // 取消已经不存在或状态改变的文件的轮询
    const currentParsingIds = new Set(parsingFiles.map(f => f.id));
    pollingRefs.current.forEach((timer, fileId) => {
      if (!currentParsingIds.has(fileId)) {
        clearInterval(timer);
        pollingRefs.current.delete(fileId);
      }
    });

    // 为新的解析中文件启动轮询
    parsingFiles.forEach(file => {
      if (!pollingRefs.current.has(file.id)) {
        const timer = setInterval(async () => {
          try {
            const response = await apiService.getFile(file.id);
            if (response.success && response.data && onFileUpdate) {
              // 如果状态不再是 parsing，停止轮询
              if (response.data.status !== 'parsing') {
                clearInterval(timer);
                pollingRefs.current.delete(file.id);
              }
              onFileUpdate(file.id, response.data);
            }
          } catch (error) {
            console.error(`Failed to check status for file ${file.id}:`, error);
          }
        }, 2000); // 每2秒轮询一次

        pollingRefs.current.set(file.id, timer);
      }
    });
  }, [files, onFileUpdate]);

  return (
    <div className="file-list">
      <div className="file-list-header">
        <div className="file-list-header-left">
          <h3>已上传文件</h3>
          <span className="file-count">{files.length} 个文件</span>
        </div>
        {files.length > 0 && onDeleteAll && (
          <button
            className="delete-all-button"
            onClick={handleDeleteAll}
            title="批量删除所有文件"
          >
            批量删除
          </button>
        )}
      </div>

      {files.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <div className="empty-state-text">暂无文件</div>
        </div>
      ) : (
        files.map(file => (
          <div key={file.id} className="file-item">
            <div className="file-icon">{getFileIcon(file.type)}</div>
            <div className="file-info">
              <div className="file-header">
                <div className="file-name" title={file.name}>{file.name}</div>
                <StatusBadge status={file.status} />
              </div>
              <div className="file-meta">
                {formatFileSize(file.size)} · {file.uploadTime}
              </div>
            </div>
            <div className="file-actions">
              <button
                className="file-action-button delete"
                onClick={() => onDelete(file.id)}
                title="删除"
              >
                🗑️
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
