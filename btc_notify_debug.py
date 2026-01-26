import yfinance as yf
import requests
import time
import os

# --- ตั้งค่าตัวแปร ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
VOL_THRESHOLD = 1        
RETRY_TIMEOUT = 180      
RETRY_WAIT = 5           
LAST_ALERT_FILE = "last_alert.txt"
LAST_THB_FILE = "last_thb_rate.txt"

# ---------------------- ฟังก์ชันดึงข้อมูล ----------------------
def fetch_with_retry(func, timeout=RETRY_TIMEOUT, wait=RETRY_WAIT):
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = func()
            if value is not None: return value
        except: pass
        time.sleep(wait)
    return None

def get_btc_data():
    ticker = yf.Ticker("BTC-USD")
    data = ticker.history(period="1d", interval="1h")
    return data if not data.empty else None

def get_thb_data():
    fx = yf.Ticker("THB=X").history(period="2d")
    if len(fx) >= 2:
        curr = fx["Close"].iloc[-1]
        prev = fx["Close"].iloc[-2]
        return curr, ((curr - prev) / prev) * 100
    return (fx["Close"].iloc[-1], 0.0) if not fx.empty else (None, None)

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

def read_last_alert():
    if os.path.exists(LAST_ALERT_FILE):
        try:
            with open(LAST_ALERT_FILE, "r") as f: return float(f.read().strip())
        except: return None
    return None

def write_last_alert(price):
    with open(LAST_ALERT_FILE, "w") as f: f.write(str(price))

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Error: {e}")

# ---------------------- ส่วนการทำงานหลัก ----------------------
def main():
    # 1. ข้อมูล BTC
    btc_data = fetch_with_retry(get_btc_data)
    if btc_data is None: return
    
    latest = btc_data.iloc[-1]
    prev = btc_data.iloc[-2] if len(btc_data) > 1 else latest
    price = latest["Close"]
    change_24h = price - prev["Close"]
    pct_24h = (change_24h / prev["Close"]) * 100
    
    # สถิติ 3 เดือน
    data_3m = yf.Ticker("BTC-USD").history(period="3mo")
    high_3m, low_3m = data_3m["High"].max(), data_3m["Low"].min()

    # 2. ข้อมูลเงินบาท
    thb_rate, thb_pct = fetch_with_retry(get_thb_data)
    thb_emoji = "🔺" if thb_pct > 0 else "🔻" if thb_pct < 0 else "🔸"
    thb_line = f"{thb_emoji}{thb_rate:.2f} THB ({thb_pct:+.2f}%)"
    
    # 3. ข้อมูลทองและเงิน
    gold = get_metal_data("GC=F")
    silver = get_metal_data("SI=F")

    # 4. ประกอบข้อความ
    btc_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
    
    message = (
        f"🔔 *Bitcoin (BTC-USD)*\n\n"
        f"💵 ราคา:  *{price:,.2f}*\n\n"
        f"{btc_emoji} เปลี่ยน 24 hr. {change_24h:+,.2f}  ({pct_24h:+.2f}%)\n"
        f"( {price*thb_rate:,.1f} บาท )\n"
        f"{thb_line}\n\n"
        f"📈 High (24h): {latest['High']:,.2f}\n"
        f"📉 Low (24h): {latest['Low']:,.2f}\n\n"
        f"📊 ช่วง 3 เดือน:\n"
        f"*{high_3m:,.2f} - {low_3m:,.2f}*\n"
        f"=======================\n"
    )

    if gold:
        g_price, g_chg, g_pct, g_low, g_high = gold
        message += (
            f"👑 *GOLD*\n"
            f"*{g_price:,.2f}* {g_chg:+,.2f} ({g_pct:+.2f}%)\n"
            f"Day's Range: {g_low:,.2f} - {g_high:,.2f}\n\n"
        )

    if silver:
        s_price, s_chg, s_pct, s_low, s_high = silver
        message += (
            f"🥈 *Silver*\n"
            f"*{s_price:,.2f}* {s_chg:+,.2f} ({s_pct:+.2f}%)\n"
            f"Day's Range: {s_low:,.2f} - {s_high:,.2f}"
        )

    send_telegram(message)

    if abs(pct_24h) >= VOL_THRESHOLD:
        last_p = read_last_alert()
        if last_p is None or abs(price - last_p)/last_p*100 >= VOL_THRESHOLD:
            vol_msg = f"⚡ *Volatility Alert — BTC-USD*\n\n" + message.replace("🔔", "⚡")
            send_telegram(vol_msg)
            write_last_alert(price)

if __name__ == "__main__":
    main()
