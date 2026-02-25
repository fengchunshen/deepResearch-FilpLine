# Docker 部署指南

## 前置条件

- 安装 Docker
- 项目根目录下准备好 `.env` 配置文件（参考 `.env.example`）

## 构建镜像

```bash
docker build -t langchain-megumi .
```

## 运行容器

```bash
docker run -d -p 8000:8000 --env-file .env --name megumi langchain-megumi
```

## 常用管理命令

```bash
# 查看日志
docker logs -f megumi

# 停止 / 启动 / 重启
docker stop megumi
docker start megumi
docker restart megumi

# 删除容器
docker rm -f megumi
```

## 更新部署

代码更新后重新构建并运行：

```bash
docker rm -f megumi
docker build -t langchain-megumi .
docker run -d -p 8000:8000 --env-file .env --name megumi langchain-megumi
```

## 离线部署（镜像导出/导入）

```bash
# 导出镜像
docker save langchain-megumi -o megumi.tar

# 导入镜像
docker load -i megumi.tar
```

## 健康检查

容器内置健康检查，访问 `http://localhost:8000/health`，可通过以下命令查看状态：

```bash
docker inspect --format='{{.State.Health.Status}}' megumi
```
