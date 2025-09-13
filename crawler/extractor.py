from newspaper import Article
from bs4 import BeautifulSoup
from datetime import datetime
import re


# ------------------ 各网站定制解析 ------------------

def parse_sina(html: str):
    """新浪新闻解析：返回 (title, publish_date, text)"""
    soup = BeautifulSoup(html, "html.parser")

    # ----------------- 标题 -----------------
    title = None

    # ----------------- 时间 -----------------
    publish_date = None

    # ----------------- 正文 -----------------
    text = None
    article_tag = soup.find("div", id="artibody")
    if article_tag:
        paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p") if p.get_text(strip=True)]
        text = "\n".join(paragraphs)

    return title, publish_date, text


def parse_eastmoney(html: str):
    """东方财富新闻解析：返回 (title, publish_date, text)"""
    soup = BeautifulSoup(html, "html.parser")

    # ----------------- 标题 -----------------
    title = None

    # ----------------- 时间 -----------------
    publish_date = None
    time_tag = None
    tipbox = soup.find("div", class_="tipbox")
    if tipbox:
        infos = tipbox.find("div", class_="infos")
        if infos:
            # infos 里面有很多 div/p，找到包含日期的
            for child in infos.find_all(["div", "span", "p"]):
                text = child.get_text(strip=True)
                if re.search(r"\d{4}年\d{2}月\d{2}日", text):
                    time_tag = text
                    break
    if time_tag:
        try:
            publish_date = datetime.strptime(time_tag, "%Y年%m月%d日 %H:%M")
        except Exception:
            pass
    else:
        # 正则兜底
        m = re.search(r"(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})", html)
        if m:
            try:
                publish_date = datetime.strptime(m.group(1), "%Y年%m月%d日 %H:%M")
            except:
                pass

    # ----------------- 正文 -----------------
    text = None
    article_tag = soup.find("div", id="ContentBody")
    if article_tag:
        paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p") if p.get_text(strip=True)]
        text = "\n".join(paragraphs)

    return title, publish_date, text


def parse_sohu(html: str):
    """东方财富新闻解析：返回 (title, publish_date, text)"""
    soup = BeautifulSoup(html, "html.parser")

    # ----------------- 标题 -----------------
    title = None

    # ----------------- 时间 -----------------
    publish_date = None
    time_tag = soup.find("span", id="news-time")
    if not time_tag:
        time_tag = soup.find("span", class_="content-main-desc--time")

    if time_tag:
        try:
            publish_date = datetime.strptime(time_tag.get_text(strip=True), "%Y-%m-%d %H:%M")
        except Exception:
            publish_date = time_tag.get_text(strip=True)

    # ----------------- 正文 -----------------
    article_tag = soup.find("article", id="mp-editor")
    if not article_tag:
        article_tag = soup.find("div", class_=re.compile(r"content-main-detail"))
    text = None
    if article_tag:
        paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p") if p.get_text(strip=True)]
        text = "\n".join(paragraphs)

    return title, publish_date, text

def parse_ifeng(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # ----------------- 标题 -----------------
    title = None

    # ----------------- 时间 -----------------
    publish_date = None
    time_tag = soup.find("div", class_=re.compile(r"index_timeBref"))
    if time_tag:
        # 可能包含 “来自北京”，只保留日期时间部分
        publish_date = time_tag.get_text(strip=True).split("来自")[0].strip()

    # ----------------- 正文 -----------------
    text = None
    article_tag = soup.find("div", class_=re.compile(r"index_text"))
    if article_tag:
        paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p") if p.get_text(strip=True)]
        text = "\n".join(paragraphs)

    return title, publish_date, text

def parse_news163(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # ----------------- 标题 -----------------
    title = None

    # ----------------- 时间 -----------------
    publish_date = None

    # ----------------- 正文 -----------------
    text = None
    content_div = soup.find("div", class_="post_body")
    if content_div:
        paragraphs = content_div.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return title, publish_date, text

# ------------------ 解析器注册表 ------------------
CUSTOM_EXTRACTORS = {
    "sina": parse_sina,
    "eastmoney": parse_eastmoney,
    "sohu": parse_sohu,
    "ifeng": parse_ifeng,
    "news163": parse_news163,
}


# ------------------ 可扩展的 Article ------------------
class News(Article):
    def __init__(self, url, source):
        self.source = source
        self.publish_date = None
        self.title = None
        self.text = None
        super(News, self).__init__(url)

    def parse(self):
        # 默认 newspaper 解析
        super().parse()

        # 如果有自定义解析器，就覆盖
        extractor = CUSTOM_EXTRACTORS.get(self.source)
        if extractor:
            try:
                title, pub_date, text = extractor(self.html)
                if title and bool(self.title) == False:
                    self.title = title
                if pub_date and bool(self.publish_date) == False:
                    self.publish_date = pub_date
                if text and bool(self.text) == False:
                    self.text = text
            except Exception as e:
                print(f"[Extractor] Failed custom parse for {self.source}: {e}")


# ------------------ 对外统一接口 ------------------
def extract_news(url, source):
    """
    抽取新闻的统一入口
    :param url: 新闻 URL
    :param source: 来源站点名，对应 CUSTOM_EXTRACTORS 的 key
    :return: (title, text, publish_date)
    """
    article = News(url, source)
    article.download()
    article.parse()
    return article.title, article.text, article.publish_date
