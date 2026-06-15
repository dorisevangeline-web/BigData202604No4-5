import time, random, datetime, re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

TARGET_KEYWORDS = ["咖啡", "拿鐵", "美式", "卡布奇諾", "冰品", "霜淇淋", "冰棒", "雪糕", "聖代", "飲料", "茶", "果汁", "汽水", "乳品", "鮮奶", "牛奶", "優酪乳", "奶茶", "啤酒", "生啤酒", "水果酒", "精釀", "發泡酒", "買一送一", "特價", "折", "超值","摩卡","國際啤酒節","0604happybeer"]
FILTER_KEYWORDS = ["icon", "logo", "arrow", "btn", "button", "footer", "header", "facebook", "instagram", "循環杯", "中獎","頂級好米","the taste of home always with you","open!plaza", "開幕主題活動","op","提袋","循環杯","1212kid"]

def parse_category_and_expiry(title):
    category = "其他"
    if any(k in title for k in ["咖啡", "拿鐵", "美式", "卡布奇諾"]): category = "咖啡"
    elif any(k in title for k in ["冰品", "霜淇淋", "冰棒", "雪糕", "聖代"]): category = "冰品"
    elif any(k in title for k in ["乳品", "鮮奶", "牛奶", "優酪乳"]): category = "乳品"
    elif any(k in title for k in ["啤酒", "生啤酒", "水果酒", "精釀", "發泡酒"]): category = "啤酒"
    elif any(k in title for k in ["飲料", "茶", "水", "果汁", "汽水", "奶茶"]): category = "飲料"
    
    expiry = (datetime.date.today() + datetime.timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
    return category, expiry

def crawl_711():
    urls = ["https://www.7-11.com.tw/special/newsList.aspx", "https://www.citycafe.com.tw/notice.aspx"]
    events = []
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        for base_url in urls:
            print(f"🌍 正在深入爬取 7-11 ({base_url})...")
            driver.get(base_url)
            time.sleep(5)
            for _ in range(6): driver.execute_script("window.scrollBy(0, 600);"); time.sleep(1.5)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            seen_images = set()
            for tag in soup.select("a, div"):
                try:
                    # 1. 取得初步的 href 屬性值
                    link = tag.get("href", "").strip() if tag.name == "a" else (tag.find("a").get("href", "").strip() if tag.find("a") else "")
                    
                    # 2. 依據不同的 base_url 進行特定的 JavaScript 解析與連結處理
                    if base_url == "https://www.7-11.com.tw/special/newsList.aspx":
                        if "javascript:galogopenwin" in link.lower():
                            matches = re.findall(r"'([^']+)'", link)
                            if len(matches) >= 3:
                                link = matches[2]  # 將 link 替換為實際的網址參數
                        
                        # 7-11 專用絕對連結處理：避免剛解析出來的網址被誤判為 javascript 忽略掉
                        absolute_link = base_url if not link or link == "#" or link.lower().startswith("javascript") else urljoin(base_url, link)
                    else:
                        # City Cafe 或其他網址的原始處理方式
                        absolute_link = base_url if not link or link == "#" or "javascript" in link.lower() else urljoin(base_url, link)
                    
                    # -----------------------------------------------
                    # 以下為原本的圖片與標題擷取邏輯，維持不變
                    # -----------------------------------------------
                    img_tag = tag.find("img")
                    img_url = (img_tag.get("data-src") or img_tag.get("src") or "").strip() if img_tag else ""
                    if not img_url: continue
                    img_url = "https:" + img_url if img_url.startswith("//") else urljoin(base_url, img_url)

                    if any(w in img_url.lower() for w in FILTER_KEYWORDS) or img_url in seen_images: continue

                    title_text = tag.get("title", "").strip() if tag.name == "a" else ""
                    alt_text = img_tag.get("alt", "").strip() if img_tag else ""
                    event_title = alt_text or title_text or tag.get_text(strip=True).strip() or "7-11 最新活動"
                    combined_text = (alt_text + " " + title_text + " " + tag.get_text(strip=True).strip()).lower()

                    if any(k in combined_text for k in FILTER_KEYWORDS): is_target = False
                    elif any(k in combined_text for k in TARGET_KEYWORDS): is_target = True
                    else: is_target = any(k in (absolute_link + img_url).lower() for k in ["event", "activity", "promo"])

                    if is_target and len(event_title) >= 2:
                        cat, exp = parse_category_and_expiry(event_title)
                        events.append({"store": "7-11", "title": event_title[:40], "img_url": img_url, "link": absolute_link, "category": cat, "expiry_date": exp})
                        seen_images.add(img_url)
                except: pass
    finally:
        driver.quit()
    print(f"✅ 7-11 爬取完成！共抓到 {len(events)} 筆。")
    return events

if __name__ == "__main__":
    result_data = crawl_711()
    for item in result_data:
        print(item)