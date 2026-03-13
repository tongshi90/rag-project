#!/bin/sh
set -e

# 默认后端 URL
API_BASE_URL=${API_BASE_URL:-http://localhost:5000}

echo "=========================================="
echo "Configuring backend URL: $API_BASE_URL"
echo "=========================================="

# 检查 config.js 文件是否存在
echo "Checking config.js..."
ls -la /usr/share/nginx/html/config.js || echo "config.js NOT FOUND!"

# 显示原始内容
echo ""
echo "Original config.js content:"
cat /usr/share/nginx/html/config.js || echo "Cannot read config.js"

# 替换 config.js 中的占位符（只替换值，不影响属性名）
echo ""
echo "Replacing placeholder..."
sed -i "s|{{API_BASE_URL}}|${API_BASE_URL}|g" /usr/share/nginx/html/config.js

# 显示替换后的内容
echo ""
echo "After replacement:"
cat /usr/share/nginx/html/config.js

echo ""
echo "=========================================="
echo "Starting nginx..."
echo "=========================================="
exec nginx -g 'daemon off;'
