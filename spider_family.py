import time, datetime, re, random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

TARGET_KEYWORDS = ["咖啡", "拿鐵", "美式", "卡布奇諾", "冰品", "霜淇淋", "冰棒", "雪糕", "聖代", "飲料", "茶", "果汁", "汽水", "乳品", "鮮奶", "牛奶", "優酪乳", "奶茶", "啤酒", "生啤酒", "水果酒", "精釀", "發泡酒", "買一送一", "特價", "折", "超值"]
FILTER_KEYWORDS = ["icon", "logo", "arrow", "btn", "button", "footer", "header", "svg", "facebook", "instagram", "line", "download", "店到店", "pdf", "限定門市", "便利生活", "juice", "beer", "蔬", "openpoint", "飲料杯", "提袋", "pass", "國泰", "ecoco", "購票", "洗衣", "地圖", "悠遊", "picard", "集章", "週期購", "寄物", "appstore", "wallet", "循環杯", "中獎", "錢包", "lbcweb", "plus", "gift", "creditcard", "famipoint", "智慧財產權", "familaundry","fm eshop","qrcode","全家你家都能取"]

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def parse_category_and_expiry(title):
    category = "其他"
    if any(k in title for k in ["咖啡", "拿鐵", "美式", "卡布奇諾"]): category = "咖啡"
    elif any(k in title for k in ["冰品", "霜淇淋", "冰棒", "雪糕", "聖代"]): category = "冰品"
    elif any(k in title for k in ["乳品", "鮮奶", "牛奶", "優酪乳"]): category = "乳品"
    elif any(k in title for k in ["啤酒", "生啤酒", "水果酒", "精釀", "發泡酒"]): category = "啤酒"
    elif any(k in title for k in ["飲料", "茶", "水", "果汁", "汽水", "奶茶"]): category = "飲料"
    expiry_date = (datetime.date.today() + datetime.timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
    return category, expiry_date

def crawl_family():
    base_url = "https://www.family.com.tw/Marketing/zh/Event"
    events = []
    driver = create_driver()
    
    try:
        print(f"🌍 正在深入爬取 全家超商 ({base_url})...")
        driver.get(base_url)
        time.sleep(5)
        
        # 模擬滾動以載入延遲圖片
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        #soup = BeautifulSoup(driver.page_source, "html.parser")
        soup = BeautifulSoup(driver.page_source, "lxml")
        seen_images = set()
        all_elements = soup.select("a, div")
        
        for tag in all_elements:
            try:
                link = tag.get("href", "").strip() if tag.name == "a" else (tag.find("a").get("href", "").strip() if tag.find("a") else "")
                absolute_link = base_url if not link or link == "#" or "javascript" in link.lower() else urljoin(base_url, link)
                
                img_tag = tag.find("img")
                img_url = ""
                if img_tag:
                    # 🌟 修正點：優先抓取 data-src 避免抓到 lazy-load 的空白預留圖
                    img_url = (img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src") or "").strip()
                
                if not img_url and "background-image" in tag.get("style", ""):
                    match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', tag.get("style", ""))
                    if match: img_url = match.group(1).strip()
                    
                if not img_url: continue
                img_url = urljoin(base_url, img_url)

                if any(word in img_url.lower() for word in FILTER_KEYWORDS) or "logo" in img_url.lower() or img_url in seen_images:
                    continue

                alt_text = img_tag.get("alt", "").strip() if img_tag else ""
                title_text = tag.get("title", "").strip() if tag.name == "a" else ""
                block_text = tag.get_text(strip=True).strip()
                
                event_title = alt_text or title_text or block_text or "全家最新活動"
                combined_text = (alt_text + " " + title_text + " " + block_text).lower()

                # 🌟 修正點：先比對目標關鍵字，再過濾無關內容，避免全家 "app" 詞彙被誤殺
                if any(key.lower() in combined_text for key in TARGET_KEYWORDS):
                    is_target_event = True
                elif any(key.lower() in combined_text for key in FILTER_KEYWORDS):
                    is_target_event = False  
                else:
                    url_text = (absolute_link + img_url).lower()
                    is_target_event = any(k in url_text for k in ["event", "activity", "campaign", "promo", "banner"])

                if is_target_event and len(event_title) >= 2:
                    category, expiry = parse_category_and_expiry(event_title)
                    events.append({
                        "store": "全家",
                        "title": event_title[:40],
                        "img_url": img_url,
                        "link": absolute_link,
                        "category": category,
                        "expiry_date": expiry
                    })
                    seen_images.add(img_url)
            except Exception:
                pass
    finally:
        driver.quit()
        
    print(f"✅ 全家 爬取完成！共抓到 {len(events)} 筆活動。")
    return events

if __name__ == "__main__":
    results = crawl_family()
    for idx, item in enumerate(results, 1):
        print(f"[{idx}] {item['title']} | 分類: {item['category']} | 連結: {item['link']}")