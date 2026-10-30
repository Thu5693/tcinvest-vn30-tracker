import os
import requests
import pandas as pd
from datetime import datetime, timedelta

def fetch_vni_drawdown():
    """Lấy điểm số VN-Index hiện tại và tính mức sụt giảm từ đỉnh 3 tháng gần nhất."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol="VNINDEX", source="TCBS")
        df = stock.quote.history(start=start_date, end=end_date, interval="1D")
        if df is not None and not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)
            curr = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-2]) if len(df) > 1 else curr
            chg_1d = ((curr - prev) / prev) * 100
            peak_3m = float(df["high"].tail(63).max())
            drawdown = ((curr - peak_3m) / peak_3m) * 100
            return curr, chg_1d, peak_3m, drawdown
    except Exception as e:
        print(f"Lỗi lấy dữ liệu VN-Index: {e}")
    return None, 0.0, None, 0.0

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
    now_str = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M ngày %d/%m/%Y")

    if curr is None:
        send_zalo(f"ℹ️ [{now_str}] Hệ thống kiểm tra VN-Index tự động: Không lấy được dữ liệu phiên hôm nay.")
    elif drawdown <= -10.0:
        msg = (
            f"🚨 [BÁO ĐỘNG ĐỎ 14h15 - {now_str}]\n"
            f"• VN-Index: {curr:,.1f} điểm ({chg_1d:+.2f}% hôm nay)\n"
            f"• Chiết khấu từ đỉnh 3 tháng ({peak_3m:,.0f}): {drawdown:.2f}% (Vượt ngưỡng -10%!)\n\n"
            f"⚡ HÀNH ĐỘNG TRƯỚC 14h30:\n"
            f"1. Dùng tiền mặt TK Techcombank (*9013) đặt mua ngay 1-2 lô chẵn (100 CP) giá đỏ của HPG, FUEVFVND hoặc E1VFVN30 trong phiên ATC.\n"
            f"2. Trước 14h30: Vào TCInvest bấm Bán 100-119,15 CCQ TCBF cũ (0% phí bán FIFO) để bù lại tiền sau 2 ngày!"
        )
        send_zalo(msg)
    elif drawdown <= -5.0 or chg_1d <= -2.5:
        msg = (
            f"⚠️ [CẢNH BÁO VÀNG 14h15 - {now_str}]\n"
            f"• VN-Index: {curr:,.1f} điểm ({chg_1d:+.2f}% hôm nay)\n"
            f"• Chiết khấu từ đỉnh 3 tháng: {drawdown:.2f}%\n\n"
            f"👉 Nếu TK Techcombank Liên kết (*9013) đã gom đủ ~2,6 - 3,0 triệu đồng, bạn có thể đặt mua sớm 1 lô chẵn HPG hoặc FUEVFVND giá đỏ trước 14h45!"
        )
        send_zalo(msg)
    else:
        # Gửi báo cáo tóm tắt nhẹ nhàng vào chiều Thứ Sáu hàng tuần (weekday == 4)
        if (datetime.utcnow() + timedelta(hours=7)).weekday() == 4:
            msg = (
                f"✅ [TỔNG KẾT TUẦN 14h15 - {now_str}]\n"
                f"• VN-Index: {curr:,.1f} điểm ({chg_1d:+.2f}% hôm nay, lệch đỉnh {drawdown:.2f}%).\n"
                f"• Thị trường ổn định: Tiếp tục duy trì kỷ luật 80/20 (300k vào TCBF + 1,2 triệu giữ trong TK Techcombank Sinh lời tự động)."
            )
            send_zalo(msg)
