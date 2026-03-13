// API 配置
// Docker 部署时，window.__API_BASE_URL__ 会被替换为实际的后端地址
// 本地开发时，使用 127.0.0.1:5000
const getApiBaseUrl = (): string => {
  // 如果占位符未被替换（本地开发环境），使用默认地址
  if (window.__API_BASE_URL__ === '{{API_BASE_URL}}' || !window.__API_BASE_URL__) {
    return 'http://127.0.0.1:5000';
  }
  return window.__API_BASE_URL__;
};

export const API_BASE_URL = getApiBaseUrl();
