# ==================== 前端 Dockerfile ====================
# ==================== 第一阶段：构建阶段 ====================
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装所有依赖（包括 devDependencies，构建需要 TypeScript）
RUN npm ci

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ==================== 第二阶段：生产运行阶段 ====================
FROM nginx:alpine

# 安装 curl 和 sed（用于环境变量替换）
RUN apk add --no-cache curl sed

# 从构建阶段复制构建产物到 nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置和启动脚本
COPY nginx.conf /etc/nginx/nginx.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh

# 设置启动脚本执行权限
RUN chmod +x /docker-entrypoint.sh

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# 使用启动脚本
CMD ["/docker-entrypoint.sh"]
