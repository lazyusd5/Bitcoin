import yfinance as yf
import requests
import time
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
VOL_THRESHOLD = 1      # % ราคาผันผวนเกิน
RETRY_TIMEOUT = 180    # retry 3 นาที
RETRY_WAIT = 5         # เว้น 5 วินาทีต่อครั้ง
LAST_ALERT_FILE = "last_alert.txt"

# ---------------------- Retry function ----------------------
def fetch_with_retry(func, timeout=RETRY_TIMEOUT, wait=RETRY_WAIT):
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = func()
            if value is not None:
                return value
        except:
            pass
        time.sleep(wait)
    return None

# ---------------------- BTC ----------------------
def get_btc_history():
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="1d", interval="1h")
    if data.empty:
        return None
    return data

# ---------------------- THB Rate ----------------------
def get_thb_rate():
    url = "https://api.exchangerate.host/latest?base=USD&symbols=THB"
    r = requests.get(url, timeout=5)
    return r.json()["rates"]["THB"]

# ---------------------- Telegram ----------------------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})

# ---------------------- อ่าน/เขียน last alert ----------------------
def read_last_alert():
    if os.path.exists(LAST_ALERT_FILE):
        with open(LAST_ALERT_FILE, "r") as f:
            try:
                return float(f.read().strip())
            except:
                return None
    return None

def write_last_alert(price):
    with open(LAST_ALERT_FILE, "w") as f:
        f.write(str(price))

# ---------------------- MAIN ----------------------
data = fetch_with_retry(get_btc_history)
if data is None:
    send_telegram("❌ *Bitcoin (BTC-USD) Alert*\n\nไม่สามารถดึง BTC price ได้หลัง retry 3 นาที")
    raise SystemExit()

latest = data.iloc[-1]
prev   = data.iloc[-2] if len(data) > 1 else latest

price = latest['Close']
change_val_24h = latest['Close'] - prev['Close']
pct_change_24h = (change_val_24h / prev['Close']) * 100
day_high = latest['High']
day_low  = latest['Low']

# ข้อมูล 3 เดือน
btc = yf.Ticker("BTC-USD")
data_3m = btc.history(period="3mo")
high_3m = data_3m["High"].max()
low_3m = data_3m["Low"].min()

# ---------------------- THB ----------------------
thb_rate = fetch_with_retry(get_thb_rate)
if thb_rate is None:
    send_telegram("❌ *Bitcoin (BTC-USD) Alert*\n\nไม่สามารถดึง THB rate ได้หลัง retry 3 นาที")
    raise SystemExit()
btc_thb = price * thb_rate
btc_thb_text = f"{btc_thb:,.1f} บาท"

# ---------------------- Emoji ขึ้น/ลง ----------------------
if change_val_24h > 0:
    change_emoji = "🟢"
elif change_val_24h < 0:
    change_emoji = "🔴"
else:
    change_emoji = "⚪"

# ---------------------- ข้อความหลัก ----------------------
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

# ---------------------- Volatility Alert ----------------------
if abs(pct_change_24h) >= VOL_THRESHOLD:
    last_alert = read_last_alert()
    if last_alert is None or abs(price - last_alert)/last_alert*100 >= VOL_THRESHOLD:
        vol_message = (
            f"⚡ *Volatility Alert — BTC-USD*\n\n"
            f"{change_emoji} ราคาผันผวนเกิน {VOL_THRESHOLD}% ใน 24 ชั่วโมง\n"
            f"ราคา: {price:,.2f} ({pct_change_24h:+.2f}%)\n"
            f"( {btc_thb_text} )\n\n"
            f"📈 High (24h): {day_high:,.2f}\n"
            f"📉 Low (24h): {day_low:,.2f}\n"
            f"📊 ช่วง 3 เดือน:\n"
            f"{high_3m:,.2f} - {low_3m:,.2f}"
        )
        send_telegram(vol_message)
        write_last_alert(price)
