// API 配置 - 优先使用环境变量，否则使用默认值
declare global {
  interface Window {
    __API_BASE_URL__?: string;
  }
}

// 从 window 对象读取环境变量，如果不存在则使用默认值
// Docker 环境：通过 docker-entrypoint.sh 注入到 index.html
// 本地开发：使用 127.0.0.1:5000
export const API_BASE_URL = window.__API_BASE_URL__ || 'http://127.0.0.1:5000';
