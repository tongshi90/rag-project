import React, { useState, useCallback } from 'react';
import type { UploadFile } from '../types';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({ isOpen, onClose, onUpload }) => {
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;

    const newFiles: UploadFile[] = Array.from(files).map(file => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      status: 'pending',
      progress: 0,
    }));

    setUploadFiles(prev => [...prev, ...newFiles]);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  }, [handleFileSelect]);

  const handleRemoveFile = useCallback((id: string) => {
    setUploadFiles(prev => prev.filter(f => f.id !== id));
  }, []);

  const handleUpload = async () => {
    if (uploadFiles.length === 0) return;

    setIsUploading(true);
    try {
      const files = uploadFiles.map(f => f.file);
      await onUpload(files);
      setUploadFiles([]);
      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">上传文件</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div
          className={`modal-dropzone ${dragOver ? 'drag-over' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <div className="modal-dropzone-icon">📁</div>
          <div className="modal-dropzone-text">拖放文件到这里或点击选择</div>
          <div className="modal-dropzone-hint">支持 PDF、Word、Markdown 等格式</div>
        </div>

        <input
          id="file-input"
          type="file"
          multiple
          className="hidden-input"
          onChange={handleInputChange}
        />

        {uploadFiles.length > 0 && (
          <div className="modal-file-list">
            {uploadFiles.map(uploadFile => (
              <div key={uploadFile.id} className="modal-file-item">
                <span className="modal-file-name">{uploadFile.file.name}</span>
                <span className="modal-file-size">{formatFileSize(uploadFile.file.size)}</span>
                <button
                  className="modal-file-remove"
                  onClick={() => handleRemoveFile(uploadFile.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="modal-actions">
          <button className="modal-button secondary" onClick={onClose}>
            取消
          </button>
          <button
            className="modal-button primary"
            onClick={handleUpload}
            disabled={uploadFiles.length === 0 || isUploading}
          >
            {isUploading ? '上传中...' : '上传'}
          </button>
        </div>
      </div>
    </div>
  );
};
