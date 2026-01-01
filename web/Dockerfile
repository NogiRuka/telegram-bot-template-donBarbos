FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /usr/src/app

# 1. 只拷贝依赖定义
COPY package.json pnpm-lock.yaml* ./

# 2. 安装依赖（这一步会生成镜像内的 node_modules）
RUN pnpm install

# 3. 拷贝除 .dockerignore 以外的所有源码
# 有了 .dockerignore，这一步就不会尝试拷贝本地的 node_modules 了
COPY . .

CMD ["pnpm", "run", "dev"]