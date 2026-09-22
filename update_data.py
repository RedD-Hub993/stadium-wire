import requests
from bs4 import BeautifulSoup
import json
import datetime

# 1. スクレイピング先のURL（例：YahooスポーツニュースのRSS）
url = 'https://news.yahoo.co.jp/rss/sports.xml'

# 2. データの取得と解析
response = requests.get(url)
soup = BeautifulSoup(response.content, 'xml')

news_list = []
# 最新の5件を取得
for item in soup.find_all('item')[:5]:
    news_list.append({
        'title': item.title.text,
        'link': item.link.text,
        'date': item.pubDate.text
    })

# メタデータ（いつ更新されたか）も追加
data = {
    "last_updated": datetime.datetime.now().isoformat(),
    "articles": news_list
}

# 3. JSONファイルとして書き出し
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("data.jsonの更新が完了しました！")
