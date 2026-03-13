import type { FileInfo, FileListResponse, ChatResponse, ApiResponse, StreamMessageCallback, SkillCard, SkillCardCreateRequest, SkillCardUpdateRequest, SkillFile, SkillFileContent } from '../types';

// 工具函数：格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

// API服务类型
export interface ApiService {
  getFileList: () => Promise<ApiResponse<FileListResponse>>;
  getFile: (fileId: string) => Promise<ApiResponse<FileInfo>>;
  uploadFile: (file: File) => Promise<ApiResponse<FileInfo>>;
  deleteFile: (fileId: string) => Promise<ApiResponse<void>>;
  deleteAllFiles: () => Promise<ApiResponse<void>>;
  sendMessage: (message: string) => Promise<ApiResponse<ChatResponse>>;
  sendMessageStream: (message: string, onChunk: StreamMessageCallback) => Promise<void>;
  // 技能卡片 API
  getSkillCards: (searchKeyword?: string) => Promise<{ code: number; data: SkillCard[]; message: string }>;
  getSkillCard: (cardId: string) => Promise<{ code: number; data: SkillCard; message: string }>;
  createSkillCard: (request: SkillCardCreateRequest) => Promise<{ code: number; data: SkillCard; message: string }>;
  updateSkillCard: (cardId: string, request: SkillCardUpdateRequest) => Promise<{ code: number; data: SkillCard; message: string }>;
  deleteSkillCard: (cardId: string) => Promise<{ code: number; message: string }>;
  deleteAllSkillCards: () => Promise<{ code: number; message: string }>;
  publishSkillCard: (cardId: string) => Promise<{ code: number; data: SkillCard; message: string }>;
  unpublishSkillCard: (cardId: string) => Promise<{ code: number; data: SkillCard; message: string }>;
  // 技能文件 API
  listSkillFiles: (skillId: string) => Promise<{ code: number; data: SkillFile[]; message: string }>;
  getSkillFileContent: (skillId: string, path: string) => Promise<{ code: number; data: SkillFileContent; message: string }>;
  createSkillFile: (skillId: string, path: string, content: string) => Promise<{ code: number; data: any; message: string }>;
  updateSkillFile: (skillId: string, path: string, newPath?: string, content?: string) => Promise<{ code: number; data: any; message: string }>;
  deleteSkillFile: (skillId: string, path: string) => Promise<{ code: number; message: string }>;
}

// 真实API服务
export const apiService: ApiService = {
  getFileList: async () => {
    const response = await fetch('http://localhost:5000/api/files');
    return response.json();
  },
  getFile: async (fileId) => {
    const response = await fetch(`http://localhost:5000/api/files/${fileId}`);
    return response.json();
  },
  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('http://localhost:5000/api/files/upload', {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
  deleteFile: async (fileId) => {
    const response = await fetch(`http://localhost:5000/api/files/${fileId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  deleteAllFiles: async () => {
    const response = await fetch('http://localhost:5000/api/files/all', {
      method: 'DELETE',
    });
    return response.json();
  },
  sendMessage: async (message) => {
    const response = await fetch('http://localhost:5000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    return response.json();
  },
  sendMessageStream: async (message, onChunk) => {
    console.log('Starting stream request for message:', message);
    const response = await fetch('http://localhost:5000/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    console.log('Response status:', response.status);
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Response error:', errorText);
      throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let chunkCount = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        console.log('Stream done, total chunks:', chunkCount);
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 保留不完整的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            console.log('Received [DONE] signal');
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              chunkCount++;
              onChunk(parsed.content);
            }
            if (parsed.error) {
              console.error('Server error:', parsed.error);
              throw new Error(parsed.error);
            }
          } catch (e) {
            if (e instanceof SyntaxError) {
              console.error('Failed to parse SSE data:', data);
            } else {
              throw e;
            }
          }
        }
      }
    }
  },
  // 技能卡片 API 实现
  getSkillCards: async (searchKeyword = '') => {
    const url = searchKeyword
      ? `http://localhost:5000/api/skills?search=${encodeURIComponent(searchKeyword)}`
      : 'http://localhost:5000/api/skills';
    const response = await fetch(url);
    return response.json();
  },
  getSkillCard: async (cardId) => {
    const response = await fetch(`http://localhost:5000/api/skills/${cardId}`);
    return response.json();
  },
  createSkillCard: async (request) => {
    const response = await fetch('http://localhost:5000/api/skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },
  updateSkillCard: async (cardId, request) => {
    const response = await fetch(`http://localhost:5000/api/skills/${cardId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },
  deleteSkillCard: async (cardId) => {
    const response = await fetch(`http://localhost:5000/api/skills/${cardId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
  deleteAllSkillCards: async () => {
    const response = await fetch('http://localhost:5000/api/skills', {
      method: 'DELETE',
    });
    return response.json();
  },
  publishSkillCard: async (cardId) => {
    const response = await fetch(`http://localhost:5000/api/skills/${cardId}/publish`, {
      method: 'PUT',
    });
    return response.json();
  },
  unpublishSkillCard: async (cardId) => {
    const response = await fetch(`http://localhost:5000/api/skills/${cardId}/unpublish`, {
      method: 'PUT',
    });
    return response.json();
  },
  // 技能文件 API 实现
  listSkillFiles: async (skillId) => {
    const response = await fetch(`http://localhost:5000/api/skills/${skillId}/files`);
    return response.json();
  },
  getSkillFileContent: async (skillId, path) => {
    const response = await fetch(`http://localhost:5000/api/skills/${skillId}/files/content?path=${encodeURIComponent(path)}`);
    return response.json();
  },
  createSkillFile: async (skillId, path, content) => {
    const response = await fetch(`http://localhost:5000/api/skills/${skillId}/files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    });
    return response.json();
  },
  updateSkillFile: async (skillId, path, newPath, content) => {
    const response = await fetch(`http://localhost:5000/api/skills/${skillId}/files`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, newPath, content }),
    });
    return response.json();
  },
  deleteSkillFile: async (skillId, path) => {
    const response = await fetch(`http://localhost:5000/api/skills/${skillId}/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
