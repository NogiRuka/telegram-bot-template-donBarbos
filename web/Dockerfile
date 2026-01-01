FROM node:20-alpine

# 安装 pnpm
RUN npm install -g pnpm

WORKDIR /usr/src/app

# 优先拷贝依赖描述文件，利用 Docker 镜像层缓存
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 拷贝其余源码
COPY . .

# 开发模式通常由 compose 启动命令覆盖，这里写默认启动
CMD ["pnpm", "run", "dev"]