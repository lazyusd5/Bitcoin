import yfinance as yf
import os
import requests

# Telegram token & Chat ID
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")  # ห้อง Bitcoin

# Volatility Threshold
VOL_THRESHOLD = 3  # % ราคาขยับ ≥3% แจ้งทันที

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def get_btc_price():
    ticker = yf.Ticker("BTC-USD")
    # ข้อมูล 1 วันย้อนหลัง ทุก 1 นาที สำหรับ High/Low 24h
    data_1d_1m = ticker.history(period="1d", interval="1m")
    # ข้อมูล 2 วันย้อนหลัง ทุก 1 วัน สำหรับ 24h change
    data_2d_daily = ticker.history(period="2d", interval="1d")
    if data_1d_1m.empty or data_2d_daily.empty:
        return None, None, None, None, None, None
    
    price = data_1d_1m["Close"].iloc[-1]

    # High / Low 24 ชั่วโมง
    day_high = data_1d_1m["High"].max()
    day_low = data_1d_1m["Low"].min()

    # การเปลี่ยนแปลง 24 ชั่วโมง
    prev_24h = data_2d_daily["Close"].iloc[0]
    change_val_24h = price - prev_24h
    pct_change_24h = (change_val_24h / prev_24h) * 100

    return price, day_high, day_low, change_val_24h, pct_change_24h, data_1d_1m

def get_highlow_3m():
    ticker = yf.Ticker("BTC-USD")
    data = ticker.history(period="3mo")
    return data["High"].max(), data["Low"].min()

def get_usd_to_thb():
    ticker = yf.Ticker("THB=X")
    data = ticker.history(period="1d", interval="1m")
    if data.empty:
        return None
    return data["Close"].iloc[-1]

def main():
    price, day_high, day_low, change_val_24h, pct_change_24h, data = get_btc_price()
    if price is None:
        send_telegram("❗ Error: ไม่พบข้อมูลราคาของ BTC")
        return

    high_3m, low_3m = get_highlow_3m()
    usd_thb = get_usd_to_thb()
    btc_thb = price * usd_thb if usd_thb else None

    # ข้อความหลัก
    msg = (
        f"🔔 *Bitcoin (BTC-USD)*\n\n"
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

    # Volatility Alert
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
