import type {
  FileInfo,
  FileListListResponse,
  ApiResponse,
  SkillCard,
  SkillCardCreateRequest,
  SkillCardUpdateRequest,
  SkillFile,
  SkillFileContent,
  KnowledgeBase,
  KnowledgeBaseCreateRequest,
  KnowledgeBaseUpdateRequest,
  KnowledgeBaseListResponse,
  RetrievalTestHistory,
  RetrievalTestHistoryListResponse,
  FileChunkListResponse
} from '../types';

// 获取API基础URL
const getApiBaseUrl = (): string => {
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (!envBaseUrl || envBaseUrl === '{{API_BASE_URL}}') {
    return 'http://127.0.0.1:5000';
  }
  return envBaseUrl;
};

const API_BASE_URL = getApiBaseUrl();

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
  getFileList: () => Promise<ApiResponse<FileListListResponse>>;
  getFile: (fileId: string) => Promise<ApiResponse<FileInfo>>;
  uploadFile: (file: File) => Promise<ApiResponse<FileInfo>>;
  deleteFile: (fileId: string) => Promise<ApiResponse<void>>;
  deleteAllFiles: () => Promise<ApiResponse<void>>;
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
  createSkillFile: (skillId: string, path: string, content: string, isFolder?: boolean) => Promise<{ code: number; data: any; message: string }>;
  updateSkillFile: (skillId: string, path: string, newPath?: string, content?: string) => Promise<{ code: number; data: any; message: string }>;
  deleteSkillFile: (skillId: string, path: string) => Promise<{ code: number; message: string }>;
  // 知识库 API
  getKnowledgeBases: () => Promise<ApiResponse<KnowledgeBaseListResponse>>;
  getKnowledgeBase: (kbId: string) => Promise<ApiResponse<KnowledgeBase>>;
  createKnowledgeBase: (request: KnowledgeBaseCreateRequest) => Promise<ApiResponse<KnowledgeBase>>;
  updateKnowledgeBase: (kbId: string, request: KnowledgeBaseUpdateRequest) => Promise<ApiResponse<KnowledgeBase>>;
  deleteKnowledgeBase: (kbId: string) => Promise<ApiResponse<void>>;
  getKnowledgeBaseFiles: (kbId: string) => Promise<ApiResponse<FileListListResponse>>;
  uploadToKnowledgeBase: (kbId: string, file: File) => Promise<ApiResponse<FileInfo>>;
  deleteKnowledgeBaseFile: (kbId: string, fileId: string) => Promise<ApiResponse<void>>;
  deleteAllKnowledgeBaseFiles: (kbId: string) => Promise<ApiResponse<{ deletedCount: number }>>;
  getFileChunks: (kbId: string, fileId: string) => Promise<ApiResponse<FileChunkListResponse>>;
  // 召回测试历史记录 API
  getRetrievalTestHistory: (kbId: string, page?: number, pageSize?: number) => Promise<ApiResponse<RetrievalTestHistoryListResponse>>;
  addRetrievalTestHistory: (kbId: string, query: string) => Promise<ApiResponse<RetrievalTestHistory>>;
  deleteRetrievalTestHistory: (historyId: string) => Promise<ApiResponse<void>>;
  clearRetrievalTestHistory: (kbId: string) => Promise<ApiResponse<{ deletedCount: number }>>;
}

// 真实API服务
export const apiService: ApiService = {
  getFileList: async () => {
    const response = await fetch(`${API_BASE_URL}/api/files`);
    return response.json();
  },

  getFile: async (fileId) => {
    const response = await fetch(`${API_BASE_URL}/api/files/${fileId}`);
    return response.json();
  },

  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },

  deleteFile: async (fileId) => {
    const response = await fetch(`${API_BASE_URL}/api/files/${fileId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  deleteAllFiles: async () => {
    const response = await fetch(`${API_BASE_URL}/api/files/all`, {
      method: 'DELETE' });
    return response.json();
  },

  // 技能卡片 API 实现
  getSkillCards: async (searchKeyword = '') => {
    const url = searchKeyword
      ? `${API_BASE_URL}/api/skills?search=${encodeURIComponent(searchKeyword)}`
      : `${API_BASE_URL}/api/skills`;
    const response = await fetch(url);
    return response.json();
  },

  getSkillCard: async (cardId) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${cardId}`);
    return response.json();
  },

  createSkillCard: async (request) => {
    const response = await fetch(`${API_BASE_URL}/api/skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },

  updateSkillCard: async (cardId, request) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${cardId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },

  deleteSkillCard: async (cardId) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${cardId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  deleteAllSkillCards: async () => {
    const response = await fetch(`${API_BASE_URL}/api/skills`, {
      method: 'DELETE',
    });
    return response.json();
  },

  publishSkillCard: async (cardId) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${cardId}/publish`, {
      method: 'PUT',
    });
    return response.json();
  },

  unpublishSkillCard: async (cardId) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${cardId}/unpublish`, {
      method: 'PUT',
    });
    return response.json();
  },

  // 技能文件 API 实现
  listSkillFiles: async (skillId) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${skillId}/files`);
    return response.json();
  },

  getSkillFileContent: async (skillId, path) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${skillId}/files/content?path=${encodeURIComponent(path)}`);
    return response.json();
  },

  createSkillFile: async (skillId, path, content, isFolder = false) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${skillId}/files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content, isFolder }),
    });
    return response.json();
  },

  updateSkillFile: async (skillId, path, newPath, content) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${skillId}/files`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, newPath, content }),
    });
    return response.json();
  },

  deleteSkillFile: async (skillId, path) => {
    const response = await fetch(`${API_BASE_URL}/api/skills/${skillId}/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  // 知识库 API 实现
  getKnowledgeBases: async () => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases`);
    return response.json();
  },

  getKnowledgeBase: async (kbId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}`);
    return response.json();
  },

  createKnowledgeBase: async (request) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },

  updateKnowledgeBase: async (kbId, request) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  },

  deleteKnowledgeBase: async (kbId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  getKnowledgeBaseFiles: async (kbId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}/files`);
    return response.json();
  },

  uploadToKnowledgeBase: async (kbId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}/files/upload`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },

  deleteKnowledgeBaseFile: async (kbId, fileId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}/files/${fileId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  deleteAllKnowledgeBaseFiles: async (kbId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}/files/all`, {
      method: 'DELETE',
    });
    return response.json();
  },

  getFileChunks: async (kbId, fileId) => {
    const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${kbId}/files/${fileId}/chunks`);
    return response.json();
  },

  // 召回测试历史记录 API 实现
  getRetrievalTestHistory: async (kbId, page = 1, pageSize = 10) => {
    const response = await fetch(`${API_BASE_URL}/api/retrieval-test-history/${kbId}?page=${page}&pageSize=${pageSize}`);
    return response.json();
  },

  addRetrievalTestHistory: async (kbId, query) => {
    const response = await fetch(`${API_BASE_URL}/api/retrieval-test-history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kbId, query }),
    });
    return response.json();
  },

  deleteRetrievalTestHistory: async (historyId) => {
    const response = await fetch(`${API_BASE_URL}/api/retrieval-test-history/${historyId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  clearRetrievalTestHistory: async (kbId) => {
    const response = await fetch(`${API_BASE_URL}/api/retrieval-test-history/${kbId}/all`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
