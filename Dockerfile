# 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY crawler/requirements.txt ./

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制爬虫代码
COPY crawler/ ./

# 设置环境变量，让爬虫可以通过环境变量获取 MongoDB 配置
ENV MONGO_URL mongodb://news_user:123456@127.0.0.1:27017/news
ENV RABBITMQ_HOST 127.0.0.1

# 设置默认命令
CMD ["python", "crawler.py"]
