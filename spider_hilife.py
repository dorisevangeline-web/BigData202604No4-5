import time, datetime, re, random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By  # 🌟 引入關鍵 By 模組
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

TARGET_KEYWORDS = ["咖啡", "拿鐵", "美式", "卡布奇諾", "冰品", "霜淇淋", "冰棒", "雪糕", "聖代", "飲料", "茶", "果汁", "汽水", "乳品", "鮮奶", "牛奶", "優酪乳", "奶茶", "啤酒", "生啤酒", "水果酒", "精釀", "發泡酒", "買一送一", "特價", "折", "超值"]
FILTER_KEYWORDS = ["icon", "logo", "arrow", "btn", "button", "footer", "header","中獎","街口支付","萊購物"]

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
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

def crawl_hilife():
    base_url = "https://www.hilife.com.tw/events_activity.aspx"
    events = []
    driver = create_driver()
    
    print(f"🌍 正在深入爬取 萊爾富 ({base_url})...")
    driver.get(base_url)
    
    seen_images = set()
    page_num = 1

    try:
        # 🌟 啟動多頁翻頁無窮迴圈機制
        while True:
            print(f"🔍 [萊爾富] 正在掃描第 {page_num} 頁...")
            time.sleep(5)
            
            # 模擬頁面滾動加載
            for _ in range(6):
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(1.2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "lxml")
            all_elements = soup.select("a, li")
            #all_elements = soup.select("a, div")
            
            page_items_count = 0
            for tag in all_elements:
                try:
                    link = tag.get("href", "").strip() if tag.name == "a" else (tag.find("a").get("href", "").strip() if tag.find("a") else "")
                    absolute_link = base_url if not link or link == "#" or "javascript" in link.lower() else urljoin(base_url, link)

                    img_tag = tag.find("img")
                    img_url = ""
                    if img_tag:
                        img_url = (img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src") or "").strip()
                    else:
                        style_attr = tag.get("style", "")
                        if "background-image" in style_attr:
                            bg_match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style_attr)
                            if bg_match: img_url = bg_match.group(1).strip()
                    
                    if not img_url: continue
                    img_url = urljoin(base_url, img_url)

                    if any(word in img_url.lower() for word in FILTER_KEYWORDS) or "logo" in img_url.lower() or img_url in seen_images:
                        continue


                    alt_text = img_tag.get("alt", "").strip() if img_tag else ""
                    title_text = tag.get("title", "").strip() if tag.name == "a" else ""

                    # 🌟 核心改寫：動態抓取標籤 (包含 <a>、<div> 等) 內的所有文字
                    # 使用 separator=" " 確保不同區塊文字不會相黏，並精準拔除 &nbsp; 與頭尾空白
                    block_text = tag.get_text(separator=" ", strip=True).replace('\xa0', '')

                    # 經由 or 機制，會優先採用這段完美的 block_text
                    event_title = alt_text or title_text or block_text or "萊爾富最新活動"
                    
                    # 依照原 app.py 白名單邏輯：萊爾富通路一律視為目標活動
                    is_target_event = True 

                    if is_target_event and len(event_title) >= 2:
                        category, expiry = parse_category_and_expiry(event_title)
                        events.append({
                            "store": "萊爾富",
                            "title": event_title[:40],
                            "img_url": img_url,
                            "link": absolute_link,
                            "category": category,
                            "expiry_date": expiry,
                            "page": page_num
                        })
                        seen_images.add(img_url)
                        page_items_count += 1
                except Exception:
                    pass
            #print(block_text)

            print(f"📖 第 {page_num} 頁掃描完畢，成功獲取 {page_items_count} 筆新優惠。")

            # === 🌟 萊爾富自動換頁 PostBack 處理邏輯 ===
            try:
                next_page_str = str(page_num + 1)
                # 使用 XPath 尋找文字內容剛好等於「下一頁碼」的 <a> 標籤
                xpath_query = f"//a[text()='{next_page_str}']"
                next_btns = driver.find_elements(By.XPATH, xpath_query)

                if next_btns and len(next_btns) > 0:
                    next_btn = next_btns[0]
                    # 執行 JavaScript 點擊換頁按鈕，觸發後台 __doPostBack 重新整理
                    driver.execute_script("arguments[0].click();", next_btn)
                    print(f"👉 成功點擊第 {next_page_str} 頁按鈕，等待新頁面資料重新載入...")
                    page_num += 1
                else:
                    print("🛑 找不到後續頁碼按鈕，已到達最終頁。結束爬取。")
                    break
            except Exception as e:
                 print(f"🛑 換頁程序異常或已到最終頁: {e}")
                 break
    finally:
        driver.quit()
        
    print(f"\n✅ 萊爾富爬取任務全部結束！總計跨頁抓到 {len(events)} 筆活動！")
    return events

if __name__ == "__main__":
    results = crawl_hilife()
    for idx, item in enumerate(results, 1):
        print(f"[{idx}] (第{item['page']}頁) {item['title']} | 分類: {item['category']} | 連結: {item['link']}")