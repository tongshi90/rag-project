// 文件类型
export interface FileInfo {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadTime: string;
  status: 'parsing' | 'completed' | 'failed';
  kbId?: string | null;
}

// 知识库类型
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  fileCount?: number;
}

// 知识库创建请求
export interface KnowledgeBaseCreateRequest {
  name: string;
  description?: string;
}

// 知识库更新请求
export interface KnowledgeBaseUpdateRequest {
  name?: string;
  description?: string;
}

// 知识库列表响应
export interface KnowledgeBaseListResponse {
  knowledgeBases: KnowledgeBase[];
  total: number;
}

// 上传文件状态
export interface UploadFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// 文件列表响应
export interface FileListListResponse {
  files: FileInfo[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 技能卡片类型
export interface SkillCard {
  id: string;
  title: string;
  description: string;
  skillCode: string;
  published: boolean;
  createdAt: string;
  updatedAt: string;
}

// 技能卡片创建请求
export interface SkillCardCreateRequest {
  title: string;
  description: string;
  skillCode: string;
  published?: boolean;
}

// 技能卡片更新请求
export interface SkillCardUpdateRequest {
  title?: string;
  description?: string;
  skillCode?: string;
  published?: boolean;
}

// 技能卡片列表响应
export interface SkillCardListResponse {
  skills: SkillCard[];
  total: number;
}

// 技能文件类型
export interface SkillFile {
  name: string;
  path: string;
  isFile: boolean;
  size: number;
  modifiedTime: number;
  children?: SkillFile[];
  hasChildren?: boolean;
  isSystemFile?: boolean;  // 系统文件标识（如 SKILL.md）
  originalPath?: string;   // 原始路径（用于文件夹路径追踪）
}

// 技能文件内容类型
export interface SkillFileContent {
  name: string;
  path: string;
  content: string;
  size: number;
}

// 召回测试请求
export interface RetrievalTestRequest {
  query: string;
  kbId?: string;
  topK?: number;
  retrievalTopK?: number;
}

// 召回chunk类型
export interface RetrievableChunk {
  chunkId: string;
  text: string;
  score: number;
  rerankScore: number;
  metadata: {
    docId: string;
    docName: string;
    page: number;
    order: number;
  };
}

// 召回测试响应
export interface RetrievalTestResponse {
  query: string;
  chunks: RetrievableChunk[];
  total: number;
  message?: string;
}

// 召回测试历史记录类型
export interface RetrievalTestHistory {
  id: string;
  kbId: string;
  query: string;
  timestamp: string;
}

// 召回测试历史记录列表响应
export interface RetrievalTestHistoryListResponse {
  histories: RetrievalTestHistory[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Chunk 类型
export interface FileChunk {
  chunkId: string;
  text: string;
  order: number;
  page: number;
  type: string;
  length: number;
  titlePath: string[];  // 标题路径，如 ["第一章 概述", "一、背景"]
}

// Chunk 列表响应
export interface FileChunkListResponse {
  fileId: string;
  fileName: string;
  chunks: FileChunk[];
  total: number;
}
