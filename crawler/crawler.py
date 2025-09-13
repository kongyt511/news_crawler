import json, random, time
import re
import sys
import threading
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
def is_allowed(url, allow_domains, blank_list_patterns):
    domain = urlparse(url).netloc
    return any(d in domain for d in allow_domains) and not any(re.search(p, url) for p in blank_list_patterns)

def is_news(url, news_path_patterns):
    return any(re.search(pattern, url) for pattern in news_path_patterns)

def normalize_url(url):
    """去掉 URL 的 query 和 fragment 部分"""
    parts = urlparse(url)
    clean_parts = parts._replace(query="", fragment="")
    return urlunparse(clean_parts)

def get_links(html, base_url, allow_domains, blank_list_patterns):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        new_url = urljoin(base_url, a['href'])
        if new_url.startswith("http") and is_allowed(new_url, allow_domains, blank_list_patterns):
            links.add(new_url)
    return links

# ------------------ BFS 爬虫 ------------------
MAX_LINKS_PER_PAGE = 65536  # 每页抓取最大链接数

def crawl_bfs(source, seed_urls, allow_domains, blank_list_patterns, news_path_patterns, interval_min, interval_max):
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

        print(f"Crawling: {url}, Queue size: {len(queue)}")
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
            links = list(get_links(html, url, allow_domains, blank_list_patterns))[:MAX_LINKS_PER_PAGE]
            enqueue_count = 0
            for link in links:
                clean_link = normalize_url(link)
                if clean_link not in in_queue and not storage.is_visited(clean_link) and is_news(clean_link, news_path_patterns):
                    queue.append(clean_link)
                    in_queue.add(clean_link)
                    enqueue_count = enqueue_count + 1
            for link in links:
                clean_link = normalize_url(link)
                if clean_link not in in_queue and not storage.is_visited(clean_link) and not is_news(clean_link, news_path_patterns):
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
                blank_list_patterns=source["blank_list_patterns"],
                news_path_patterns=source["news_path_patterns"],
                interval_min=source["interval"]["min"],
                interval_max=source["interval"]["max"]
            )
    print("Crawling finished.")

def crawl_source_all():
    threads = []

    for source in config["sources"]:
        t = threading.Thread(
            target=crawl_bfs,
            args=(
                source["name"],
                source["root_urls"],
                source["allow_domains"],
                source["blank_list_patterns"],
                source["news_path_patterns"],
                source["interval"]["min"],
                source["interval"]["max"],
            ),
            daemon=True  # 主线程退出时自动结束
        )
        t.start()
        threads.append(t)
        print(f"[Thread] Started crawling source: {source['name']}")

    # 等待所有线程结束
    for t in threads:
        t.join()

    print("All crawling finished.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        crawl_source_all()
    else:
        crawl_source(sys.argv[1])