import os
import requests
import yfinance as yf

# ------------------------- CONFIG -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
VOL_THRESHOLD = 3  # % ราคาผันผวนเกิน

# ------------------------- FUNCTIONS -------------------------
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    if not response.ok:
        print("Telegram error:", response.text)

def main():
    # ดึงข้อมูล BTC-USD
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="1d", interval="1h")  # ข้อมูล 1 วัน / 1 ชั่วโมง
    if data.empty:
        print("No data fetched")
        return

    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest

    price = latest['Close']
    change_val_24h = latest['Close'] - prev['Close']
    pct_change_24h = (change_val_24h / prev['Close']) * 100
    day_high = latest['High']
    day_low = latest['Low']

    # ข้อมูล 3 เดือน
    data_3m = btc.history(period="3mo")
    high_3m = data_3m['High'].max()
    low_3m = data_3m['Low'].min()

    # แปลงเป็น THB (ไม่จำเป็น ถ้าไม่มี API ให้ดึงอัตราแลกเปลี่ยน)
    btc_thb = None

    # ข้อความหลัก
    msg = (
        f"🔔 *Bitcoin (BTC-USD)*\n"
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

    # แจ้งเตือน Volatility
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
