import yfinance as yf
import requests
import time
import os

# --- ตั้งค่าตัวแปร (Environment Variables) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_BTC")
RETRY_TIMEOUT = 180      
RETRY_WAIT = 5           

def fetch_with_retry(func, timeout=RETRY_TIMEOUT, wait=RETRY_WAIT):
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = func()
            if value is not None: return value
        except: pass
        time.sleep(wait)
    return None

def get_data(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    if not data.empty:
        price = data["Close"].iloc[-1]
        prev_close = ticker.info.get('regularMarketPreviousClose', price)
        change = price - prev_close
        pct = (change / prev_close) * 100
        return price, change, pct, data["Low"].iloc[-1], data["High"].iloc[-1]
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

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    # 1. ข้อมูล BTC & ช่วง 3 เดือน
    btc_data = fetch_with_retry(get_btc_data)
    if btc_data is None: return
    latest = btc_data.iloc[-1]
    prev = btc_data.iloc[-2] if len(btc_data) > 1 else latest
    price, change_24h = latest["Close"], latest["Close"] - prev["Close"]
    pct_24h = (change_24h / prev["Close"]) * 100
    
    data_3m = yf.Ticker("BTC-USD").history(period="3mo")
    high_3m, low_3m = data_3m["High"].max(), data_3m["Low"].min()

    # 2. ข้อมูลเงินบาท
    thb_rate, thb_pct = fetch_with_retry(get_thb_data)
    thb_emoji = "🔺" if thb_pct > 0 else "🔻" if thb_pct < 0 else "🔸"
    
    # 3. สินทรัพย์อื่นๆ
    gold = get_data("GC=F")
    silver = get_data("SI=F")
    nasdaq = get_data("^NDX")

    # 4. ประกอบข้อความ
    btc_emoji = "🟢" if change_24h > 0 else "🔴"
    
    message = (
        f"🔔 *Bitcoin (BTC-USD)*\n\n"
        f"💵 ราคา:  *{price:,.2f}*\n\n"
        f"{btc_emoji} เปลี่ยน 24 hr. {change_24h:+,.2f}  ({pct_24h:+.2f}%)\n"
        f"( {price*thb_rate:,.1f} บาท )\n"
        f"{thb_emoji}*{thb_rate:.2f}* THB ({thb_pct:+.2f}%)\n\n"
        f"📈 High (24h): {latest['High']:,.2f}\n"
        f"📉 Low (24h): {latest['Low']:,.2f}\n\n"
        f"📊 ช่วง 3 เดือน:\n"
        f"*{high_3m:,.2f} - {low_3m:,.2f}*\n"
        f"=======================\n"
    )

    if gold:
        p, c, pct, l, h = gold
        def to_thai_gold(world_price):
            return ((world_price * 15.244 * 0.965) / 31.1035) * thb_rate
            
        thai_gold_now = to_thai_gold(p)
        thai_gold_low = to_thai_gold(l)
        thai_gold_high = to_thai_gold(h)

        message += (
            f"👑 *GOLD*\n"
            f"*{p:,.2f}* {c:+,.2f} ({pct:+.2f}%)\n"
            f"Day's Range: {l:,.2f} - {h:,.2f}\n"
            f"🇹🇭 ทองแท่งไทย: *{thai_gold_now:,.0f}* บาท\n"
            f"ต่ำสุด {thai_gold_low:,.0f} // สูงสุด {thai_gold_high:,.0f}\n\n"
        )

    if silver:
        p, c, pct, l, h = silver
        # คำนวณ Silver 1 Kg ไทย
        # สูตร: ราคาโลก * ค่าเงินบาท * 32.1507
        silver_sell = p * thb_rate * 32.1507
        silver_buy = silver_sell * (1 - 0.013) # หักออก 1.3%

        message += (
            f"🥈 *Silver*\n"
            f"*{p:,.2f}* {c:+,.2f} ({pct:+.2f}%)\n"
            f"Day's Range: {l:,.2f} - {h:,.2f}\n"
            f"ราคาขาย 1 Kg. *{silver_sell:,.0f}* บาท\n"
            f"ราคารับซื้อ 1 Kg. *{silver_buy:,.0f}* บาท\n\n"
        )

    if nasdaq:
        p, c, pct, l, h = nasdaq
        message += (
            f"🇺🇸 *NASDAQ-100*\n"
            f"*{p:,.2f}* {c:+,.2f} ({pct:+.2f}%)\n"
            f"Day's Range: {l:,.2f} - {h:,.2f}"
        )

    send_telegram(message)

if __name__ == "__main__":
    main()
