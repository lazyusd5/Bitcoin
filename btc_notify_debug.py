import yfinance as yf
import requests
import time
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
VOL_THRESHOLD = 1
RETRY_TIMEOUT = 180
RETRY_WAIT = 5
LAST_ALERT_FILE = "last_alert.txt"
LAST_THB_FILE = "last_thb_rate.txt"

def fetch_with_retry(func, timeout=RETRY_TIMEOUT, wait=RETRY_WAIT):
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = func()
            if value is not None: return value
        except: pass
        time.sleep(wait)
    return None

def get_btc_history():
    data = yf.Ticker("BTC-USD").history(period="1d", interval="1h")
    return data if not data.empty else None

def get_thb_data():
    fx = yf.Ticker("THB=X").history(period="2d")
    if len(fx) >= 2:
        curr = fx["Close"].iloc[-1]
        prev = fx["Close"].iloc[-2]
        return curr, ((curr - prev) / prev) * 100
    return (fx["Close"].iloc[-1], 0.0) if not fx.empty else (None, None)

# --- ฟังก์ชันดึงข้อมูลทองและเงิน ---
def get_metal_data(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    if not data.empty:
        price = data["Close"].iloc[-1]
        prev_close = ticker.info.get('regularMarketPreviousClose', price)
        change = price - prev_close
        pct = (change / prev_close) * 100
        day_low = data["Low"].iloc[-1]
        day_high = data["High"].iloc[-1]
        return price, change, pct, day_low, day_high
    return None

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    # 1. BTC Data
    data = fetch_with_retry(get_btc_history)
    if data is None: return
    
    latest, prev = data.iloc[-1], data.iloc[-2] if len(data) > 1 else data.iloc[-1]
    price, change_24h, pct_24h = latest["Close"], latest["Close"] - prev["Close"], ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
    
    btc_3m = yf.Ticker("BTC-USD").history(period="3mo")
    
    # 2. THB Data
    thb_rate, thb_pct = fetch_with_retry(get_thb_data)
    thb_emoji = "🔺" if thb_pct > 0 else "🔻" if thb_pct < 0 else "🔸"
    
    # 3. Metal Data (Gold & Silver)
    gold = get_metal_data("GC=F")
    silver = get_metal_data("SI=F")

    # 4. สร้างข้อความ
    btc_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
    
    message = (
        f"🔔 *Bitcoin (BTC-USD)*\n\n"
        f"💵 ราคา: *{price:,.2f}*\n\n"
        f"{btc_emoji} เปลี่ยน 24 hr. {change_24h:+,.2f} ({pct_24h:+.2f}%)\n"
        f"( {price*thb_rate:,.1f} บาท )\n"
        f"{thb_emoji}{thb_rate:.2f} THB ({thb_pct:+.2f}%)\n\n"
        f"📈 High (24h): {latest['High']:,.2f}\n"
        f"📉 Low (24h): {latest['Low']:,.2f}\n\n"
        f"📊 ช่วง 3 เดือน: {btc_3m['High'].max():,.2f} - {btc_3m['Low'].min():,.2f}\n"
        f"=======================\n"
    )

    if gold:
        g_price, g_chg, g_pct, g_low, g_high = gold
        g_emoji = "🟢" if g_chg > 0 else "🔴"
        message += (
            f"👑 *GOLD*\n"
            f"{g_price:,.2f} {g_chg:+,.2f} ({g_pct:+.2f}%)\n"
            f"Day's Range: {g_low:,.2f} - {g_high:,.2f}\n\n"
        )

    if silver:
        s_price, s_chg, s_pct, s_low, s_high = silver
        s_emoji = "🟢" if s_chg > 0 else "🔴"
        message += (
            f"🥈 *Silver*\n"
            f"{s_price:,.2f} {s_chg:+,.2f} ({s_pct:+.2f}%)\n"
            f"Day's Range: {s_low:,.2f} - {s_high:,.2f}"
        )

    send_telegram(message)

if __name__ == "__main__":
    main()
