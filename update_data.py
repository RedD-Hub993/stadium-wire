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
# 高速で無料枠に最適なモデルを指定
model = genai.GenerativeModel('gemini-1.5-flash')

# サイト名とカテゴリの定義
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

# Geminiで翻訳と要約を生成する関数
def generate_i18n(title, description):
    prompt = f"""
    以下のスポーツニュース記事のタイトルと概要を読み、5つの言語（英語、日本語、スペイン語、中国語、フランス語）で、それぞれ「魅力的なタイトル」と「2〜3文の短い要約」を作成してください。
    必ず以下のJSONフォーマットのみを出力し、Markdown記法（```jsonなど）は絶対に含めないでください。

    [元記事]
    タイトル: {title}
    概要: {description}

    [出力JSON]
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
        text = response.text.strip()
        # JSON以外の余計な文字をクリーニング
        if text.startswith("```json"): text = text[7:-3].strip()
        elif text.startswith("```"): text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # 失敗した場合は原文をそのまま入れる
        return {
            lang: {"title": title, "summary": description[:100]+"..."} 
            for lang in ["en", "ja", "es", "zh", "fr"]
        }

articles_data = []

for site_key, url in rss_urls.items():
    print(f"Fetching {site_key}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        
        # 各サイト最新3件を取得（無料枠の制限を超えないよう調整）
        for idx, item in enumerate(soup.find_all('item')[:3]):
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            desc = item.description.text if item.description else ""
            pub_date = item.pubDate.text if item.pubDate else datetime.datetime.now().isoformat()
            
            print(f"  -> AI処理中: {title}")
            i18n_data = generate_i18n(title, desc)
            
            articles_data.append({
                "id": f"{site_key}-{idx}",
                "sport": source_info[site_key]["sport"],
                "region": source_info[site_key]["region"],
                "topics": ["biz", "team"], # タグ（必要に応じてAIに判定させることも可能）
                "published_at": pub_date,
                "source_name": source_info[site_key]["name"],
                "source_url": link,
                "i18n": i18n_data
            })
            
            # Gemini無料枠の制限（15回/分）を回避するため、4秒待つ
            time.sleep(4)
            
    except Exception as e:
        print(f"Error fetching {site_key}: {e}")

# JSON出力
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(articles_data, f, ensure_ascii=False, indent=2)

print("自動更新とAI要約が完了しました！")
