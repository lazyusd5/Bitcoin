import yfinance as yf
import os
import requests
from datetime import datetime, timedelta
import pytz
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")

VOL_THRESHOLD = 3  # % ราคาขยับ ≥3% แจ้งทันที
THAI_TZ = pytz.timezone("Asia/Bangkok")

# ไฟล์ cache สำหรับเก็บ high/low และ USD→THB
CACHE_FILE = "btc_cache.json"


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print("Error sending Telegram message:", e)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)


def get_btc_price():
    ticker = yf.Ticker("BTC-USD")
    data_1d_1m = ticker.history(period="1d", interval="1m")
    data_2d_daily = ticker.history(period="2d", interval="1d")
    if data_1d_1m.empty or data_2d_daily.empty:
        return None, None, None, None, None
    
    price = data_1d_1m["Close"].iloc[-1]
    day_high = data_1d_1m["High"].max()
    day_low = data_1d_1m["Low"].min()
    prev_24h = data_2d_daily["Close"].iloc[0]
    change_val_24h = price - prev_24h
    pct_change_24h = (change_val_24h / prev_24h) * 100

    return price, day_high, day_low, change_val_24h, pct_change_24h


def get_highlow_3m(cache):
    now = datetime.utcnow()
    # อัปเดตทุกวัน
    last_update = cache.get("highlow_3m_time")
    if not last_update or datetime.fromisoformat(last_update) < now - timedelta(days=1):
        ticker = yf.Ticker("BTC-USD")
        data = ticker.history(period="3mo")
        cache["high_3m"] = float(data["High"].max())
        cache["low_3m"] = float(data["Low"].min())
        cache["highlow_3m_time"] = now.isoformat()
        save_cache(cache)
    return cache.get("high_3m"), cache.get("low_3m")


def get_usd_to_thb(cache):
    now = datetime.utcnow()
    # อัปเดตทุก 5 นาที
    last_update = cache.get("usdthb_time")
    if not last_update or datetime.fromisoformat(last_update) < now - timedelta(minutes=5):
        ticker = yf.Ticker("THB=X")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            cache["usd_thb"] = float(data["Close"].iloc[-1])
            cache["usdthb_time"] = now.isoformat()
            save_cache(cache)
    return cache.get("usd_thb")


def main():
    cache = load_cache()
    price, day_high, day_low, change_val_24h, pct_change_24h = get_btc_price()
    if price is None:
        send_telegram("❗ Error: ไม่พบข้อมูลราคาของ BTC")
        return

    high_3m, low_3m = get_highlow_3m(cache)
    usd_thb = get_usd_to_thb(cache)
    btc_thb = price * usd_thb if usd_thb else None

    now = datetime.now(THAI_TZ)
    msg = (
        f"🔔 *Bitcoin (BTC-USD)*\n"
        f"🕒 เวลาไทย: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"💵 ราคา: *{price:,.2f}*\n"
        f"เปลี่ยน 24 hr. {change_val_24h:+,.2f} ({pct_change_24h:+.2f}%)\n"
    )
    if btc_thb:
        msg += f"({btc_thb:,.2f} บาท)\n\n"
    else:
        msg += "\n"

    msg += f"📈 High (24h): {day_high:,.2f}\n"
    msg += f"📉 Low (24h): {day_low:,.2f}\n"
    msg += f"📊 ช่วง 3 เดือน: {high_3m:,.2f} - {low_3m:,.2f}\n"

    send_telegram(msg)

    if abs(pct_change_24h) >= VOL_THRESHOLD:
        vol_msg = (
            f"⚡ *Volatility Alert — BTC-USD*\n\n"
            f"ราคาผันผวนเกิน {VOL_THRESHOLD}% ใน 24 ชั่วโมง\n"
            f"ราคา: {price:,.2f} ({pct_change_24h:+.2f}%)\n\n"
            f"📈 High (24h): {day_high:,.2f}\n"
            f"📉 Low (24h): {day_low:,.2f}\n"
            f"📊 ช่วง 3 เดือน: {high_3m:,.2f} - {low_3m:,.2f}"
        )
        send_telegram(vol_msg)


if __name__ == "__main__":
    main()
