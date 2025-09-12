import os, json

class Storage:
    def __init__(self, visited_file="visited.json", news_file="news.json"):
        self.visited_file = visited_file
        self.news_file = news_file
        self.visited = set()
        self.news = []
        # self._load()

    def _load(self):
        if os.path.exists(self.visited_file):
            with open(self.visited_file, "r", encoding="utf-8") as f:
                self.visited = set(json.load(f))
        if os.path.exists(self.news_file):
            with open(self.news_file, "r", encoding="utf-8") as f:
                self.news = json.load(f)

    def save(self):
        with open(self.visited_file, "w", encoding="utf-8") as f:
            json.dump(list(self.visited), f, ensure_ascii=False, indent=2)
        with open(self.news_file, "w", encoding="utf-8") as f:
            json.dump(self.news, f, ensure_ascii=False, indent=2)

    def add_visited(self, url):
        self.visited.add(url)

    def is_visited(self, url):
        v = url in self.visited
        return v

    def add_news(self, source, title, url, content, publish_time=None, preview_len=100):
        self.news.append({
            "source": source,
            "title": title,
            "url": url,
            "content": content,
            "publish_time": str(publish_time)
        })
        # 日志输出，只显示正文前 preview_len 个字符
        preview = content[:preview_len].replace("\n", " ").strip()
        if len(content) > preview_len:
            preview += "..."
        print(f"[News Added] Title: {title} | URL: {url} | Publish Time: {str(publish_time)} | Content Preview: {preview}")
        self.save()
