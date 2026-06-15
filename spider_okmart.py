# spider_okmart_V3.py

import time
import random
import datetime

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager

from urllib.parse import urljoin


# ==========================================
# 過濾條件
# ==========================================

FILTER_KEYWORDS = [
    "icon",
    "logo",
    "arrow",
    "btn",
    "button",
    "footer",
    "header",
    "facebook",
    "instagram",
    "youtube",
    "line",
    "svg",
]

TITLE_FILTERS = [
    "facebook",
    "instagram",
    "youtube",
    "line",
    "logo",
    "icon",
    "更多",
    "查看更多",
    "了解更多",
    "立即前往",
    "回首頁",
    "首頁",
    "下載app",
    "下載APP",
    "會員登入",
    "會員中心",
    "登入",
    "註冊",
    "客服",
    "聯絡我們",
    "關於我們",
    "代收房屋稅",
    "代收房屋稅","共享","客製車牌號碼悠遊卡","週五會員日最高5%回饋","台灣PAY筆筆20%回饋","台鐵","繳交電信費","涼一夏"
]


# ==========================================
# 分類
# ==========================================

def parse_category_and_expiry(title):

    category = "其他"

    if any(x in title for x in ["咖啡", "拿鐵", "美式", "CITY"]):
        category = "咖啡"

    elif any(x in title for x in ["霜淇淋", "冰品", "雪糕"]):
        category = "冰品"

    elif any(x in title for x in ["飲料", "茶", "奶茶"]):
        category = "飲料"

    elif any(x in title for x in ["便當", "飯糰", "鮮食"]):
        category = "鮮食"

    elif any(x in title for x in ["集點", "會員"]):
        category = "會員活動"

    expiry = (
        datetime.date.today()
        + datetime.timedelta(days=random.randint(3, 14))
    ).strftime("%Y-%m-%d")

    return category, expiry


# ==========================================
# OK超商爬蟲
# ==========================================

def crawl_okmart():

    base_url = "https://www.okmart.com.tw/promotion_reference"

    events = []

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:

        print(f"🌍 開始爬取 OK超商：{base_url}")

        driver.get(base_url)

        time.sleep(5)

        # 自動滾動
        for _ in range(10):

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(1.5)

        soup = BeautifulSoup(
            driver.page_source,
            "lxml"
        )

        seen_images = set()
        seen_titles = set()

        candidates = soup.select(
            "a, div, dl, article, section, li"
        )

        print(f"找到 {len(candidates)} 個候選區塊")

        for tag in candidates:

            try:

                # ==========================
                # 圖片
                # ==========================

                img_tag = tag.find("img")

                if not img_tag:
                    continue

                img_url = (
                    img_tag.get("src", "")
                    or img_tag.get("data-src", "")
                ).strip()

                if not img_url:
                    continue

                img_url = urljoin(base_url, img_url)

                # 圖片過濾
                if any(
                    x.lower() in img_url.lower()
                    for x in FILTER_KEYWORDS
                ):
                    continue

                if img_url in seen_images:
                    continue

                # ==========================
                # 標題
                # ==========================

                title = tag.get_text(
                    separator=" ",
                    strip=True
                )

                title = " ".join(title.split())

                if not title:
                    continue

                if len(title) < 8:
                    continue

                if any(
                    x.lower() in title.lower()
                    for x in TITLE_FILTERS
                ):
                    continue

                if title in seen_titles:
                    continue

                # ==========================
                # 取得連結
                # ==========================

                link = ""

                if tag.name == "a":

                    link = tag.get(
                        "href",
                        ""
                    ).strip()

                else:

                    a_tag = tag.find("a")

                    if not a_tag:

                        parent_a = tag.find_parent("a")

                        if parent_a:
                            a_tag = parent_a

                    if a_tag:

                        link = a_tag.get(
                            "href",
                            ""
                        ).strip()

                # 無效連結
                if (
                    not link
                    or link == "#"
                    or "javascript" in link.lower()
                ):
                    abs_link = base_url

                else:
                    abs_link = urljoin(
                        base_url,
                        link
                    )

                # ==========================
                # 分類
                # ==========================

                category, expiry = (
                    parse_category_and_expiry(title)
                )

                events.append(
                    {
                        "store": "OK超商",
                        "title": title[:120],
                        "img_url": img_url,
                        "link": abs_link,
                        "category": category,
                        "expiry_date": expiry,
                    }
                )

                seen_images.add(img_url)
                seen_titles.add(title)

            except Exception:
                continue

    except Exception as e:

        print("❌ OK超商爬取失敗：", e)

    finally:

        driver.quit()

    print(f"✅ OK超商完成，共 {len(events)} 筆")

    return events


# ==========================================
# 測試
# ==========================================

if __name__ == "__main__":

    data = crawl_okmart()

    print("-" * 100)

    for i, item in enumerate(data[:20], start=1):

        print(f"[{i}] {item['title']}")
        print("圖片 :", item["img_url"])
        print("連結 :", item["link"])
        print("分類 :", item["category"])
        print("-" * 100)