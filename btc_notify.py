import yfinance as yf
import requests
import os

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
    data = ticker.history(period="1d", interval="1m")
    if data.empty:
        return None, None, None, None
    price = data["Close"].iloc[-1]
    day_high = data["High"].iloc[-1]
    day_low = data["Low"].iloc[-1]
    return price, day_high, day_low, data

def get_highlow_3m():
    ticker = yf.Ticker("BTC-USD")
    data = ticker.history(period="3mo")
    return data["High"].max(), data["Low"].min()

def get_usd_to_thb():
    # ใช้ exchangerate.host แทน Yahoo เพื่อความเสถียร
    try:
        resp = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=THB").json()
        rate = resp["rates"]["THB"]
        return rate
    except:
        return None

def main():
    price, day_high, day_low, data = get_btc_price()
    if price is None:
        send_telegram("❗ Error: ไม่พบข้อมูลราคาของ BTC")
        return

    high_3m, low_3m = get_highlow_3m()
    rate_thb = get_usd_to_thb()
    price_thb = price * rate_thb if rate_thb else None

    # เปลี่ยนแปลง % จากแท่งก่อนหน้า
    prev_close = data["Close"].iloc[-2] if len(data) >=2 else price
    pct_change = (price - prev_close)/prev_close*100
    change_val = price - prev_close

    # ข้อความหลัก
    msg = (
        f"🔔 *Bitcoin (BTC-USD)*\n\n"
        f"💵 ราคา: *{price:,.2f}*  {change_val:+.2f} ({pct_change:+.2f}%)\n"
    )
    if price_thb:
        msg += f"({price_thb:,.2f} บาท)\n\n"
    else:
        msg += "\n"

    msg += f"📈 High: {day_high:,.2f}\n"
    msg += f"📉 Low: {day_low:,.2f}\n"
    msg += f"📊 ช่วง 3 เดือน: {high_3m:,.2f} - {low_3m:,.2f}\n"

    send_telegram(msg)

    # Volatility Alert
    if abs(pct_change) >= VOL_THRESHOLD:
        vol_msg = (
            f"⚡ *Volatility Alert — BTC-USD*\n\n"
            f"ราคาผันผวนเกิน {VOL_THRESHOLD}%\n"
            f"ราคา: {price:,.2f} ({pct_change:+.2f}%)\n\n"
            f"📈 High: {day_high:,.2f}\n"
            f"📉 Low: {day_low:,.2f}\n"
            f"📊 ช่วง 3 เดือน: {high_3m:,.2f} - {low_3m:,.2f}"
        )
        send_telegram(vol_msg)

if __name__ == "__main__":
    main()
