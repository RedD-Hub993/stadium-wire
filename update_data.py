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

# JSON形式での出力を強制し、エラーを防ぐ
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
    prompt = f"""
    あなたはスポーツニュースの専門エディターです。以下の記事を読み、5つの言語に翻訳・要約してください。
    ただし、記事の内容が「スポーツに全く関係のない一般的なニュース（事件、政治、ビジネスなど）」である場合は、すべての言語のtitleに "SKIP" とだけ出力してください。
    ※選手、チーム、スポーツビジネス、大会運営に関する内容はスポーツニュースとして扱ってください。

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
        return None

# 1サイトあたり取得したいスポーツ記事の目標件数
TARGET_ARTICLES = 3 
articles_data = []

for site_key, url in rss_urls.items():
    print(f"Fetching {site_key}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        
        success_count = 0 # 取得できたスポーツ記事の数をカウント
        
        # 変更点: [:3] の制限を外し、すべての記事を順番にチェックする
        for idx, item in enumerate(soup.find_all('item')):
            # 目標の件数に達したら、このサイトの処理を終了して次へ
            if success_count >= TARGET_ARTICLES:
                print(f"  => {TARGET_ARTICLES}件のスポーツ記事を取得完了しました。")
                break
                
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            desc = item.description.text if item.description else ""
            pub_date = item.pubDate.text if item.pubDate else datetime.datetime.now().isoformat()
            
            print(f"  -> AI処理中 ({success_count+1}件目を探しています): {title}")
            i18n_data = generate_i18n(title, desc)
            
            # APIエラー時や、非スポーツニュース(SKIP)の場合は次へ
            if i18n_data is None or i18n_data.get("en", {}).get("title") == "SKIP":
                print("     => スキップされました（次の記事を探します）")
                time.sleep(4) # 連続リクエストを避けるための待機
                continue
            
            # 無事にスポーツ記事だと判定されたらデータを追加
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
            
            success_count += 1 # 成功カウントを増やす
            time.sleep(8) # API制限を回避するための待機
            
    except Exception as e:
        print(f"Error fetching {site_key}: {e}")

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(articles_data, f, ensure_ascii=False, indent=2)

print("完了しました！")
