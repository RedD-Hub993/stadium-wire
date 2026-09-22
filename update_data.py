import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import time
import google.generativeai as genai

# Gemini APIの準備
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set!")
genai.configure(api_key=api_key)

# 変更点: JSON形式での出力を強制し、エラーを防ぐ
model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})

source_info = {
    "yahoo_jp": {"name": "Yahoo!スポーツ", "region": "japan", "sport": "general"},
    "nhk": {"name": "NHKスポーツ", "region": "japan", "sport": "general"},
    "espn": {"name": "ESPN", "region": "global", "sport": "general"},
    "bbc": {"name": "BBC Sport", "region": "global", "sport": "general"}
}

rss_urls = {
    "yahoo_jp": "https://news.yahoo.co.jp/rss/sports.xml",
    "nhk": "https://www.nhk.or.jp/rss/news/cat6.xml",
    "espn": "https://www.espn.com/espn/rss/news",
    "bbc": "http://feeds.bbci.co.uk/sport/rss.xml"
}

def generate_i18n(title, description):
    # 変更点: スポーツ以外のニュースを弾く指示
    prompt = f"""
    あなたはスポーツニュースの専門エディターです。以下の記事を読み、5つの言語に翻訳・要約してください。
    ただし、記事の内容が「スポーツに全く関係のない一般的なニュース（事件、政治、ビジネスなど）」である場合は、すべての言語のtitleに "SKIP" とだけ出力してください。

    [元記事]
    タイトル: {title}
    概要: {description}

    [出力JSONフォーマット]
    {{
      "en": {{"title": "...", "summary": "..."}},
      "ja": {{"title": "...", "summary": "..."}},
      "es": {{"title": "...", "summary": "..."}},
      "zh": {{"title": "...", "summary": "..."}},
      "fr": {{"title": "...", "summary": "..."}}
    }}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None # エラー時はNoneを返す

articles_data = []

for site_key, url in rss_urls.items():
    print(f"Fetching {site_key}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        
        for idx, item in enumerate(soup.find_all('item')[:3]):
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            desc = item.description.text if item.description else ""
            pub_date = item.pubDate.text if item.pubDate else datetime.datetime.now().isoformat()
            
            print(f"  -> AI処理中: {title}")
            i18n_data = generate_i18n(title, desc)
            
            # 変更点: APIエラー時や、非スポーツニュース(SKIP)の場合はサイトに載せない
            if i18n_data is None or i18n_data.get("en", {}).get("title") == "SKIP":
                print("     => スキップされました（非スポーツ、またはエラー）")
                continue
            
            articles_data.append({
                "id": f"{site_key}-{idx}",
                "sport": source_info[site_key]["sport"],
                "region": source_info[site_key]["region"],
                "topics": ["biz", "team"],
                "published_at": pub_date,
                "source_name": source_info[site_key]["name"],
                "source_url": link,
                "i18n": i18n_data
            })
            
            # 変更点: 待機時間を8秒に増やし、API制限を回避
            time.sleep(8)
            
    except Exception as e:
        print(f"Error fetching {site_key}: {e}")

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(articles_data, f, ensure_ascii=False, indent=2)

print("完了しました！")
