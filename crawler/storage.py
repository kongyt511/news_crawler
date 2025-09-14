import json
import os
import re
import pika
from datetime import datetime
import pymongo


class Storage:
    def __init__(self):
        # 从环境变量读取 MongoDB 配置
        self.client = pymongo.MongoClient(os.environ.get("MONGO_URL", ""))
        self.db = self.client.get_database()
        self.news = self.db["news"]
        self.news.create_index("url", unique=True)
        self.visited = set()
        self.rabbitmq_host = os.environ.get("RABBITMQ_HOST", "")
        self.rabbitmq_conn = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.rabbitmq_host)
        )
        self.rabbitmq_channel = self.rabbitmq_conn.channel()
        self.rabbitmq_channel.queue_declare(queue="news", durable=True)


    def add_visited(self, url):
        self.visited.add(url)

    def is_visited(self, url):
        if url in self.visited:
            return True
        if self.news.find_one({"url": url}) is not None:
            self.visited.add(url)
            return True
        return False

    def save_failed(self, url, title, content, publish_time):
        try:
            filepath = "failed_urls.txt"
            os.makedirs("data", exist_ok=True)
            with open(os.path.join("data", filepath), "a", encoding="utf-8") as f:
                f.write(f"url: {url}, title_valid: {bool(title)}, content_valid: {bool(content)}, publish_time_valid: {bool(publish_time)}\n")
            print(f"[Saved] 失败 URL 已保存到 {filepath}")
        except Exception as e:
            print(f"[Error] 保存失败 URL 失败: {e}")

    def check_valid(self, url, title, content, publish_time):
        if title == "" or content == "" or publish_time is None:
            self.save_failed(url, title, content, publish_time)
            return False
        else:
            return True

    def parse_datetime(self, dt):
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt  # 已经是 datetime 类型，直接返回
        if not isinstance(dt, str):
            return None  # 不是字符串也不是 datetime，返回 None

        # 尝试匹配常见日期格式
        patterns = [
            ("%Y年%m月%d日 %H:%M:%S", r"\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}:\d{2}"),
            ("%Y-%m-%d %H:%M:%S", r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"),
            ("%Y-%m-%dT%H:%M:%S.%f%z", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[\+\-]\d{2}:\d{2}"),
            ("%Y-%m-%dT%H:%M:%S", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
            ("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}")
        ]

        for fmt, pattern in patterns:
            if re.fullmatch(pattern, dt):
                try:
                    return datetime.strptime(dt, fmt)
                except Exception:
                    continue
        return None  # 无法解析，返回 None

    def notify_news(self, item):
        self.rabbitmq_channel.basic_publish(
            exchange="",
            routing_key="news",
            body=json.dumps(item),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
        print(f'[RabbitMQ] 推送新闻: {item["source"]}, {item["title"]}, {item["url"]}]')

    def add_news(self, source, title, url, content, publish_time=None, preview_len=100):
        publish_time = self.parse_datetime(publish_time)
        if self.check_valid(url, title, content, publish_time) == False:
            return
        news_item = {
            "source": source,
            "title": title,
            "url": url,
            "content": content,
            "publish_time": publish_time,
            "created_at": datetime.utcnow()
        }
        try:
            self.news.insert_one(news_item)
            # 日志输出
            preview = content[:preview_len].replace("\n", " ").strip()
            if len(content) > preview_len:
                preview += "..."
            print(f"[News Added] Title: {title} | URL: {url} | Publish Time: {publish_time} | Preview: {preview}")
            if news_item.get("publish_time").date() == datetime.now().date():
                self.notify_news(news_item)

        except Exception as e:
            print(f"[Duplicate] {url} 已存在，跳过")
