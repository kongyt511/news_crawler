import json, random, time
import re
from urllib.parse import urlparse, urlunparse, urljoin
import requests
from bs4 import BeautifulSoup
from collections import deque
from storage import Storage
from extractor import extract_news

# ------------------ 配置 ------------------
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

storage = Storage()

# ------------------ 辅助函数 ------------------
def is_allowed(url, allow_domains):
    domain = urlparse(url).netloc
    return any(d in domain for d in allow_domains)

def is_news(url, news_path_patterns):
    path = urlparse(url).path
    return any(re.search(pattern, path) for pattern in news_path_patterns)

def normalize_url(url):
    """去掉 URL 的 query 和 fragment 部分"""
    parts = urlparse(url)
    clean_parts = parts._replace(query="", fragment="")
    return urlunparse(clean_parts)

def get_links(html, base_url, allow_domains):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        new_url = urljoin(base_url, a['href'])
        if new_url.startswith("http") and is_allowed(new_url, allow_domains):
            links.add(new_url)
    return links

# ------------------ BFS 爬虫 ------------------
MAX_LINKS_PER_PAGE = 65536  # 每页抓取最大链接数

def crawl_bfs(source, seed_urls, allow_domains, news_path_patterns, interval_min, interval_max):
    queue = deque()
    in_queue = set()  # 用来记录队列里已经存在的 URL

    # 初始化队列
    for url in seed_urls:
        clean_url = normalize_url(url)
        queue.append(clean_url)
        in_queue.add(clean_url)

    while queue:
        url = queue.popleft()
        in_queue.remove(url)

        if storage.is_visited(url):
            continue

        print(f"Crawling: {url}")
        storage.add_visited(url)

        try:
            interval = random.uniform(interval_min, interval_max)
            print(f"  -> Sleeping {interval:.2f} seconds...")
            time.sleep(interval)

            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text

            # ------------------ 新闻页处理 ------------------
            if is_news(url, news_path_patterns):
                try:
                    interval = random.uniform(interval_min, interval_max)
                    print(f"  -> Sleeping {interval:.2f} seconds...")
                    time.sleep(interval)
                    title, content, pub_time = extract_news(url, source)
                    storage.add_news(source, title, url, content, pub_time)
                    print(f"  -> Saved news: {title}")
                except Exception as e:
                    print(f"  -> Failed to parse news: {e}")

            # ------------------ 抽取子链接入队 ------------------
            links = list(get_links(html, url, allow_domains))[:MAX_LINKS_PER_PAGE]
            enqueue_count = 0
            for link in links:
                clean_link = normalize_url(link)
                if clean_link not in in_queue and not storage.is_visited(clean_link):
                    queue.append(clean_link)
                    in_queue.add(clean_link)
                    enqueue_count = enqueue_count + 1
            if enqueue_count > 0:
                print(f"Enqueue: {enqueue_count}: Total: {len(queue)}")

        except Exception as e:
            print(f"Failed to crawl {url}: {e}")

# ------------------ 启动 ------------------
def crawl_source(name=None):
    for source in config["sources"]:
        if name is None or source["name"] == name:
            crawl_bfs(
                source=source["name"],
                seed_urls=source["root_urls"],
                allow_domains=source["allow_domains"],
                news_path_patterns=source["news_path_patterns"],
                interval_min=source["interval"]["min"],
                interval_max=source["interval"]["max"]
            )

if __name__ == "__main__":
    crawl_source('ifeng')  # 可以替换为 None 抓取所有源
    storage.save()
    print("Crawling finished.")
