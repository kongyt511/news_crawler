import os
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
            with open(filepath, "a", encoding="utf-8") as f:
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

    def add_news(self, source, title, url, content, publish_time=None, preview_len=100):
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
        except Exception as e:
            print(f"[Duplicate] {url} 已存在，跳过")
