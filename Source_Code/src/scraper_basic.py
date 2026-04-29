import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import sqlite3
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_fbref_data_bs4():
    url = "https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats"

    driver = uc.Chrome(headless=False)
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


def save_to_sqlite(data):
    conn = sqlite3.connect("players.db")
    df = pd.DataFrame(data)
    df.fillna("N/a", inplace=True)
    df.to_sql("player_stats", conn, if_exists="replace", index=False)
    conn.close()


def init_driver():
    options = webdriver.ChromeOptions()
    return webdriver.Chrome(options=options)  # ❌ bỏ headless


def get_transfer_value(driver, player_name, team_name):
    try:
        wait = WebDriverWait(driver, 10)
        driver.set_page_load_timeout(15)

        team_name = team_name.replace("Utd", "United")

        query = f"{player_name} {team_name}"
        driver.get(f"https://www.footballtransfers.com/en/search?q={query}")

        first_player = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/players/']"))
        )

        try:
            first_player.click()
        except:
            return "N/a"

        values = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.player-tag"))
        )

        if values:
            return values[0].text.strip()

        return "N/a"

    except Exception as e:
        print(f"❌ Error {player_name}: {e}")
        return "N/a"


def save_transfer_data():
    conn = sqlite3.connect("players.db")
    cursor = conn.cursor()

    driver = init_driver()

    cursor.execute("SELECT player, team FROM player_stats")
    players = cursor.fetchall()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_values (
            player TEXT,
            transfer_value TEXT
        )
    """)

    for i, (player, team) in enumerate(players):

        # ✅ restart driver tránh crash
        if i % 10 == 0:
            driver.quit()
            driver = init_driver()

        print("Đang xử lý:", player, "|", team)

        value = get_transfer_value(driver, player, team)

        cursor.execute("""
            INSERT OR REPLACE INTO player_values (player, transfer_value)
            VALUES (?, ?)
        """, (player, value))

        print("→", value)

        time.sleep(2)  # tránh bị block

    conn.commit()
    conn.close()
    driver.quit()


if __name__ == "__main__":
    data = get_fbref_data_bs4()
    save_to_sqlite(data)

    save_transfer_data()

    conn = sqlite3.connect("players.db")
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