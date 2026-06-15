import time, random, datetime, re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

# 擴充黑名單，過濾掉常見的無效按鈕與雜訊文字
FILTER_KEYWORDS = ["icon", "logo", "arrow", "btn", "button", "footer", "header", "svg", "facebook", "了解更多", "瞭解更多", "詳細資訊", "馬上看", "中獎", 
                   "最新消息","活動日期"]

def get_clean_title(tag):
    """精準提取與清洗標題的函式"""
    # 1. 優先尋找 HTML 標準的標題標籤
    heading = tag.find(["h2", "h3", "h4", "h5", "strong"])
    if heading and heading.get_text(strip=True):
        return heading.get_text(strip=True).replace('\xa0', '')
    
    # 2. 如果沒有標題標籤，處理整塊文字並用換行符拆解
    raw_text = tag.get_text(separator="\n", strip=True).replace('\xa0', '')
    lines = [line.strip() for line in raw_text.split('\n') if len(line.strip()) > 2]
    
    # 3. 過濾掉包含日期的行與黑名單字眼
    valid_lines = [l for l in lines if not re.search(r'\d{2,4}[/.-]\d{1,2}', l) and not any(kw in l for kw in FILTER_KEYWORDS)]
    
    # 回傳第一行有效文字，若全被過濾光則回傳空字串
    return valid_lines[0] if valid_lines else ""

def parse_category_and_expiry(title):
    category = "其他"
    if any(k in title for k in ["咖啡", "拿鐵", "美式"]): category = "咖啡"
    elif any(k in title for k in ["冰品", "霜淇淋"]): category = "冰品"
    elif any(k in title for k in ["飲料", "茶"]): category = "飲料"
    
    expiry = (datetime.date.today() + datetime.timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
    return category, expiry

def crawl_pxmart():
    base_url = "https://www.pxmart.com.tw/campaign/life-will/best-buy/recommend"
    events = []
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("window-size=1920,1080")
    # 加入反爬蟲防護隱藏參數
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print(f"🌍 正在深入爬取 全聯 ({base_url})...")
        driver.get(base_url)
        time.sleep(5) # 確保首頁載入
        
        # 模擬滾動以觸發圖片與排版的懶加載 (Lazy Load)
        for _ in range(6): 
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.5)
        
        soup = BeautifulSoup(driver.page_source, "lxml")
        seen_images = set()
        
        # 選取範圍加入 li 標籤，以防有些活動是用 list 排版的
        for tag in soup.select("a, div, li"):
            try:
                # 🛠️ 核心防呆：如果該標籤內包含超過 1 個連結或 1 張圖片，代表它是外層大容器，直接跳過！
                if len(tag.find_all("a")) > 1 or len(tag.find_all("img")) > 1:
                    continue

                # 處理圖片 URL
                img_tag = tag.find("img")
                img_url = img_tag.get("src", "").strip() if img_tag else ""
                
                # 若無 img 標籤，嘗試從 style background-image 中提取
                if not img_url and "background-image" in tag.get("style", ""):
                    match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', tag.get("style", ""))
                    if match: img_url = match.group(1).strip()
                    
                if not img_url: continue
                img_url = urljoin(base_url, img_url)

                # 過濾不要的圖片與重複圖片
                if any(w in img_url.lower() for w in FILTER_KEYWORDS) or img_url in seen_images: 
                    continue

                # 🛠️ 標題清洗擷取：使用上方定義好的 get_clean_title
                title = get_clean_title(tag)
                
                # 如果標題長度太短或仍含有黑名單字眼，直接拋棄這筆資料
                if len(title) < 2 or any(k in title for k in FILTER_KEYWORDS):
                    continue
                
                # 處理點擊連結 (考慮到可能是 div 包著 a 的情況)
                link = tag.get("href", "") if tag.name == "a" else (tag.find("a").get("href", "") if tag.find("a") else "")
                abs_link = urljoin(base_url, link) if link else base_url
                
                # 解析分類與假造到期日
                cat, exp = parse_category_and_expiry(title)
                
                events.append({
                    "store": "全聯", 
                    "title": title[:40], 
                    "img_url": img_url, 
                    "link": abs_link, 
                    "category": cat, 
                    "expiry_date": exp
                })
                seen_images.add(img_url)
            except Exception: 
                pass
                
    finally:
        driver.quit()
        
    print(f"✅ 全聯 爬取完成！共抓到 {len(events)} 筆。")
    return events

if __name__ == "__main__":
    results = crawl_pxmart()
    for idx, item in enumerate(results, 1):
        print(f"[{idx}] {item['title']} | 分類: {item['category']} | 連結: {item['link']}")