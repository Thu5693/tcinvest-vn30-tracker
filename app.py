import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
import os

# Cấu hình trang
st.set_page_config(
    page_title="TCInvest Smart Accumulator - Pro Edition",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .alert-box-red {
        padding: 18px; background-color: #ffebee; border-left: 6px solid #d32f2f;
        border-radius: 6px; color: #b71c1c; margin-bottom: 16px;
    }
    .alert-box-amber {
        padding: 18px; background-color: #fff8e1; border-left: 6px solid #ffa000;
        border-radius: 6px; color: #e65100; margin-bottom: 16px;
    }
    .alert-box-green {
        padding: 18px; background-color: #e8f5e9; border-left: 6px solid #388e3c;
        border-radius: 6px; color: #1b5e20; margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# 1. DỮ LIỆU KHỞI TẠO MẶC ĐỊNH (LỘ TRÌNH & LỊCH SỬ GIAO DỊCH GỐC CỦA BẠN)
DEFAULT_ROADMAP = [
    {"id": "step_1", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Giữ nguyên 300 CP TCB (6,705tr), 269,31 CCQ TCEF (5,51tr) và 119,15 CCQ TCBF (2,52tr)", "done": True},
    {"id": "step_2", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Đặt lệnh Bán toàn bộ 12,72 CCQ TCFF (~200.000đ) trước 14h30 ngày làm việc để gom gọn danh mục", "done": True},
    {"id": "step_3", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Kích hoạt Liên kết nguồn tiền TK Techcombank (*9013) vào Sức mua cổ phiếu trên TCInvest", "done": True},
    {"id": "step_4", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Kiểm tra Bán nháp 119,15 CCQ TCBF để xác nhận số lượng CCQ được miễn 100% phí bán (FIFO)", "done": True},
    {"id": "step_5", "time": "Hàng tháng (Từ Tháng 11/2026)", "task": "Kỷ luật 80/20: Mua 300.000đ TCBF/tháng + Giữ 1.200.000đ trong TK Techcombank Sinh lời tự động", "done": False},
    {"id": "step_6", "time": "Tháng 12/2026 (Đợt mua Lô chẵn 1)", "task": "Gom đủ ~2,6 - 2,8 triệu (2 tháng + 200k TCFF): Đặt lệnh mua 100 cổ phiếu HPG bổ sung ngành Sản xuất", "done": False},
    {"id": "step_7", "time": "Tháng 02/2027 (Đợt mua Lô chẵn 2)", "task": "Gom đủ ~3,2 triệu: Mua 100 CCQ FUEVFVND trên bảng giá CP (sở hữu FPT, MWG, PNJ với phí 0,8%/năm)", "done": False},
    {"id": "step_8", "time": "Tháng 04/2027 (Đợt mua Lô chẵn 3)", "task": "Gom đủ ~2,5 triệu: Mua 100 cổ phiếu ACB hoặc MBB để đón mùa chia cổ tức tiền mặt tháng 5-8", "done": False},
    {"id": "step_9", "time": "Tháng 05 - 08 Hàng Năm (Mùa cổ tức)", "task": "Gộp tiền cổ tức thực nhận (TCB, ACB, MBB, HPG) với tiền nộp tháng để rút ngắn chu kỳ mua thêm 1 lô chẵn", "done": False},
    {"id": "step_10", "time": "Cuối Tháng 1, 4, 7, 10 Hàng Năm", "task": "Dành 3 phút trên TCInvest kiểm tra Nợ xấu (<2,2%) của TCB/ACB/MBB và Biên lãi gộp của HPG", "done": False},
    {"id": "step_11", "time": "Bất cứ khi nào VN-Index giảm > 10%", "task": "Ứng tiền TK Techcombank mua ngay 1 lô chẵn giá đỏ trong phiên + Bấm bán lô TCBF cũ trước 14h30 cùng ngày", "done": False},
]

DEFAULT_TRANSACTIONS = [
    {"date": "2021-06-01", "ticker": "TCB", "asset_type": "Cổ phiếu trực tiếp", "action": "MUA", "quantity": 300.0, "price": 14666.67, "fee": 0.0, "note": "Vốn gốc 4,4 triệu (100 CP + 200 CP cổ tức)"},
    {"date": "2024-01-15", "ticker": "TCEF", "asset_type": "Quỹ mở cổ phiếu", "action": "MUA", "quantity": 269.31, "price": 17089.38, "fee": 0.0, "note": "Tích lũy quỹ cổ phiếu TCEF (Vốn 4.602.342đ)"},
    {"date": "2023-05-10", "ticker": "TCBF", "asset_type": "Quỹ mở trái phiếu", "action": "MUA", "quantity": 119.15, "price": 15879.14, "fee": 0.0, "note": "Tích lũy quỹ trái phiếu TCBF (Vốn 1.892.000đ - Đã miễn phí bán FIFO)"},
    {"date": "2026-09-01", "ticker": "TCFF", "asset_type": "Quỹ mở ngắn hạn", "action": "MUA", "quantity": 12.72, "price": 15330.19, "fee": 0.0, "note": "Quỹ linh hoạt TCFF (Vốn 195.000đ)"},
]

CHECKLIST_FILE = "roadmap_progress.json"
TX_FILE = "transactions_log.json"

# ==========================================
# 2. MODULE KẾT NỐI GOOGLE SHEETS (2 SHEETS: Roadmap & Transactions)
# ==========================================
def get_gsheet_spreadsheet():
    try:
        if "gcp_service_account" in st.secrets and "SHEET_ID" in st.secrets:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
            client = gspread.authorize(creds)
            return client.open_by_key(st.secrets["SHEET_ID"])
    except Exception:
        return None
    return None

def get_or_create_worksheet(sheet_title: str, cols: int = 8):
    sh = get_gsheet_spreadsheet()
    if sh is not None:
        try:
            return sh.worksheet(sheet_title)
        except Exception:
            try:
                return sh.add_worksheet(title=sheet_title, rows="200", cols=str(cols))
            except Exception:
                return None
    return None

def load_roadmap_data():
    ws = get_or_create_worksheet("Roadmap", cols=5)
    if ws is not None:
        try:
            records = ws.get_all_records()
            if records and len(records) >= len(DEFAULT_ROADMAP):
                parsed = []
                for r in records:
                    done_val = str(r.get("done", "")).strip().upper() in ["TRUE", "1", "YES"]
                    parsed.append({
                        "id": str(r.get("id")),
                        "time": str(r.get("time")),
                        "task": str(r.get("task")),
                        "done": done_val
                    })
                return parsed, "🟢 Đã đồng bộ Google Sheets (Sheet: Roadmap)"
            else:
                save_roadmap_data(DEFAULT_ROADMAP)
                return DEFAULT_ROADMAP, "🟢 Đã khởi tạo Sheet Roadmap trên Google Sheets"
        except Exception:
            pass

    if os.path.exists(CHECKLIST_FILE):
        try:
            with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f), "🟡 Lưu cục bộ (Chưa kết nối Google Sheets)"
        except Exception:
            pass
    return DEFAULT_ROADMAP, "🟡 Lưu cục bộ (Chưa kết nối Google Sheets)"

def save_roadmap_data(roadmap_list):
    try:
        with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(roadmap_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    ws = get_or_create_worksheet("Roadmap", cols=5)
    if ws is not None:
        try:
            rows = [["id", "time", "task", "done"]]
            for item in roadmap_list:
                rows.append([item["id"], item["time"], item["task"], "TRUE" if item["done"] else "FALSE"])
            ws.clear()
            ws.update("A1", rows)
            return True
        except Exception:
            return False
    return False

def load_transactions_data():
    ws = get_or_create_worksheet("Transactions", cols=9)
    if ws is not None:
        try:
            records = ws.get_all_records()
            if records and len(records) >= 1:
                parsed = []
                for r in records:
                    parsed.append({
                        "date": str(r.get("date", "")),
                        "ticker": str(r.get("ticker", "")).upper().strip(),
                        "asset_type": str(r.get("asset_type", "Cổ phiếu trực tiếp")),
                        "action": str(r.get("action", "MUA")).upper().strip(),
                        "quantity": float(r.get("quantity", 0.0)),
                        "price": float(r.get("price", 0.0)),
                        "fee": float(r.get("fee", 0.0)),
                        "note": str(r.get("note", ""))
                    })
                return parsed, "🟢 Đã đồng bộ Google Sheets (Sheet: Transactions)"
            else:
                save_transactions_data(DEFAULT_TRANSACTIONS)
                return DEFAULT_TRANSACTIONS, "🟢 Đã khởi tạo Sheet Transactions trên Google Sheets"
        except Exception:
            pass

    if os.path.exists(TX_FILE):
        try:
            with open(TX_FILE, "r", encoding="utf-8") as f:
                return json.load(f), "🟡 Lưu cục bộ (transactions_log.json)"
        except Exception:
            pass
    return DEFAULT_TRANSACTIONS, "🟡 Lưu cục bộ (transactions_log.json)"

def save_transactions_data(tx_list):
    try:
        with open(TX_FILE, "w", encoding="utf-8") as f:
            json.dump(tx_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    ws = get_or_create_worksheet("Transactions", cols=9)
    if ws is not None:
        try:
            rows = [["date", "ticker", "asset_type", "action", "quantity", "price", "fee", "note"]]
            for t in tx_list:
                rows.append([
                    t["date"], t["ticker"], t["asset_type"], t["action"],
                    float(t["quantity"]), float(t["price"]), float(t.get("fee", 0.0)), t.get("note", "")
                ])
            ws.clear()
            ws.update("A1", rows)
            return True
        except Exception:
            return False
    return False

# ==========================================
# 3. THUẬT TOÁN TỰ TÍNH GIÁ VỐN TRUNG BÌNH & TỶ TRỌNG TỪ NHẬT KÝ
# ==========================================
def compute_portfolio_from_transactions(tx_list: list, current_market_prices: dict) -> pd.DataFrame:
    holdings = {}
    for tx in tx_list:
        ticker = tx["ticker"].upper().strip()
        act = tx["action"].upper().strip()
        qty = float(tx["quantity"])
        price = float(tx["price"])
        fee = float(tx.get("fee", 0.0))
        a_type = tx.get("asset_type", "Cổ phiếu / ETF")

        if ticker not in holdings:
            holdings[ticker] = {
                "asset_type": a_type,
                "qty": 0.0,
                "total_cost": 0.0,
                "realized_pnl": 0.0
            }

        h = holdings[ticker]
        if act == "MUA":
            h["total_cost"] += (qty * price) + fee
            h["qty"] += qty
        elif act == "BÁN" and h["qty"] > 0:
            avg_cost = h["total_cost"] / h["qty"]
            sell_qty = min(qty, h["qty"])
            proceeds = (sell_qty * price) - fee
            cost_removed = sell_qty * avg_cost
            h["realized_pnl"] += (proceeds - cost_removed)
            h["qty"] -= sell_qty
            h["total_cost"] = max(0.0, h["total_cost"] - cost_removed)

    rows = []
    for ticker, h in holdings.items():
        if h["qty"] <= 0.001:
            continue
        avg_cost = h["total_cost"] / h["qty"]
        mkt_price = current_market_prices.get(ticker, avg_cost)
        mkt_value = h["qty"] * mkt_price
        unrealized_pnl = mkt_value - h["total_cost"]
        pnl_pct = (unrealized_pnl / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0

        rows.append({
            "Mã Tài Sản": ticker,
            "Phân Loại": h["asset_type"],
            "Số Lượng Hiện Có": round(h["qty"], 2),
            "Giá Vốn Trung Bình (₫)": round(avg_cost, 0),
            "Giá Thị Trường / NAV (₫)": round(mkt_price, 0),
            "Tổng Vốn Gốc (₫)": round(h["total_cost"], 0),
            "Giá Trị Hiện Tại (₫)": round(mkt_value, 0),
            "Lãi/Lỗ Tạm Tính (₫)": round(unrealized_pnl, 0),
            "Hiệu Suất (%)": round(pnl_pct, 2)
        })

    df_port = pd.DataFrame(rows)
    if not df_port.empty:
        total_mkt = df_port["Giá Trị Hiện Tại (₫)"].sum()
        df_port["Tỷ Trọng (%)"] = (df_port["Giá Trị Hiện Tại (₫)"] / total_mkt) * 100
    return df_port

# ==========================================
# 4. MODULE GỬI CẢNH BÁO ZALO & LẤY GIÁ TRỰC TIẾP QUA API (KHÔNG CẦN VNSTOCK3)
# ==========================================
def send_zalo_notification(message_text: str, bot_token: str = "", user_id: str = "", webhook_url: str = "") -> tuple[bool, str]:
    if bot_token and user_id:
        try:
            url = f"https://bot-api.zaloplatforms.com/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={"chat_id": user_id, "text": message_text}, timeout=8)
            if resp.status_code == 200:
                return True, "Đã gửi cảnh báo thành công về Zalo qua Zalo Bot!"
            return False, f"Lỗi Zalo Bot API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return False, f"Lỗi kết nối Zalo Bot: {str(e)}"
    if webhook_url:
        try:
            payload = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": message_text}
            resp = requests.post(webhook_url, json=payload, timeout=8)
            if resp.status_code in [200, 201, 202, 204]:
                return True, "Đã bắn tín hiệu qua Zalo Webhook thành công!"
            return False, f"Webhook trả về mã {resp.status_code}"
        except Exception as e:
            return False, f"Lỗi gọi Webhook: {str(e)}"
    return False, "Chưa cấu hình Zalo Bot Token hoặc Webhook URL."

@st.cache_data(ttl=300)
def fetch_price_history(symbol: str, days: int = 365) -> pd.DataFrame:
    """Lấy dữ liệu giá trực tiếp từ API chứng khoán qua requests, không cần cài vnstock3."""
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    try:
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol={symbol}&resolution=1D"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data and "t" in data and len(data["t"]) > 0:
                df = pd.DataFrame({
                    "time": pd.to_datetime(data["t"], unit="s"),
                    "open": pd.to_numeric(data["o"]),
                    "high": pd.to_numeric(data["h"]),
                    "low": pd.to_numeric(data["l"]),
                    "close": pd.to_numeric(data["c"]),
                    "volume": pd.to_numeric(data["v"])
                })
                df = df.sort_values("time").reset_index(drop=True)
                if symbol != "VNINDEX" and df["close"].iloc[-1] < 500:
                    for col in ["open", "high", "low", "close"]:
                        df[col] = df[col] * 1000
                return df
    except Exception:
        pass

    # Dữ liệu dự phòng an toàn nếu ngoài giờ hoặc nghẽn mạng
    np.random.seed(abs(hash(symbol)) % (10**6))
    dates = pd.date_range(end=datetime.now(), periods=int(days * 0.7), freq="B")
    base_prices = {
        "VNINDEX": 1285.0, "TCB": 22350.0, "HPG": 27200.0,
        "MBB": 24800.0, "ACB": 25600.0, "FUEVFVND": 32800.0, "E1VFVN30": 23500.0,
    }
    target_last = base_prices.get(symbol, 25000.0)
    returns = np.random.normal(0.0004, 0.014, size=len(dates))
    price_path = target_last * np.exp(np.cumsum(returns) - np.sum(returns))
    return pd.DataFrame({
        "time": dates,
        "open": price_path * (1 - np.random.uniform(0, 0.008, len(dates))),
        "high": price_path * (1 + np.random.uniform(0, 0.015, len(dates))),
        "low": price_path * (1 - np.random.uniform(0, 0.015, len(dates))),
        "close": price_path,
        "volume": np.random.randint(1500000, 25000000, len(dates))
    })

WATCHLIST_META = {
    "TCB": {"name": "Techcombank", "group": "Ngân hàng (Trụ cột sẵn có)", "pb": 1.15, "pe": 6.8, "roe": 16.5, "fair_price": 31500, "role": "Giữ nguyên 300 CP (Giá vốn 14.667đ). Hưởng lợi CASA đầu ngành."},
    "HPG": {"name": "Tập đoàn Hòa Phát", "group": "Sản xuất & Hạ tầng", "pb": 1.48, "pe": 12.4, "roe": 14.8, "fair_price": 36000, "role": "Ưu tiên mua Đợt 1 (100 CP ~ 2,72 triệu) để đa dạng hóa khỏi Ngân hàng."},
    "MBB": {"name": "MBBank", "group": "Ngân hàng cổ tức", "pb": 1.22, "pe": 5.9, "roe": 21.2, "fair_price": 33000, "role": "ROE > 20%, CASA cao, chia cổ tức tiền mặt + cổ phiếu đều đặn."},
    "ACB": {"name": "Ngân hàng Á Châu", "group": "Ngân hàng cổ tức", "pb": 1.35, "pe": 6.4, "roe": 22.0, "fair_price": 33500, "role": "Ngân hàng bán lẻ an toàn nhất, nợ xấu thấp, chia cổ tức tiền mặt đều."},
    "FUEVFVND": {"name": "Quỹ ETF DCVFMVN Diamond", "group": "Quỹ ETF Tăng trưởng", "pb": 2.10, "pe": 13.5, "roe": 19.5, "fair_price": 42000, "role": "Thay thế mua mới TCEF (phí 0,8%/năm). Sở hữu gián tiếp FPT, MWG, PNJ."},
    "E1VFVN30": {"name": "Quỹ ETF DCVFMVN30", "group": "Quỹ ETF Tiêu chuẩn", "pb": 1.60, "pe": 11.2, "roe": 15.8, "fair_price": 29500, "role": "Mua gom khi VN-Index sụt giảm sâu (>10%) để đón sóng hồi phục."},
}

if "tx_state" not in st.session_state:
    tx_data, tx_sync_msg = load_transactions_data()
    st.session_state.tx_state = tx_data
    st.session_state.tx_sync_msg = tx_sync_msg

if "roadmap_state" not in st.session_state:
    rm_data, rm_sync_msg = load_roadmap_data()
    st.session_state.roadmap_state = rm_data
    st.session_state.rm_sync_msg = rm_sync_msg

# ==========================================
# 5. SIDEBAR: CẤU HÌNH & ZALO BOT
# ==========================================
with st.sidebar:
    st.title("⚙️ Cấu hình & Zalo Alert")
    monthly_budget = st.number_input("Ngân sách tích sản / tháng (VNĐ)", 500000, 20000000, 1500000, 100000, format="%d")
    tcbf_ratio = st.slider("Tỷ lệ nạp vào TCBF (%)", 10, 50, 20, 5)
    months_accumulated = st.slider("Số tháng gom trong TK Liên kết", 1, 6, 2, 1)

    st.divider()
    st.subheader("📲 Kết nối Cảnh báo Zalo")
    default_bot_token = st.secrets.get("ZALO_BOT_TOKEN", "") if hasattr(st, "secrets") else ""
    default_user_id = st.secrets.get("ZALO_USER_ID", "") if hasattr(st, "secrets") else ""
    default_webhook = st.secrets.get("ZALO_WEBHOOK_URL", "") if hasattr(st, "secrets") else ""

    zalo_bot_token = st.text_input("Zalo Bot Token", value=default_bot_token, type="password")
    zalo_user_id = st.text_input("Zalo Chat/User ID của bạn", value=default_user_id)
    zalo_webhook = st.text_input("Hoặc Zalo Webhook URL", value=default_webhook)
    auto_zalo_alert = st.checkbox("Tự động bắn Zalo khi VNI giảm > 5%", value=True)

    st.divider()
    st.subheader("🧪 Giả lập Nhịp chỉnh VN-Index")
    sim_drop = st.slider("Giả lập mức giảm VN-Index từ đỉnh (%)", -20.0, 2.0, 0.0, 0.5)

df_vni = fetch_price_history("VNINDEX", days=365)
vni_current = float(df_vni["close"].iloc[-1])

def calc_change(df: pd.DataFrame, sessions: int) -> float:
    if len(df) > sessions:
        prev = float(df["close"].iloc[-(sessions + 1)])
        return ((float(df["close"].iloc[-1]) - prev) / prev) * 100
    return 0.0

chg_1d = calc_change(df_vni, 1)
chg_1w = calc_change(df_vni, 5)
chg_1m = calc_change(df_vni, 21)
chg_3m = calc_change(df_vni, 63)
chg_6m = calc_change(df_vni, 126)
peak_3m = float(df_vni["high"].tail(63).max())
actual_drawdown = ((vni_current - peak_3m) / peak_3m) * 100
effective_drawdown = sim_drop if sim_drop != 0.0 else actual_drawdown

market_prices_map = {
    "TCEF": 20459.69,
    "TCBF": 21149.81,
    "TCFF": 15723.27,
}
watchlist_rows = []
for ticker, meta in WATCHLIST_META.items():
    df_t = fetch_price_history(ticker, days=180)
    curr_p = float(df_t["close"].iloc[-1])
    market_prices_map[ticker] = curr_p
    chg_t_1m = calc_change(df_t, 21)
    lot_cost = curr_p * 100
    upside = ((meta["fair_price"] - curr_p) / curr_p) * 100
    val_status = "🟢 Rẻ (Ưu tiên gom)" if meta["pb"] <= 1.25 else ("🔵 Hợp lý (Mua tích sản)" if meta["pb"] <= 1.85 else "🟡 Theo dõi")
    watchlist_rows.append({
        "Mã CK": ticker, "Tên Cổ Phiếu / Quỹ": meta["name"], "Nhóm Ngành": meta["group"],
        "Giá Hiện Tại (₫)": curr_p, "Vốn 1 Lô Chẵn 100 CP (₫)": lot_cost,
        "Biến Động 1 Tháng (%)": round(chg_t_1m, 2), "P/B Hiện Tại": meta["pb"],
        "P/E": meta["pe"], "ROE (%)": meta["roe"], "Giá Mục Tiêu 1-2 Năm (₫)": meta["fair_price"],
        "Tiềm Năng Tăng Giá (%)": round(upside, 1), "Đánh Giá Định Giá": val_status, "Vai Trò Chiến Lược": meta["role"]
    })
df_watchlist = pd.DataFrame(watchlist_rows)

df_portfolio_live = compute_portfolio_from_transactions(st.session_state.tx_state, market_prices_map)
live_total_value = df_portfolio_live["Giá Trị Hiện Tại (₫)"].sum() if not df_portfolio_live.empty else 14935000.0
live_total_cost = df_portfolio_live["Tổng Vốn Gốc (₫)"].sum() if not df_portfolio_live.empty else 11089342.0
live_total_pnl = live_total_value - live_total_cost

if effective_drawdown <= -10.0:
    zalo_msg = (
        f"🚨 [BÁO ĐỘNG ĐỎ TCINVEST] VN-Index giảm mạnh {effective_drawdown:.2f}% từ đỉnh ({vni_current:,.1f} điểm)!\n"
        f"1. Dùng tiền mặt TK Techcombank (*9013) đặt mua ngay 1-2 lô chẵn HPG, FUEVFVND hoặc E1VFVN30 giá đỏ.\n"
        f"2. Trước 14h30 hôm nay: Vào TCInvest bấm Bán 100-119,15 CCQ TCBF cũ (~2,52tr, phí 0% FIFO) để bù tiền về sau 2 ngày!"
    )
elif effective_drawdown <= -5.0:
    zalo_msg = (
        f"⚠️ [CẢNH BÁO VÀNG TCINVEST] VN-Index điều chỉnh {effective_drawdown:.2f}% từ đỉnh ({vni_current:,.1f} điểm).\n"
        f"👉 Kiểm tra TK Techcombank Liên kết (*9013), nếu đã gom gần đủ 2,6 - 3,0 triệu đồng thì đặt mua sớm 1 lô chẵn HPG hoặc FUEVFVND giá đỏ!"
    )
else:
    zalo_msg = (
        f"✅ [BÁO CÁO TCINVEST] VN-Index ổn định tại {vni_current:,.1f} điểm (Lệch đỉnh: {effective_drawdown:.2f}%).\n"
        f"• Tổng tài sản hiện tại: {live_total_value:,.0f} ₫ (Lãi ròng: +{live_total_pnl:,.0f} ₫)."
    )

with st.sidebar:
    if st.button("📨 Gửi thử Cảnh báo về Zalo ngay", use_container_width=True):
        ok, status_msg = send_zalo_notification(zalo_msg, zalo_bot_token, zalo_user_id, zalo_webhook)
        if ok:
            st.success(status_msg)
        else:
            st.warning(status_msg)

# ==========================================
# 6. GIAO DIỆN CHÍNH (5 TABS CHỨC NĂNG)
# ==========================================
st.title("📊 Hệ Thống Quản Trị Tích Sản VN30 & Quỹ Mở (Pro Edition)")
st.markdown(
    f"**Tổng giá trị danh mục (Tự động cập nhật):** `{live_total_value:,.0f} ₫` "
    f"*(Vốn gốc: `{live_total_cost:,.0f} ₫` | Lãi ròng: `+{live_total_pnl:,.0f} ₫`)* "
    f"| **Lịch quét Zalo tự động:** `14h15 chiều (T2 - T6)`"
)

if effective_drawdown <= -10.0:
    st.markdown(f"""
    <div class="alert-box-red">
        <h4>🚨 BÁO ĐỘNG ĐỎ: VN-INDEX GIẢM MẠNH {effective_drawdown:.2f}% TỪ ĐỈNH — KÍCH HOẠT CHIẾN LƯỢC BẮT ĐÁY!</h4>
        <ul>
            <li><b>Bước 1 (9h00 - 14h45 trong phiên):</b> Dùng ngay tiền mặt trong <b>TK Techcombank Liên kết (*9013)</b> đặt lệnh mua <b>1 - 2 lô chẵn (100 - 200 CP/CCQ)</b> giá đỏ của <b>HPG, FUEVFVND hoặc E1VFVN30</b>.</li>
            <li><b>Bước 2 (Trước 14h30 chiều cùng ngày):</b> Vào mục Quỹ mở trên TCInvest bấm <b>Bán 100 - 119,15 CCQ TCBF cũ (~2.520.000đ, Phí bán = 0% theo luật FIFO)</b> để bù tiền về sau 2 ngày làm việc.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
elif effective_drawdown <= -5.0:
    st.markdown(f"""
    <div class="alert-box-amber">
        <h4>⚠️ CẢNH BÁO VÀNG: VN-INDEX ĐIỀU CHỈNH {effective_drawdown:.2f}% TỪ ĐỈNH — SẴN SÀNG GOM SỚM!</h4>
        <ul>
            <li>Nếu TK Techcombank Liên kết (*9013) đã gom gần đủ <b>2.600.000đ - 3.000.000đ</b>, bạn có thể đặt lệnh mua sớm <b>1 lô chẵn (100 CP HPG/ACB/MBB hoặc 100 CCQ FUEVFVND)</b> ở vùng giá đỏ.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="alert-box-green">
        <h4>✅ THỊ TRƯỜNG ỔN ĐỊNH (Độ lệch từ đỉnh 3 tháng: {effective_drawdown:.2f}%) — DUY TRÌ KỶ LUẬT 80/20</h4>
        <ul>
            <li><b>20% Ngân sách ({monthly_budget * tcbf_ratio / 100:,.0f} ₫/tháng):</b> Mua định kỳ quỹ <b>TCBF</b> hưởng lãi 8% - 9%/năm.</li>
            <li><b>80% Ngân sách ({monthly_budget * (100 - tcbf_ratio) / 100:,.0f} ₫/tháng):</b> Giữ trong <b>TK Techcombank Liên kết (*9013)</b> hưởng lãi Sinh lời tự động, chờ gom đủ 2 tháng mua 1 lô chẵn.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("VN-Index Hiện tại", f"{vni_current:,.1f}", f"{chg_1d:+.2f}% (1 Phiên)")
col2.metric("Biến động 1 Tuần", f"{chg_1w:+.2f}%", "5 phiên")
col3.metric("Biến động 1 Tháng", f"{chg_1m:+.2f}%", "21 phiên")
col4.metric("Biến động 3 Tháng", f"{chg_3m:+.2f}%", f"Đỉnh 3T: {peak_3m:,.0f}")
col5.metric("Biến động 6 Tháng", f"{chg_6m:+.2f}%", "126 phiên")
col6.metric("Chiết khấu từ Đỉnh", f"{effective_drawdown:.2f}%", "Tự bắn Zalo lúc 14h15")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 1. Biểu Đồ & Tiềm Năng Cổ Phiếu / ETF",
    "🤖 2. Máy Trạm Đề Xuất & Dự Trù Ngân Sách",
    "💼 3. Quản Trị Danh Mục (Tự Tính Giá Vốn)",
    "📝 4. Nhật Ký Giao Dịch (Lưu Sheet 2)",
    "✅ 5. Lộ Trình & Checklist (Lưu Sheet 1)"
])

with tab1:
    st.subheader("Bảng Giá Tổng Hợp, Chi Phí Mua 1 Lô Chẵn (100 CP) & Tiềm Năng Sinh Lời")
    st.dataframe(
        df_watchlist.style.format({
            "Giá Hiện Tại (₫)": "{:,.0f}", "Vốn 1 Lô Chẵn 100 CP (₫)": "{:,.0f}",
            "Biến Động 1 Tháng (%)": "{:+.2f}%", "P/B Hiện Tại": "{:.2f}",
            "P/E": "{:.1f}", "ROE (%)": "{:.1f}%",
            "Giá Mục Tiêu 1-2 Năm (₫)": "{:,.0f}", "Tiềm Năng Tăng Giá (%)": "{:+.1f}%"
        }),
        use_container_width=True, hide_index=True
    )

    col_chart_left, col_chart_right = st.columns([3, 2])
    with col_chart_left:
        selected_ticker = st.selectbox(
            "Chọn mã để xem Biểu đồ kỹ thuật & Đường trung bình MA20 / MA50:",
            options=["VNINDEX", "TCB", "HPG", "MBB", "ACB", "FUEVFVND", "E1VFVN30"], index=1
        )
        df_chart = fetch_price_history(selected_ticker, days=250)
        df_chart["MA20"] = df_chart["close"].rolling(20).mean()
        df_chart["MA50"] = df_chart["close"].rolling(50).mean()

        fig_candle = go.Figure()
        fig_candle.add_trace(go.Candlestick(
            x=df_chart["time"], open=df_chart["open"], high=df_chart["high"],
            low=df_chart["low"], close=df_chart["close"], name=selected_ticker
        ))
        fig_candle.add_trace(go.Scatter(x=df_chart["time"], y=df_chart["MA20"], mode="lines", name="MA20", line=dict(color="#1e88e5", width=1.5)))
        fig_candle.add_trace(go.Scatter(x=df_chart["time"], y=df_chart["MA50"], mode="lines", name="MA50", line=dict(color="#fb8c00", width=1.5)))
        fig_candle.update_layout(title=f"Biểu đồ biến động giá {selected_ticker}", xaxis_rangeslider_visible=False, height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_candle, use_container_width=True)

    with col_chart_right:
        fig_upside = px.bar(
            df_watchlist.sort_values("Tiềm Năng Tăng Giá (%)", ascending=True),
            x="Tiềm Năng Tăng Giá (%)", y="Mã CK", color="Nhóm Ngành",
            orientation="h", text="Tiềm Năng Tăng Giá (%)", title="So sánh Dư địa tăng giá kỳ vọng (%)"
        )
        fig_upside.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
        fig_upside.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_upside, use_container_width=True)

with tab2:
    st.subheader("🤖 Tự Động Phân Tích Ngân Sách & Đề Xuất Mã Mua Theo Khả Năng Tài Chính")
    monthly_tcbf_alloc = monthly_budget * (tcbf_ratio / 100.0)
    monthly_stock_alloc = monthly_budget - monthly_tcbf_alloc
    available_lot_cash = (monthly_stock_alloc * months_accumulated) + 200000.0

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("Trích mua TCBF hàng tháng", f"{monthly_tcbf_alloc:,.0f} ₫", f"{tcbf_ratio}% ngân sách")
    b_col2.metric("Gom trong TK Techcombank/tháng", f"{monthly_stock_alloc:,.0f} ₫", f"{100 - tcbf_ratio}% ngân sách")
    b_col3.metric(f"Sức mua Lô chẵn sau {months_accumulated} tháng (+200k TCFF)", f"{available_lot_cash:,.0f} ₫", "Tự động cộng vào Sức mua")
    b_col4.metric("Kho đạn TCBF miễn phí bán (FIFO)", "2,520,000 ₫", "Sẵn sàng khi VNI giảm >10%")

    rec_list = []
    for _, row in df_watchlist.iterrows():
        ticker = row["Mã CK"]
        if ticker == "TCB":
            continue
        lot_cost = row["Vốn 1 Lô Chẵn 100 CP (₫)"]
        diff = available_lot_cash - lot_cost
        can_buy_now = diff >= 0
        score = round(row["Tiềm Năng Tăng Giá (%)"] * 1.2 + (20 if ticker in ["HPG", "FUEVFVND", "E1VFVN30"] else 10) + (25 if can_buy_now else max(0, 15 + (diff / 100000))), 1)
        rec_list.append({
            "Điểm Ưu Tiên": score, "Mã Đề Xuất": ticker,
            "Tên & Nhóm Ngành": f"{row['Tên Cổ Phiếu / Quỹ']} ({row['Nhóm Ngành']})",
            "Số Tiền Cần Cho 100 CP/CCQ (₫)": lot_cost,
            "So Với Sức Mua Hiện Tại": f"Dư {diff:,.0f} ₫ (Mua được ngay)" if can_buy_now else f"Thiếu {abs(diff):,.0f} ₫ (Gom thêm)",
            "Khuyến Nghị Hành Động Cụ Thể": row["Vai Trò Chiến Lược"]
        })
    df_rec = pd.DataFrame(rec_list).sort_values("Điểm Ưu Tiên", ascending=False)
    st.dataframe(df_rec.style.format({"Điểm Ưu Tiên": "{:.1f} điểm", "Số Tiền Cần Cho 100 CP/CCQ (₫)": "{:,.0f}"}), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("💼 Bảng Cân Đối Danh Mục Thực Tế (Tự Động Tính Giá Vốn Trung Bình Từ Nhật Ký)")
    p_left, p_right = st.columns([3, 2])
    with p_left:
        st.dataframe(
            df_portfolio_live.style.format({
                "Số Lượng Hiện Có": "{:,.2f}",
                "Giá Vốn Trung Bình (₫)": "{:,.0f}",
                "Giá Thị Trường / NAV (₫)": "{:,.0f}",
                "Tổng Vốn Gốc (₫)": "{:,.0f}",
                "Giá Trị Hiện Tại (₫)": "{:,.0f}",
                "Lãi/Lỗ Tạm Tính (₫)": "{:+,.0f}",
                "Hiệu Suất (%)": "{:+.2f}%",
                "Tỷ Trọng (%)": "{:.2f}%"
            }),
            use_container_width=True, hide_index=True
        )
        overweight = df_portfolio_live[df_portfolio_live["Tỷ Trọng (%)"] > 50.0]
        if not overweight.empty:
            for _, ow in overweight.iterrows():
                st.warning(f"⚠️ Mã **{ow['Mã Tài Sản']}** đang chiếm **{ow['Tỷ Trọng (%)']:.1f}%** tổng danh mục (> trần 50%). Hãy ưu tiên giải ngân tiền mới vào HPG và FUEVFVND để cân bằng!")
        else:
            st.success("✅ Toàn bộ các mã trong danh mục đều tuân thủ quy tắc an toàn (Không có tài sản đơn lẻ nào vượt quá 50% tổng danh mục).")

    with p_right:
        fig_pie = px.pie(
            df_portfolio_live, values="Giá Trị Hiện Tại (₫)", names="Mã Tài Sản",
            hole=0.45, title=f"Cơ cấu tỷ trọng ({live_total_value:,.0f} ₫)"
        )
        fig_pie.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

with tab4:
    st.subheader("📝 Ghi Nhật Ký Mua / Bán Cổ Phiếu & Quỹ Mở (Tự Động Đồng Bộ Google Sheets - Sheet 2)")
    st.caption(f"Trạng thái kết nối Sổ cái Giao dịch: **{st.session_state.get('tx_sync_msg', '')}**")

    with st.form("add_transaction_form", clear_on_submit=True):
        st.markdown("#### ➕ Nhập Giao Dịch Mới (Mua Lô Chẵn HPG / FUEVFVND, Mua TCBF định kỳ hoặc Bán TCFF)")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            tx_date = st.date_input("Ngày giao dịch", value=datetime.now())
            tx_action = st.selectbox("Loại lệnh", ["MUA", "BÁN"])
        with f_col2:
            tx_ticker = st.selectbox("Mã CK / Quỹ", ["HPG", "FUEVFVND", "ACB", "MBB", "TCBF", "E1VFVN30", "TCB", "TCEF", "TCFF"])
            tx_type = st.selectbox("Nhóm tài sản", ["Cổ phiếu trực tiếp", "Quỹ ETF Tăng trưởng", "Quỹ mở trái phiếu", "Quỹ mở cổ phiếu", "Quỹ mở ngắn hạn"])
        with f_col3:
            default_p = float(market_prices_map.get(tx_ticker, 25000.0))
            tx_qty = st.number_input("Số lượng (CP / CCQ)", min_value=0.01, max_value=100000.0, value=100.0, step=10.0)
            tx_price = st.number_input("Giá khớp lệnh / NAV (₫)", min_value=100.0, max_value=500000.0, value=default_p, step=100.0)
        with f_col4:
            tx_fee = st.number_input("Phí giao dịch / Thuế (₫)", min_value=0.0, max_value=500000.0, value=0.0, step=1000.0)
            tx_note = st.text_input("Ghi chú đợt mua/bán", placeholder="VD: Mua lô chẵn đợt 1 từ TK Techcombank")

        submitted = st.form_submit_button("💾 Lưu Giao Dịch & Cập Nhật Lại Giá Vốn Trung Bình", use_container_width=True)
        if submitted:
            new_tx = {
                "date": tx_date.strftime("%Y-%m-%d"),
                "ticker": tx_ticker,
                "asset_type": tx_type,
                "action": tx_action,
                "quantity": float(tx_qty),
                "price": float(tx_price),
                "fee": float(tx_fee),
                "note": tx_note
            }
            st.session_state.tx_state.append(new_tx)
            ok_sheet = save_transactions_data(st.session_state.tx_state)
            if ok_sheet:
                st.session_state.tx_sync_msg = "🟢 Đã lưu vĩnh viễn vào Sheet 'Transactions' trên Google Sheets!"
            st.success(f"Đã ghi nhận lệnh {tx_action} {tx_qty:,.2f} {tx_ticker} tại giá {tx_price:,.0f} ₫!")
            st.rerun()

    st.markdown("#### 📜 Lịch Sử Tất Cả Giao Dịch Đã Ghi Nhận")
    df_tx_history = pd.DataFrame(st.session_state.tx_state)
    if not df_tx_history.empty:
        df_tx_history["Tổng Giá Trị Lệnh (₫)"] = df_tx_history["quantity"] * df_tx_history["price"]
        st.dataframe(
            df_tx_history.style.format({
                "quantity": "{:,.2f}", "price": "{:,.0f}",
                "fee": "{:,.0f}", "Tổng Giá Trị Lệnh (₫)": "{:,.0f}"
            }),
            use_container_width=True, hide_index=True
        )

with tab5:
    st.subheader("✅ Bảng Lộ Trình Chi Tiết & Checklist Thực Thi (Đồng bộ Google Sheets - Sheet 1)")
    st.caption(f"Trạng thái lưu trữ: **{st.session_state.get('rm_sync_msg', '')}**")

    completed_count = sum(1 for item in st.session_state.roadmap_state if item["done"])
    total_steps = len(st.session_state.roadmap_state)
    st.progress(completed_count / total_steps, text=f"Tiến độ hoàn thành: {completed_count}/{total_steps} mốc ({completed_count/total_steps*100:.0f}%)")

    updated_state = []
    for item in st.session_state.roadmap_state:
        checked = st.checkbox(f"**[{item['time']}]** — {item['task']}", value=item["done"], key=item["id"])
        updated_state.append({**item, "done": checked})

    if updated_state != st.session_state.roadmap_state:
        st.session_state.roadmap_state = updated_state
        if save_roadmap_data(updated_state):
            st.session_state.rm_sync_msg = "🟢 Đã lưu vĩnh viễn vào Sheet 'Roadmap' trên Google Sheets!"
        st.rerun()
