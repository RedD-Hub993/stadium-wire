import requests
from bs4 import BeautifulSoup
import json
import datetime

# --- RSSから指定件数のニュースを取得する共通関数 ---
def fetch_rss(url, limit=10):
    try:
        # 海外サイトでBotとして弾かれないように「人間（ブラウザ）からのアクセス」を装う
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # ステータスコードが200（成功）以外の場合はエラーとして扱う
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        
        news_list = []
        for item in soup.find_all('item')[:limit]:
            news_list.append({
                'title': item.title.text if item.title else "No Title",
                'link': item.link.text if item.link else ""
            })
        return news_list
    except Exception as e:
        print(f"データの取得に失敗しました ({url}): {e}")
        return []

# --- ニュースを取得するサイトのURL一覧 ---
rss_urls = {
    # 日本のニュース
    "yahoo_jp": "https://news.yahoo.co.jp/rss/sports.xml",
    "nhk": "https://www.nhk.or.jp/rss/news/cat6.xml",
    "nikkan": "https://www.nikkansports.com/rss/newspool/sports.xml",
    
    # 海外のニュース
    "espn": "https://www.espn.com/espn/rss/news",                  # ESPN (米・総合)
    "bbc": "http://feeds.bbci.co.uk/sport/rss.xml",                # BBC Sport (英)
    "yahoo_us": "https://sports.yahoo.com/rss/",                   # Yahoo! Sports (米)
    "cbs": "https://www.cbssports.com/rss/headlines/",             # CBS Sports (米)
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html" # CNBC (米・ビジネス＆トップニュース)
}

# データをまとめるための辞書
articles_data = {}

# URLリストを順番に読み込んで取得していく
for site_name, url in rss_urls.items():
    print(f"{site_name} のデータを取得中...")
    articles_data[site_name] = fetch_rss(url)

# --- 取得した全データを1つのJSONにまとめる ---
data = {
    "last_updated": datetime.datetime.now().isoformat(),
    "articles": articles_data
}

# JSONファイルとして保存（日本語の文字化けを防ぐため ensure_ascii=False を指定）
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("data.jsonの更新が完了しました！")
