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
    r = requests.post(url, data=payload)
    if not r.ok:
        print("Telegram error:", r.text)


def create_message(price, change_val_24h, pct_change_24h,
                   day_high, day_low, high_3m, low_3m):

    # ---- ดึงอัตรา USD → THB จาก Yahoo Finance ----
    fx = yf.Ticker("THB=X").history(period="1d")
    if not fx.empty:
        thb_rate = fx["Close"].iloc[-1]
        btc_thb = price * thb_rate
    else:
        btc_thb = None

    # ---- ข้อความตามรูปแบบที่ต้องการ ----
    msg = (
        "🔔 *Bitcoin (BTC-USD)*\n"
        "\n"
        f"💵 ราคา:  *{price:,.2f}*\n"
        f"เปลี่ยน 24 hr. {change_val_24h:+,.2f}  ({pct_change_24h:+.2f}%)\n"
    )

    if btc_thb:
        msg += f"( {btc_thb:,.1f} บาท )\n"

    msg += (
        "\n"
        f"📈 High (24h): {day_high:,.2f}\n"
        f"📉 Low (24h): {day_low:,.2f}\n"
        "\n"
        f"📊 ช่วง 3 เดือน:\n"
        f"{high_3m:,.2f} - {low_3m:,.2f}\n"
    )

    return msg


def main():
    btc = yf.Ticker("BTC-USD")

    # ข้อมูล 24 ชม.
    data = btc.history(period="1d", interval="1h")
    if data.empty:
        print("No BTC data")
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
    high_3m = data_3m["High"].max()
    low_3m = data_3m["Low"].min()

    # -------- ส่งข้อความหลัก --------
    msg = create_message(
        price, change_val_24h, pct_change_24h,
        day_high, day_low, high_3m, low_3m
    )
    send_telegram(msg)

    # -------- ส่งแจ้งเตือนความผันผวน --------
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
