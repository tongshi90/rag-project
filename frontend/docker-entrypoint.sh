#!/bin/sh
set -e

# 默认后端 URL
API_BASE_URL=${API_BASE_URL:-http://localhost:5000}

echo "=========================================="
echo "Configuring backend URL: $API_BASE_URL"
echo "=========================================="

# 替换 index.html 中的占位符
sed -i "s|{{API_BASE_URL}}|${API_BASE_URL}|g" /usr/share/nginx/html/index.html

echo "Configuration applied. Starting nginx..."
exec nginx -g 'daemon off;'
