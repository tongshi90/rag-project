// 文件类型
export interface FileInfo {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadTime: string;
  status: 'parsing' | 'completed' | 'failed';
}

// 消息类型
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
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
export interface FileListResponse {
  files: FileInfo[];
  total: number;
}

// 聊天请求
export interface ChatRequest {
  message: string;
  files?: string[];
}

// 聊天响应
export interface ChatResponse {
  answer: string;
  elapsed?: number;
}

// 流式聊天回调函数
export type StreamMessageCallback = (chunk: string) => void;

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
  isFile: boolean;
  size: number;
  modifiedTime: number;
}

// 技能文件内容类型
export interface SkillFileContent {
  name: string;
  path: string;
  content: string;
  size: number;
}
