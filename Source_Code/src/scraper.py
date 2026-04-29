import requests
import base64
import json
from bs4 import BeautifulSoup, Comment
import pandas as pd
import sqlite3
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re
import os
import unicodedata
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
cache = {}
def get_fbref_data_bs4():
    url = "https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats"

    driver = uc.Chrome()
    driver.get(url)

    while True:
        html = driver.page_source
        if "Just a moment" not in html:
            print("✅ Đã vượt Cloudflare")
            break
        time.sleep(3)

    soup = BeautifulSoup(html, "html.parser")
    driver.quit()

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    table = None
    for c in comments:
        if "stats_standard" in c:
            soup_comment = BeautifulSoup(c, "html.parser")
            table = soup_comment.find("table", {"id": "stats_standard"})
            break

    if table is None:
        raise Exception("❌ Không tìm thấy bảng")

    players_data = []
    rows = table.find("tbody").find_all("tr")

    for row in rows:
        if row.get("class") == ["thead"]:
            continue

        player_data = {}

        name_tag = row.find("th", {"data-stat": "player"})
        if name_tag:
            player_data["player"] = name_tag.text.strip()

        cells = row.find_all("td")

        for cell in cells:
            stat = cell.get("data-stat")
            if not stat:
                continue

            # position lấy text
            if stat == "position":
                value = cell.text.strip()
            else:
                value = cell.get("csk") if cell.get("csk") else cell.text.strip()

            # fix nation (100% hết cờ)
            if stat == "nation":
                raw = cell.text.strip()
                match = re.findall(r"[A-Z]{3}", raw)
                value = match[0] if match else "N/a"

            if value == "":
                value = "N/a"

            player_data[stat] = value

        mins = player_data.get("minutes")

        try:
            if mins is None or int(mins) <= 90:
                continue
        except:
            continue

        players_data.append(player_data)

    return players_data
def normalize(name):
    name = unicodedata.normalize('NFD', name)
    name = name.encode('ascii', 'ignore').decode('utf-8')
    
    words = name.lower().split()
    words.sort()   #  KEY FIX
    
    return "".join(words)

def save_to_sqlite(data):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "players.db")
    
    conn = sqlite3.connect(db_path)
    df = pd.DataFrame(data)
    df.fillna("N/a", inplace=True)
    df.to_sql("player_stats", conn, if_exists="replace", index=False)
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player ON player_stats(player)")
    conn.close()


def init_driver():
    options = webdriver.ChromeOptions()
    # Chặn pop-up thông báo từ hệ thống trình duyệt
    prefs = {"profile.default_content_setting_values.notifications": 2}
    options.add_experimental_option("prefs", prefs)
    
    # Một số cấu hình giúp trình duyệt ổn định hơn
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized") # Mở rộng màn hình để dễ tìm phần tử
    
    return webdriver.Chrome(options=options)
def safe_get(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res
        except:
            time.sleep(2)
    return None
def fallback_search(player_name):
    query = player_name.replace(" ", "+")
    url = f"https://www.footballtransfers.com/en/search?q={query}"

    res = safe_get(url)
    if not res:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.select("a[href*='/players/']"):
        return "https://www.footballtransfers.com" + a.get("href")

    return None
def crawl_transfers(team_url, mapping):
    base = "https://www.footballtransfers.com"

    transfer_urls = [
        team_url + "/transfers",
        team_url + "/transfers/2024-2025",
        team_url + "/transfers/2025-2026"
    ]

    for url in transfer_urls:
        print("🔄 Transfers:", url)

        res = safe_get(url)
        if not res:
            continue

        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.select("a[href*='/players/']"):
            name = a.text.strip()
            href = a.get("href")

            if not name or not href:
                continue

            if href.startswith("/"):
                player_url = base + href
            else:
                player_url = href

            key = normalize(name)

            if key not in mapping:
                mapping[key] = player_url
def build_player_map():
    base = "https://www.footballtransfers.com"
    league_url = base + "/us/leagues-cups/national/uk/premier-league/2024-2025"

    res = safe_get(league_url)
    if not res:
        raise Exception("❌ Không load được league page")

    soup = BeautifulSoup(res.text, "html.parser")

    mapping = {}

    # ✅ FIX 1: lấy đúng team URL
    teams = set()

    for a in soup.select("a[href*='/teams/uk/']"):
        href = a.get("href")

        if not href:
            continue

        # nếu là relative → nối base
        if href.startswith("/"):
            full_url = base + href
        else:
            full_url = href

        # ✅ chỉ lấy URL team (loại squad/player)
        if "/teams/uk/" in full_url and full_url.count("/") <= 6:
            teams.add(full_url)

    print("✅ Total teams:", len(teams))  # phải ~20

    # ✅ crawl squad từng team
    for team_url in teams:
        squad_url = team_url.rstrip("/") + "/squad"
        print("➡️ Team:", squad_url)

        res2 = safe_get(squad_url)
        if not res2:
            print("⚠️ skip:", squad_url)
            continue
        crawl_transfers(team_url, mapping)
        soup2 = BeautifulSoup(res2.text, "html.parser")

        for p in soup2.select("a[href*='/players/']"):
            name = p.text.strip()
            href = p.get("href")

            if not name or not href:
                continue

            # FIX URL
            if href.startswith("/"):
                player_url = base + href
            else:
                player_url = href

            key = normalize(name)

            if key not in mapping:
                mapping[key] = player_url

        time.sleep(1)

    print("✅ Total players mapped:", len(mapping))
    return mapping
def extract_etv_from_js(html):
    try:
        # tìm JSON trong script
        match = re.search(r'chartData\s*=\s*(\{.*?\});', html)

        if not match:
            return "N/a"

        data = json.loads(match.group(1))

        values = []
        for point in data.get("data", []):
            if point.get("value"):
                values.append(int(point["value"]))

        return max(values) if values else "N/a"

    except Exception as e:
        print("⚠️ JS extract lỗi:", e)
        return "N/a"    
def extract_etv(html):
    soup = BeautifulSoup(html, "html.parser")

    # 🔥 CASE 1: base64 (Casemiro)
    graph = soup.select_one(".player-graph")
    if graph:
        data_base64 = graph.get("data-base64")
        if data_base64:
            try:
                decoded = base64.b64decode(data_base64).decode("utf-8")
                data = json.loads(decoded)

                chart = data.get("chartDates", {})
                values = []

                for date, val in chart.items():
                    if date.startswith("2024") or date.startswith("2025"):
                        if val.get("estimate"):
                            values.append(int(val["estimate"]))

                if values:
                    return max(values)

            except:
                pass

    # 🔥 CASE 2: JS (Amad Diallo)
    val = extract_etv_from_js(html)
    if val != "N/a":
        return val

    return "N/a"
def get_etv_for_player(player_name, player_map):
    # ✅ cache
    if player_name in cache:
        return cache[player_name]

    url = player_map.get(normalize(player_name))

    # ✅ fallback nếu không match
    if not url:
        url = fallback_search(player_name)

    if not url:
        print("❌ Không match:", player_name)
        cache[player_name] = "N/a"
        return "N/a"

    try:
        res = safe_get(url)
        value = extract_etv(res.text) if res else "N/a"

        cache[player_name] = value
        return value

    except Exception as e:
        print(f"⚠️ Lỗi {player_name}: {e}")
        return "N/a"
    
def save_map(mapping):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    map_path = os.path.join(current_dir, "player_map.json")
    
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)

def load_map():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    map_path = os.path.join(current_dir, "player_map.json")
    
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None
    

def save_etv_table():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "players.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_values (
            player TEXT PRIMARY KEY,
            transfer_value TEXT
        )
    """)

    player_map = load_map()

    if not player_map:
        print("🚀 Building player map...")
        player_map = build_player_map()
        save_map(player_map)

    cursor.execute("SELECT player FROM player_stats")
    players = cursor.fetchall()

    import random

    for (player,) in players:
        print("Đang xử lý:", player)

        value = get_etv_for_player(player, player_map)

        cursor.execute("""
            INSERT OR REPLACE INTO player_values (player, transfer_value)
            VALUES (?, ?)
        """, (player, value))

        time.sleep(0.5 + random.random())  # anti-block

    conn.commit()
    conn.close()
if __name__ == "__main__":
    data = get_fbref_data_bs4()
    save_to_sqlite(data)

    save_etv_table()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "players.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n=== FINAL JOIN RESULT ===")

    query = """
    SELECT ps.player, ps.minutes, pv.transfer_value
    FROM player_stats ps
    LEFT JOIN player_values pv
    ON ps.player = pv.player
    """

    for row in cursor.execute(query):
        print(row)

    conn.close()

    print("✅ DONE")