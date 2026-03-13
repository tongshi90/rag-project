import React, { useState, useEffect } from 'react';
import { FileList } from './FileList';
import { FileUploadModal } from './FileUploadModal';
import { apiService } from '../services/api';
import type { FileInfo } from '../types';

export const Sidebar: React.FC = () => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 加载文件列表
  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.getFileList();
      if (response.success && response.data) {
        setFiles(response.data.files);
      }
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  // 处理上传
  const handleUpload = async (selectedFiles: File[]) => {
    for (const file of selectedFiles) {
      const response = await apiService.uploadFile(file);
      if (response.success && response.data) {
        setFiles(prev => [response.data!, ...prev]);
      }
    }
  };

  // 处理删除
  const handleDelete = async (fileId: string) => {
    const response = await apiService.deleteFile(fileId);
    if (response.success) {
      setFiles(prev => prev.filter(f => f.id !== fileId));
    }
  };

  // 处理批量删除
  const handleDeleteAll = async () => {
    const response = await apiService.deleteAllFiles();
    if (response.success) {
      setFiles([]);
    }
  };

  // 处理文件状态更新
  const handleFileUpdate = (fileId: string, updatedFile: FileInfo) => {
    setFiles(prev => prev.map(f => f.id === fileId ? updatedFile : f));
  };

  return (
    <>
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>RAG 知识库</h2>
        </div>

        <div className="upload-area">
          <button
            className="upload-button"
            onClick={() => setIsModalOpen(true)}
            disabled={isLoading}
          >
            + 上传文件
          </button>
        </div>

        <FileList
          files={files}
          onFileUpdate={handleFileUpdate}
          onDelete={handleDelete}
          onDeleteAll={handleDeleteAll}
        />
      </div>

      <FileUploadModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUpload={handleUpload}
      />
    </>
  );
};
