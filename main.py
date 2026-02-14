import feedparser
import requests
import os
import json
import google.generativeai as genai
import re

# ===== 환경변수 =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===== Gemini 설정 =====
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"
DATA_FILE = "sent.json"

# ===== 1차 키워드 필터 =====
PRIMARY_KEYWORDS = [
    "bitcoin", "btc",
    "dogecoin", "doge",
    "elon musk",
    "etf", "sec",
    "approval", "ban",
    "regulation",
    "halving",
    "surge", "crash"
]

def contains_primary_keyword(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PRIMARY_KEYWORDS)

def load_sent():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ===== Gemini 분석 (JSON 반환 강제) =====
def analyze_with_gemini(text):
    prompt = f"""
You are a professional crypto analyst.

Analyze ONLY for Bitcoin (BTC) or Dogecoin (DOGE).

Return strictly in JSON format:

{{
  "coin": "BTC or DOGE or BOTH or NONE",
  "importance": 1-5,
  "reason": "short reason",
  "summary_korean": "translated summary in Korean"
}}

Rules:
- Importance 5 = market moving event (ETF approval, SEC action, Elon Musk impact, 5%+ price move)
- Importance 4 = strong investor relevance
- Importance 3 = moderate relevance
- Importance <=2 = ignore

News:
{text}
"""
    response = model.generate_content(prompt)

    try:
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except:
        return None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, data=data)

def main():
    feed = feedparser.parse(RSS_URL)
    sent_items = load_sent()

    for entry in feed.entries[:7]:

        if entry.link in sent_items:
            continue

        combined_text = entry.title + "\n" + entry.summary

        # 1차 필터
        if not contains_primary_keyword(combined_text):
            continue

        analysis = analyze_with_gemini(combined_text)

        if not analysis:
            continue

        if analysis["coin"] == "NONE":
            continue

        if analysis["importance"] >= 4:

            icon = "₿" if analysis["coin"] == "BTC" else "🐶"

            message = f"""
🚨 CRYPTO ALERT {icon}

코인: {analysis["coin"]}
중요도: {analysis["importance"]}/5

{analysis["summary_korean"]}

이유: {analysis["reason"]}

🔗 {entry.link}
"""

            send_telegram(message)
            sent_items.append(entry.link)

    save_sent(sent_items)

if __name__ == "__main__":
    main()

def send_telegram_test():
    import requests
    import os

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": "🔥 강제 테스트 메시지 - 전송 확인"
    }

    requests.post(url, data=data)

if __name__ == "__main__":
    send_telegram_test()
