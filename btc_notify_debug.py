import yfinance as yf
import requests
import time
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
VOL_THRESHOLD = 1        # % ราคาผันผวนเกินที่ถือว่า alert
RETRY_TIMEOUT = 180      # retry สูงสุด 3 นาที
RETRY_WAIT = 5           # หน่วง 5 วินาทีต่อครั้ง
LAST_ALERT_FILE = "last_alert.txt"


def fetch_with_retry(func, timeout=RETRY_TIMEOUT, wait=RETRY_WAIT):
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = func()
            if value is not None:
                return value
        except Exception as e:
            # คุณอาจ print(e) ถ้าต้องการ debug
            pass
        time.sleep(wait)
    return None


def get_btc_history():
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="1d", interval="1h")
    if data.empty:
        return None
    return data


def get_usd_to_thb_rate():
    # ใช้ exchangerate.host API
    res = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=THB", timeout=10)
    res.raise_for_status()
    data = res.json()
    rate = data.get("rates", {}).get("THB")
    return rate


def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})


def read_last_alert():
    if os.path.exists(LAST_ALERT_FILE):
        try:
            with open(LAST_ALERT_FILE, "r") as f:
                return float(f.read().strip())
        except:
            return None
    return None


def write_last_alert(price):
    with open(LAST_ALERT_FILE, "w") as f:
        f.write(str(price))


# ===== MAIN =====
data = fetch_with_retry(get_btc_history)
if data is None:
    send_telegram("❌ *Bitcoin (BTC-USD) Alert*\n\nไม่สามารถดึงราคา BTC ได้ หลัง retry 3 นาที")
    raise SystemExit()

latest = data.iloc[-1]
prev   = data.iloc[-2] if len(data) > 1 else latest

price = latest["Close"]
change_val_24h = price - prev["Close"]
pct_change_24h = (change_val_24h / prev["Close"]) * 100
day_high = latest["High"]
day_low  = latest["Low"]

# ข้อมูล 3 เดือน
btc = yf.Ticker("BTC-USD")
data_3m = btc.history(period="3mo")
high_3m = data_3m["High"].max()
low_3m = data_3m["Low"].min()

# ดึงอัตรา USD → THB
thb_rate = fetch_with_retry(get_usd_to_thb_rate)
if thb_rate is None:
    send_telegram("❌ *Bitcoin (BTC-USD) Alert*\n\nไม่สามารถดึง USD→THB rate ได้ หลัง retry 3 นาที")
    raise SystemExit()

btc_thb = price * thb_rate
btc_thb_text = f"{btc_thb:,.1f} บาท"

# Emoji ขึ้น/ลง
if change_val_24h > 0:
    change_emoji = "🟢"
elif change_val_24h < 0:
    change_emoji = "🔴"
else:
    change_emoji = "⚪"

# ส่งข้อความหลัก
message = (
    f"🔔 *Bitcoin (BTC-USD)*\n\n"
    f"💵 ราคา:  *{price:,.2f}*\n\n"
    f"{change_emoji} เปลี่ยน 24 hr. {change_val_24h:+,.2f}  ({pct_change_24h:+.2f}%)\n"
    f"( {btc_thb_text} )\n\n"
    f"📈 High (24h): {day_high:,.2f}\n"
    f"📉 Low (24h): {day_low:,.2f}\n\n"
    f"📊 ช่วง 3 เดือน:\n"
    f"{high_3m:,.2f} - {low_3m:,.2f}"
)
send_telegram(message)

# ส่ง Volatility Alert ถ้าเกิน threshold และต่างจากครั้งล่าสุดพอ
if abs(pct_change_24h) >= VOL_THRESHOLD:
    last = read_last_alert()
    if last is None or abs(price - last) / last * 100 >= VOL_THRESHOLD:
        vol_msg = (
            f"⚡ *Volatility Alert — BTC-USD*\n\n"
            f"{change_emoji} ราคาผันผวนเกิน {VOL_THRESHOLD}% ใน 24 ชั่วโมง\n"
            f"ราคา: {price:,.2f} ({pct_change_24h:+.2f}%)\n"
            f"( {btc_thb_text} )\n\n"
            f"📈 High (24h): {day_high:,.2f}\n"
            f"📉 Low (24h): {day_low:,.2f}\n"
            f"📊 ช่วง 3 เดือน:\n"
            f"{high_3m:,.2f} - {low_3m:,.2f}"
        )
        send_telegram(vol_msg)
        write_last_alert(price)
