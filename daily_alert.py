import os
import requests
import pandas as pd
from datetime import datetime, timedelta

DEFAULT_META = {
    "TCB": {"cat": "BANK", "pb": 1.15, "pe": 6.8, "roe": 16.5, "buy_pb": 1.2, "sell_pb": 2.2},
    "ACB": {"cat": "BANK", "pb": 1.35, "pe": 6.4, "roe": 22.0, "buy_pb": 1.25, "sell_pb": 2.2},
    "MBB": {"cat": "BANK", "pb": 1.22, "pe": 5.9, "roe": 21.2, "buy_pb": 1.2, "sell_pb": 2.2},
    "HPG": {"cat": "CYCLE", "pb": 1.48, "pe": 12.4, "roe": 14.8, "buy_pb": 1.3, "sell_pb": 2.5},
    "FUEVFVND": {"cat": "ETF", "pb": 2.05, "pe": 13.8, "roe": 19.5, "buy_pb": 1.85, "sell_pb": 2.85},
    "E1VFVN30": {"cat": "ETF", "pb": 1.58, "pe": 11.2, "roe": 15.8, "buy_pb": 1.45, "sell_pb": 2.30},
}

def fetch_vni_drawdown():
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=120)).timestamp())
    try:
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol=VNINDEX&resolution=1D"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and "t" in data and len(data["t"]) > 0:
                df = pd.DataFrame({
                    "time": pd.to_datetime(data["t"], unit="s"),
                    "high": pd.to_numeric(data["h"]),
                    "close": pd.to_numeric(data["c"])
                }).sort_values("time").reset_index(drop=True)
                curr = float(df["close"].iloc[-1])
                prev = float(df["close"].iloc[-2]) if len(df) > 1 else curr
                chg_1d = ((curr - prev) / prev) * 100
                peak_3m = float(df["high"].tail(63).max())
                drawdown = ((curr - peak_3m) / peak_3m) * 100
                return curr, chg_1d, peak_3m, drawdown
    except Exception as e:
        print(f"Lỗi lấy dữ liệu VN-Index: {e}")
    return None, 0.0, None, 0.0

def scan_valuation_triggers():
    cheap_list = []
    take_profit_list = []
    for sym, m in DEFAULT_META.items():
        pb, pe, roe = m["pb"], m["pe"], m["roe"]
        try:
            url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{sym}/overview"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                pb = float(d.get("pb") or pb)
                pe = float(d.get("pe") or pe)
                r_raw = float(d.get("roe") or (roe / 100.0))
                roe = r_raw * 100.0 if r_raw < 1.0 else r_raw
        except Exception:
            pass

        if pb <= m["buy_pb"] and roe >= 12.0:
            cheap_list.append(f"{sym} (P/B={pb:.2f}, ROE={roe:.1f}%)")
        elif pb >= m["sell_pb"]:
            take_profit_list.append(f"{sym} (P/B={pb:.2f} vượt trần {m['sell_pb']})")
    return cheap_list, take_profit_list

def send_zalo(message: str):
    bot_token = os.environ.get("ZALO_BOT_TOKEN", "")
    user_id = os.environ.get("ZALO_USER_ID", "")
    webhook_url = os.environ.get("ZALO_WEBHOOK_URL", "")

    if bot_token and user_id:
        url = f"https://bot-api.zaloplatforms.com/bot{bot_token}/sendMessage"
        resp = requests.post(url, json={"chat_id": user_id, "text": message}, timeout=10)
        print("Zalo Bot status:", resp.status_code, resp.text)
    elif webhook_url:
        resp = requests.post(webhook_url, json={"message": message, "time": str(datetime.now())}, timeout=10)
        print("Webhook status:", resp.status_code)
    else:
        print("Chưa cấu hình biến môi trường ZALO_BOT_TOKEN hoặc ZALO_WEBHOOK_URL.")

if __name__ == "__main__":
    curr, chg_1d, peak_3m, drawdown = fetch_vni_drawdown()
    cheap_list, take_profit_list = scan_valuation_triggers()
    now_str = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M ngày %d/%m/%Y")

    if curr is None:
        send_zalo(f"ℹ️ [{now_str}] Hệ thống kiểm tra tự động: Không lấy được dữ liệu phiên hôm nay.")
    elif drawdown <= -10.0 or take_profit_list or cheap_list:
        msg = (
            f"🔔 [TÍN HIỆU ĐỊNH GIÁ & THỊ TRƯỜNG 14h15 - {now_str}]\n"
            f"• VN-Index: {curr:,.1f} điểm ({chg_1d:+.2f}%, lệch đỉnh 3T: {drawdown:.2f}%)\n"
            f"• 🟢 Mã vào vùng RẺ (Ưu tiên gom 80/20): {', '.join(cheap_list) if cheap_list else 'Chưa có'}\n"
            f"• 🔴 Mã chạm trần CHỐT LỜI (30-50%): {', '.join(take_profit_list) if take_profit_list else 'Không có'}\n\n"
            f"👉 Nếu VNI giảm >10%, hãy ứng tiền TK Techcombank (*9013) mua ngay lô chẵn giá đỏ và bấm Bán 100 CCQ TCBF cũ (0% phí FIFO) trước 14h30!"
        )
        send_zalo(msg)
    elif (datetime.utcnow() + timedelta(hours=7)).weekday() == 4:
        msg = (
            f"✅ [TỔNG KẾT ĐỊNH GIÁ TUẦN 14h15 - {now_str}]\n"
            f"• VN-Index: {curr:,.1f} điểm ({chg_1d:+.2f}%, lệch đỉnh: {drawdown:.2f}%).\n"
            f"• Toàn bộ P/B, P/E, ROE danh mục trong vùng ổn định. Duy trì nạp 300k vào TCBF + 1,2tr giữ ở TK Techcombank Sinh lời tự động."
        )
        send_zalo(msg)
