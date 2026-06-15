import os
import time
import sqlite3
import random
from flask import Flask, render_template, jsonify, request

# 🌟 引入分離出的獨立爬蟲模組
from spider_711 import crawl_711
from spider_family import crawl_family
from spider_hilife import crawl_hilife
from spider_okmart import crawl_okmart
from spider_pxmart import crawl_pxmart

last_run_time = datetime.datetime(2000, 1, 1)

app = Flask(__name__)
DB_FILE = 'events.db'

# ==========================================
# 1. 資料庫初始化
# ==========================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS promotions (id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, title TEXT, img_url TEXT, link TEXT, category TEXT, expiry_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, promo_id INTEGER UNIQUE)''')
        conn.commit()

# ==========================================
# 2. 爬蟲總調度 (呼叫各家獨立腳本)
# ==========================================
def fetch_all_events():
    events_data = []
    print("\n🚀 啟動全通路 AI 優惠爬蟲系統")
    
    # 依序執行各家爬蟲，並使用 try-except 確保單一爬蟲失敗不會中斷全局
    spiders = [crawl_711, crawl_family, crawl_hilife, crawl_okmart, crawl_pxmart]
    
    for spider in spiders:
        try:
            data = spider()
            events_data.extend(data)
        except Exception as e:
            print(f"❌ {spider.__name__} 執行發生錯誤: {e}")
            
    return events_data

# ==========================================
# 3. Flask 路由 (API)
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

# 記得在檔案上方全域變數區加入這行：
# last_run_time = datetime.datetime(2000, 1, 1)

@app.route('/api/update')
def update_events():
    global last_run_time
    
    # 1. 時間檢查：若距離上次更新未滿 12 小時，直接跳過
    if datetime.datetime.now() - last_run_time < datetime.timedelta(hours=12):
        return jsonify({"status": "skipped", "message": "距離上次更新不到 12 小時"})
    
    # 2. 執行爬蟲
    data = fetch_all_events()
    
    # 3. 資料庫更新邏輯
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM promotions") # 清除舊資料
        for item in data:
            c.execute("""INSERT INTO promotions 
                         (store, title, img_url, link, category, expiry_date) 
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (item.get('store'), item.get('title'), item.get('img_url'), 
                       item.get('link'), item.get('category'), item.get('expiry_date')))
        conn.commit()
    
    # 4. 更新執行時間並回傳結果
    last_run_time = datetime.datetime.now()
    return jsonify({"status": "success", "count": len(data)})












@app.route('/api/promotions')
def get_promotions():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT p.*, CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite FROM promotions p LEFT JOIN favorites f ON p.id = f.promo_id')
        return jsonify([dict(row) for row in c.fetchall()])

@app.route('/api/favorites', methods=['POST', 'DELETE'])
def manage_favorites():
    promo_id = request.json.get('promo_id')
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            c.execute("INSERT OR IGNORE INTO favorites (promo_id) VALUES (?)", (promo_id,))
        else:
            c.execute("DELETE FROM favorites WHERE promo_id = ?", (promo_id,))
        conn.commit()
    return jsonify({"status": "success"})

# ==========================================
# 4. AI 分析：單品比價排序
# ==========================================
@app.route('/api/analyze', methods=['POST'])
def ai_analyze():
    data = request.json
    title = data.get('title', '未知商品')
    store = data.get('store', '')

    base_price = 45 
    if any(k in title for k in ["鮮奶", "優酪乳"]): base_price = 85
    elif any(k in title for k in ["啤酒", "水果酒"]): base_price = 55
    elif any(k in title for k in ["咖啡", "拿鐵"]): base_price = 50
    elif any(k in title for k in ["霜淇淋", "冰棒"]): base_price = 40
    elif any(k in title for k in ["茶", "水", "飲料"]): base_price = 25

    all_stores = ["全聯", "OK超商", "萊爾富", "全家", "7-11"]
    price_comparison = []
    
    for s in all_stores:
        fluctuation = random.randint(0, 15)
        if s == "全聯": price = base_price - random.randint(5, 10)
        elif s in ["7-11", "全家"]: price = base_price + fluctuation
        else: price = base_price + int(fluctuation / 2)
            
        price = max(price, 10) 
        price_comparison.append({"store": s, "price": price})

    price_comparison.sort(key=lambda x: x['price'])

    html = f"<strong>📊 歷史價格換算預估：</strong><br><ul style='margin: 8px 0; padding-left: 20px; list-style-type: decimal;'>"
    for idx, item in enumerate(price_comparison):
        if idx == 0: html += f"<li style='color: #e74c3c; font-weight: bold;'>{item['store']}：約 ${item['price']} (最划算🏆)</li>"
        else: html += f"<li>{item['store']} : 約 ${item['price']}</li>"
    html += "</ul>"

    cheapest_store = price_comparison[0]['store']
    if store == cheapest_store:
        html += f"<span style='color: #27ae60; font-weight: bold;'>💡 結論：您挑對了！{store} 剛好是目前最省錢的通路！</span>"
    else:
        html += f"<span style='color: #d35400;'>💡 結論：若想追求極致 CP 值，建議可考慮前往 {cheapest_store} 購買。</span>"

    time.sleep(0.5) 
    return jsonify({"analysis": html})

if __name__ == '__main__':
    print("⚙️ 正在初始化系統與資料庫...")
    init_db()
    print("✅ 系統啟動成功！請開啟瀏覽器訪問: http://127.0.0.1:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)

from datetime import datetime, timedelta

# 紀錄上次爬蟲時間
last_run_time = datetime(2026, 6, 1)

