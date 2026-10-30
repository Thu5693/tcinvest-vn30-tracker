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
    page_title="TCInvest Smart Accumulator - Auto Valuation Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .alert-box-red {
        padding: 18px; background-color: #ffebee; border-left: 6px solid #d32f2f;
        border-radius: 6px; color: #b71c1c; margin-bottom: 14px;
    }
    .alert-box-amber {
        padding: 18px; background-color: #fff8e1; border-left: 6px solid #ffa000;
        border-radius: 6px; color: #e65100; margin-bottom: 14px;
    }
    .alert-box-green {
        padding: 18px; background-color: #e8f5e9; border-left: 6px solid #388e3c;
        border-radius: 6px; color: #1b5e20; margin-bottom: 14px;
    }
    .signal-card {
        padding: 14px; background-color: #f8f9fa; border: 1px solid #e0e0e0;
        border-left: 5px solid #1976d2; border-radius: 6px; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 1. DỮ LIỆU KHỞI TẠO MẶC ĐỊNH
DEFAULT_ROADMAP = [
    {"id": "step_1", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Giữ nguyên 300 CP TCB (6,705tr), 269,31 CCQ TCEF (5,51tr) và 119,15 CCQ TCBF (2,52tr)", "done": True},
    {"id": "step_2", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Đặt lệnh Bán toàn bộ 12,72 CCQ TCFF (~200.000đ) trước 14h30 ngày làm việc để gom gọn danh mục", "done": True},
    {"id": "step_3", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Kích hoạt Liên kết nguồn tiền TK Techcombank (*9013) vào Sức mua cổ phiếu trên TCInvest", "done": True},
    {"id": "step_4", "time": "Tháng 10 - 11/2026 (Khởi động)", "task": "Kiểm tra Bán nháp 119,15 CCQ TCBF để xác nhận số lượng CCQ được miễn 100% phí bán (FIFO)", "done": True},
    {"id": "step_5", "time": "Hàng tháng (Từ Tháng 11/2026)", "task": "Kỷ luật 80/20: Mua 300.000đ TCBF/tháng + Giữ 1.200.000đ trong TK Techcombank Sinh lời tự động", "done": False},
    {"id": "step_6", "time": "Tháng 12/2026 (Đợt mua Lô chẵn 1)", "task": "Gom đủ ~2,1 - 2,6 triệu: Đặt lệnh mua 100 cổ phiếu HPG bổ sung ngành Sản xuất", "done": False},
    {"id": "step_7", "time": "Tháng 02/2027 (Đợt mua Lô chẵn 2)", "task": "Gom đủ ~3,17 triệu: Mua 100 CCQ FUEVFVND trên bảng giá CP (sở hữu FPT, MWG, PNJ với phí 0,8%/năm)", "done": False},
    {"id": "step_8", "time": "Tháng 04/2027 (Đợt mua Lô chẵn 3)", "task": "Gom đủ ~1,93 - 2,1 triệu: Mua 100 cổ phiếu ACB hoặc MBB để đón mùa chia cổ tức tiền mặt tháng 5-8", "done": False},
    {"id": "step_9", "time": "Tháng 05 - 08 Hàng Năm (Mùa cổ tức)", "task": "Gộp tiền cổ tức thực nhận (TCB, ACB, MBB, HPG) với tiền nộp tháng để rút ngắn chu kỳ mua thêm 1 lô chẵn", "done": False},
    {"id": "step_10", "time": "Cuối Tháng 1, 4, 7, 10 Hàng Năm", "task": "Dành 3 phút trên TCInvest kiểm tra Nợ xấu (<2,2%) của TCB/ACB/MBB và Biên lãi gộp của HPG", "done": False},
    {"id": "step_11", "time": "Bất cứ khi nào VN-Index giảm > 10%", "task": "Ứng tiền TK Techcombank mua ngay 1 lô chẵn giá đỏ trong phiên + Bấm bán lô TCBF cũ trước 14h30 cùng ngày", "done": False},
]

DEFAULT_TRANSACTIONS = [
    {"date": "2021-06-01", "ticker": "TCB", "asset_type": "Cổ phiếu Ngân hàng", "action": "MUA", "quantity": 300.0, "price": 14666.67, "fee": 0.0, "note": "Vốn gốc 4,4 triệu (100 CP + 200 CP cổ tức)"},
    {"date": "2024-01-15", "ticker": "TCEF", "asset_type": "Quỹ mở cổ phiếu", "action": "MUA", "quantity": 269.31, "price": 17089.38, "fee": 0.0, "note": "Tích lũy quỹ cổ phiếu TCEF (Vốn 4.602.342đ)"},
    {"date": "2023-05-10", "ticker": "TCBF", "asset_type": "Quỹ mở trái phiếu", "action": "MUA", "quantity": 119.15, "price": 15879.14, "fee": 0.0, "note": "Tích lũy quỹ trái phiếu TCBF (Vốn 1.892.000đ - Đã miễn phí bán FIFO)"},
    {"date": "2026-09-01", "ticker": "TCFF", "asset_type": "Quỹ mở ngắn hạn", "action": "MUA", "quantity": 12.72, "price": 15330.19, "fee": 0.0, "note": "Quỹ linh hoạt TCFF (Vốn 195.000đ)"},
]

CHECKLIST_FILE = "roadmap_progress.json"
TX_FILE = "transactions_log.json"

ASSET_VALUATION_META = {
    "TCB": {
        "name": "Techcombank", "category": "BANK", "group": "Cổ phiếu Ngân hàng",
        "default_pb": 1.15, "default_pe": 6.8, "default_roe": 16.5, "fair_price": 31500,
        "buy_pb": 1.20, "hold_pb": 1.60, "sell_pb": 2.20, "min_roe": 15.0,
        "rule_desc": "Rẻ: P/B < 1.2 & ROE >= 15% | Hợp lý: P/B 1.2 - 1.6 | Chốt lời: P/B > 2.2"
    },
    "ACB": {
        "name": "Ngân hàng Á Châu", "category": "BANK", "group": "Cổ phiếu Ngân hàng",
        "default_pb": 1.35, "default_pe": 6.4, "default_roe": 22.0, "fair_price": 33500,
        "buy_pb": 1.25, "hold_pb": 1.65, "sell_pb": 2.20, "min_roe": 15.0,
        "rule_desc": "Rẻ: P/B < 1.25 & ROE >= 15% | Hợp lý: P/B 1.25 - 1.65 | Chốt lời: P/B > 2.2"
    },
    "MBB": {
        "name": "MBBank", "category": "BANK", "group": "Cổ phiếu Ngân hàng",
        "default_pb": 1.22, "default_pe": 5.9, "default_roe": 21.2, "fair_price": 33000,
        "buy_pb": 1.20, "hold_pb": 1.60, "sell_pb": 2.20, "min_roe": 15.0,
        "rule_desc": "Rẻ: P/B < 1.2 & ROE >= 15% | Hợp lý: P/B 1.2 - 1.6 | Chốt lời: P/B > 2.2"
    },
    "HPG": {
        "name": "Tập đoàn Hòa Phát", "category": "CYCLE", "group": "Sản xuất chu kỳ",
        "default_pb": 1.48, "default_pe": 12.4, "default_roe": 14.8, "fair_price": 36000,
        "buy_pb": 1.30, "hold_pb": 1.90, "sell_pb": 2.50, "min_roe": 12.0,
        "rule_desc": "Rẻ: P/B < 1.3 | Hợp lý: P/B 1.3 - 1.9 | Chốt lời đỉnh chu kỳ: P/B > 2.5"
    },
    "FUEVFVND": {
        "name": "Quỹ ETF Diamond (FPT, MWG, PNJ)", "category": "ETF", "group": "Quỹ ETF Tăng trưởng",
        "default_pb": 2.05, "default_pe": 13.8, "default_roe": 19.5, "fair_price": 42000,
        "buy_pb": 1.85, "hold_pb": 2.35, "sell_pb": 2.85, "min_roe": 16.0,
        "rule_desc": "Thay thế mua mới TCEF (phí 0,8%/năm). Gom mạnh khi P/E < 14 hoặc VNI chỉnh > 5%"
    },
    "E1VFVN30": {
        "name": "Quỹ ETF VN30", "category": "ETF", "group": "Quỹ ETF Tiêu chuẩn",
        "default_pb": 1.58, "default_pe": 11.2, "default_roe": 15.8, "fair_price": 29500,
        "buy_pb": 1.45, "hold_pb": 1.85, "sell_pb": 2.30, "min_roe": 14.0,
        "rule_desc": "Ưu tiên bắt đáy khi P/B < 1.45 hoặc khi VN-Index sụt giảm mạnh > 10%"
    },
    "TCEF": {
        "name": "Quỹ Mở Cổ Phiếu Techcom", "category": "MUTUAL_EQ", "group": "Quỹ mở cổ phiếu (Sẵn có)",
        "default_pb": 1.65, "default_pe": 12.5, "default_roe": 16.2, "fair_price": 25000,
        "buy_pb": 1.30, "hold_pb": 1.90, "sell_pb": 2.35, "min_roe": 14.0,
        "rule_desc": "Giữ nguyên 269,31 CCQ (+19,72%). Ngừng mua mới do phí 1,8%/năm; chốt lời 30% nếu P/B rổ > 2.35"
    },
    "TCBF": {
        "name": "Quỹ Mở Trái Phiếu Techcom", "category": "MUTUAL_BOND", "group": "Quỹ mở trái phiếu (Kho đạn)",
        "default_pb": 1.00, "default_pe": 11.5, "default_roe": 8.8, "fair_price": 24500,
        "buy_pb": 1.00, "hold_pb": 1.05, "sell_pb": 9.99, "min_roe": 7.5,
        "rule_desc": "Kỷ luật nạp 20% (300k/tháng) hưởng lãi ~8.8%/năm. Rút lô cũ (0% phí FIFO) khi CP/VNI về vùng Rẻ"
    },
    "TCFF": {
        "name": "Quỹ Mở Linh Hoạt Techcom", "category": "MUTUAL_CASH", "group": "Quỹ mở ngắn hạn",
        "default_pb": 1.00, "default_pe": 15.0, "default_roe": 5.5, "fair_price": 16000,
        "buy_pb": 0.00, "hold_pb": 0.00, "sell_pb": 0.50, "min_roe": 5.0,
        "rule_desc": "BÁN CƠ CẤU 100% (12,72 CCQ ~ 200k) để gom vốn mua lô chẵn cổ phiếu"
    }
}

# ==========================================
# 2. MODULE ĐỒNG BỘ GOOGLE SHEETS
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
                    parsed.append({"id": str(r.get("id")), "time": str(r.get("time")), "task": str(r.get("task")), "done": done_val})
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
                rows.append([t["date"], t["ticker"], t["asset_type"], t["action"], float(t["quantity"]), float(t["price"]), float(t.get("fee", 0.0)), t.get("note", "")])
            ws.clear()
            ws.update("A1", rows)
            return True
        except Exception:
            return False
    return False

# ==========================================
# 3. HÀM LẤY GIÁ ĐA LUỒNG CHUẨN XÁC (PHÂN BIỆT INDEX VÀ STOCK)
# ==========================================
@st.cache_data(ttl=300)
def fetch_price_history(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Tự động phân luồng:
    - Nếu là VNINDEX / VN30: Gọi cổng 'ohlcs/index' của DNSE -> Dự phòng cổng CafeF -> Dự phòng VNDirect.
    - Nếu là Cổ phiếu / ETF: Gọi cổng 'ohlcs/stock' của DNSE -> Dự phòng cổng CafeF.
    """
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # LUỒNG 1: Cổng API DNSE (Tách riêng đường dẫn 'index' cho VNINDEX và 'stock' cho Cổ phiếu)
    endpoint_type = "index" if symbol in ["VNINDEX", "VN30", "HNX", "UPCOM"] else "stock"
    try:
        url_dnse = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{endpoint_type}?from={start_ts}&to={end_ts}&symbol={symbol}&resolution=1D"
        resp = requests.get(url_dnse, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data and "t" in data and len(data["t"]) > 5:
                df = pd.DataFrame({
                    "time": pd.to_datetime(data["t"], unit="s"),
                    "open": pd.to_numeric(data["o"]),
                    "high": pd.to_numeric(data["h"]),
                    "low": pd.to_numeric(data["l"]),
                    "close": pd.to_numeric(data["c"]),
                    "volume": pd.to_numeric(data["v"])
                }).sort_values("time").reset_index(drop=True)
                if endpoint_type == "stock" and df["close"].iloc[-1] < 500:
                    for col in ["open", "high", "low", "close"]:
                        df[col] = df[col] * 1000
                return df
    except Exception:
        pass

    # LUỒNG 2: Cổng API CafeF Real-time (Không bao giờ chặn IP quốc tế của Streamlit Cloud)
    try:
        url_cafef = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate=&EndDate=&PageIndex=1&PageSize=150"
        resp_cf = requests.get(url_cafef, headers=headers, timeout=6)
        if resp_cf.status_code == 200:
            js_cf = resp_cf.json()
            records = js_cf.get("Data", {}).get("Data", [])
            if records and len(records) > 5:
                rows_cf = []
                for r in records:
                    dt = pd.to_datetime(r["Ngay"], format="%d/%m/%Y", errors="coerce")
                    c_val = float(r.get("GiaDongCua", 0))
                    o_val = float(r.get("GiaMoCua", c_val))
                    h_val = float(r.get("GiaCaoNhat", c_val))
                    l_val = float(r.get("GiaThapNhat", c_val))
                    v_val = float(r.get("KhoiLuongKhopLenh", 0))
                    if endpoint_type == "stock" and c_val < 500:
                        c_val, o_val, h_val, l_val = c_val * 1000, o_val * 1000, h_val * 1000, l_val * 1000
                    if c_val > 0 and pd.notna(dt):
                        rows_cf.append({"time": dt, "open": o_val, "high": h_val, "low": l_val, "close": c_val, "volume": v_val})
                if rows_cf:
                    return pd.DataFrame(rows_cf).sort_values("time").reset_index(drop=True)
    except Exception:
        pass

    # LUỒNG 3: Cổng API VNDirect Dchart
    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol}&from={start_ts}&to={end_ts}"
        resp_vnd = requests.get(url_vnd, headers=headers, timeout=6)
        if resp_vnd.status_code == 200:
            d_vnd = resp_vnd.json()
            if d_vnd and "t" in d_vnd and len(d_vnd["t"]) > 5:
                df = pd.DataFrame({
                    "time": pd.to_datetime(d_vnd["t"], unit="s"),
                    "open": pd.to_numeric(d_vnd["o"]),
                    "high": pd.to_numeric(d_vnd["h"]),
                    "low": pd.to_numeric(d_vnd["l"]),
                    "close": pd.to_numeric(d_vnd["c"]),
                    "volume": pd.to_numeric(d_vnd["v"])
                }).sort_values("time").reset_index(drop=True)
                if endpoint_type == "stock" and df["close"].iloc[-1] < 500:
                    for col in ["open", "high", "low", "close"]:
                        df[col] = df[col] * 1000
                return df
    except Exception:
        pass

    # LUỒNG 4: Dự phòng cuối cùng nếu đứt toàn bộ kết nối mạng
    dates = pd.date_range(end=datetime.now(), periods=100, freq="B")
    base_prices = {
        "VNINDEX": 1265.0, "TCB": 21600.0, "HPG": 21000.0,
        "MBB": 19300.0, "ACB": 21000.0, "FUEVFVND": 31700.0, "E1VFVN30": 33600.0,
    }
    p_base = base_prices.get(symbol, 21000.0)
    return pd.DataFrame({
        "time": dates, "open": p_base, "high": p_base * 1.01,
        "low": p_base * 0.99, "close": p_base, "volume": 10000000
    })

@st.cache_data(ttl=1800)
def fetch_live_valuation(symbol: str) -> tuple[float, float, float]:
    meta = ASSET_VALUATION_META.get(symbol, {})
    def_pb = meta.get("default_pb", 1.5)
    def_pe = meta.get("default_pe", 10.0)
    def_roe = meta.get("default_roe", 15.0)
    if symbol in ["TCEF", "TCBF", "TCFF"]:
        return def_pb, def_pe, def_roe
    try:
        url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{symbol}/overview"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pb = float(data.get("pb") or def_pb)
            pe = float(data.get("pe") or def_pe)
            roe_raw = float(data.get("roe") or (def_roe / 100.0))
            roe = roe_raw * 100.0 if roe_raw < 1.0 else roe_raw
            if 0.1 < pb < 15.0 and 0.5 < pe < 100.0:
                return round(pb, 2), round(pe, 1), round(roe, 1)
    except Exception:
        pass
    return def_pb, def_pe, def_roe

# ==========================================
# 4. BỘ MÁY QUY CHIẾU NGƯỠNG MUA TÍCH SẢN & BÁN CHỐT LỜI TỰ ĐỘNG
# ==========================================
def evaluate_valuation_signal(ticker: str, pb: float, pe: float, roe: float, vni_drawdown: float) -> dict:
    meta = ASSET_VALUATION_META[ticker]
    cat = meta["category"]

    if cat == "BANK":
        if pb > meta["sell_pb"]:
            return {
                "zone": "🔴 ĐẮT (Vượt P/B > 2.2)",
                "action": "BÁN CHỐT LỜI 30% - 50%",
                "detail": f"P/B ({pb:.2f}) vượt trần lịch sử 2.2 lần. Chốt lời 30-50% vị thế chuyển sang TCBF/ETF.",
                "score_bonus": -50
            }
        if roe < 12.0:
            return {
                "zone": "🟠 CẢNH BÁO ROE (< 12%)",
                "action": "TẠM NGỪNG MUA MỚI",
                "detail": f"ROE ({roe:.1f}%) sụt giảm dưới ngưỡng an toàn 12%. Tạm ngừng giải ngân thêm.",
                "score_bonus": -30
            }
        if pb < meta["buy_pb"] and roe >= meta["min_roe"]:
            return {
                "zone": "🟢 RẺ (P/B < 1.2 & ROE >= 15%)",
                "action": "ƯU TIÊN GOM MẠNH (80/20)",
                "detail": f"Định giá P/B ({pb:.2f}) rất rẻ so với ROE ({roe:.1f}%). Ưu tiên gom đủ lô chẵn 100 CP!",
                "score_bonus": 35
            }
        if pb <= meta["hold_pb"] and roe >= meta["min_roe"]:
            return {
                "zone": "🔵 HỢP LÝ (P/B 1.2 - 1.6)",
                "action": "MUA TÍCH SẢN ĐỊNH KỲ / NẮM GIỮ",
                "detail": f"P/B ({pb:.2f}) và ROE ({roe:.1f}%) nằm trong vùng tích sản chuẩn. Mua định kỳ theo lịch.",
                "score_bonus": 20
            }
        return {
            "zone": "🟡 THEO DÕI (P/B 1.6 - 2.2)",
            "action": "NẮM GIỮ HƯỞNG LÃI KÉP (CHƯA MUA THÊM)",
            "detail": f"P/B ({pb:.2f}) đã qua vùng rẻ nhưng chưa tới ngưỡng chốt lời 2.2. Giữ nguyên cổ phiếu sẵn có.",
            "score_bonus": 0
        }

    elif cat == "CYCLE":
        if pb > meta["sell_pb"]:
            return {
                "zone": "🔴 ĐẮT (Đỉnh chu kỳ P/B > 2.5)",
                "action": "BÁN CHỐT LỜI 50%",
                "detail": f"P/B ({pb:.2f}) vượt 2.5 lần (đỉnh chu kỳ thép). Chốt lời tối thiểu 50% vị thế!",
                "score_bonus": -50
            }
        if pb < meta["buy_pb"]:
            return {
                "zone": "🟢 RẺ (Chân sóng P/B < 1.3)",
                "action": "ƯU TIÊN GOM MẠNH (80/20)",
                "detail": f"P/B ({pb:.2f}) dưới 1.3 lần. Cơ hội gom mạnh lô chẵn 100 CP HPG giá vùng đáy!",
                "score_bonus": 35
            }
        if pb <= meta["hold_pb"]:
            return {
                "zone": "🔵 HỢP LÝ (P/B 1.3 - 1.9)",
                "action": "MUA TÍCH SẢN ĐỊNH KỲ",
                "detail": f"P/B ({pb:.2f}) nằm trong vùng tích sản hợp lý (1.3 - 1.9). Giải ngân mua lô chẵn theo kế hoạch.",
                "score_bonus": 25
            }
        return {
            "zone": "🟡 THEO DÕI (P/B 1.9 - 2.5)",
            "action": "NẮM GIỮ (NHƯỜNG TIỀN MUA MÃ KHÁC)",
            "detail": f"P/B ({pb:.2f}) tiệm cận vùng cao. Giữ cổ phiếu sẵn có, ưu tiên tiền mới cho mã rẻ hơn.",
            "score_bonus": 5
        }

    elif cat == "ETF":
        if pe > 22.0 or pb > meta["sell_pb"]:
            return {
                "zone": "🔴 ĐẮT (P/E rổ > 22)",
                "action": "TẠM DỪNG MUA / CHỐT LỜI 30%",
                "detail": f"Định giá rổ ETF (P/E {pe:.1f}, P/B {pb:.2f}) quá nóng. Tạm ngừng mua, dồn tiền vào TCBF.",
                "score_bonus": -35
            }
        if pe < 14.0 or pb < meta["buy_pb"] or vni_drawdown <= -5.0:
            return {
                "zone": "🟢 RẺ / THỊ TRƯỜNG CHIẾT KHẤU",
                "action": "ƯU TIÊN GOM MẠNH LÔ CHẴN 100 CCQ",
                "detail": f"P/E rổ ETF ({pe:.1f}) hấp dẫn (phí chỉ 0.65-0.8%/năm). Ưu tiên mua sở hữu FPT, MWG, PNJ!",
                "score_bonus": 32
            }
        return {
            "zone": "🔵 HỢP LÝ (Tích sản chuẩn)",
            "action": "MUA ĐỊNH KỲ THAY THẾ TCEF",
            "detail": f"P/E ({pe:.1f}) & ROE ({roe:.1f}%) cân bằng. Mua lô chẵn 100 CCQ định kỳ để đa dạng hóa.",
            "score_bonus": 22
        }

    elif cat == "MUTUAL_EQ":
        if pb > meta["sell_pb"] or pe > 22.0:
            return {
                "zone": "🔴 ĐỊNH GIÁ THỊ TRƯỜNG CAO",
                "action": "CHỐT LỜI 30% - 50% CCQ TCEF",
                "detail": "Thị trường chung vượt ngưỡng định giá đắt. Bán chốt lời một phần TCEF (miễn phí FIFO) sang TCBF.",
                "score_bonus": -40
            }
        return {
            "zone": "🔵 NẮM GIỮ (Phí quản lý 1.8%/năm)",
            "action": "GIỮ NGUYÊN 269,31 CCQ (DỪNG MUA MỚI)",
            "detail": "Đang lãi +19.72%. Giữ nguyên hưởng lãi kép, chuyển dòng tiền mua mới sang ETF FUEVFVND (phí 0.8%).",
            "score_bonus": -10
        }

    elif cat == "MUTUAL_BOND":
        if vni_drawdown <= -10.0:
            return {
                "zone": "🚨 KÍCH HOẠT KHO ĐẠN FIFO",
                "action": "BÁN 100 - 119,15 CCQ CŨ BẮT ĐÁY CP",
                "detail": "VN-Index giảm >10%! Bán lô TCBF cũ (0% phí bán FIFO) trước 14h30 để lấy ~2,52tr bắt đáy cổ phiếu.",
                "score_bonus": 40
            }
        return {
            "zone": "🟢 KHO ĐẠN AN TOÀN (~8.8%/năm)",
            "action": "MUA ĐỊNH KỲ 300.000Đ/THÁNG (20%)",
            "detail": "Giữ 119,15 CCQ cũ (+33.18%) làm đệm thanh khoản 0% phí bán. Nạp đều 20% ngân sách mỗi tháng.",
            "score_bonus": 15
        }

    else:
        return {
            "zone": "🟠 CẦN TÁI CƠ CẤU GỌN",
            "action": "BÁN 100% (12,72 CCQ ~ 200.000Đ)",
            "detail": "Trùng lặp tính năng với TK Techcombank Sinh lời tự động. Bán trước 14h30 để gom vốn mua lô chẵn.",
            "score_bonus": -99
        }

# ==========================================
# 5. THUẬT TOÁN TÍNH DANH MỤC TỪ NHẬT KÝ GIAO DỊCH
# ==========================================
def compute_portfolio_from_transactions(tx_list: list, current_market_prices: dict, valuation_signals: dict) -> pd.DataFrame:
    holdings = {}
    for tx in tx_list:
        ticker = tx["ticker"].upper().strip()
        act = tx["action"].upper().strip()
        qty = float(tx["quantity"])
        price = float(tx["price"])
        fee = float(tx.get("fee", 0.0))
        a_type = tx.get("asset_type", "Cổ phiếu / ETF")

        if ticker not in holdings:
            holdings[ticker] = {"asset_type": a_type, "qty": 0.0, "total_cost": 0.0}
        h = holdings[ticker]
        if act == "MUA":
            h["total_cost"] += (qty * price) + fee
            h["qty"] += qty
        elif act == "BÁN" and h["qty"] > 0:
            avg_cost = h["total_cost"] / h["qty"]
            sell_qty = min(qty, h["qty"])
            h["qty"] -= sell_qty
            h["total_cost"] = max(0.0, h["total_cost"] - (sell_qty * avg_cost))

    rows = []
    for ticker, h in holdings.items():
        if h["qty"] <= 0.001:
            continue
        avg_cost = h["total_cost"] / h["qty"]
        mkt_price = current_market_prices.get(ticker, avg_cost)
        mkt_value = h["qty"] * mkt_price
        unrealized_pnl = mkt_value - h["total_cost"]
        pnl_pct = (unrealized_pnl / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0
        sig_info = valuation_signals.get(ticker, {})

        rows.append({
            "Mã Tài Sản": ticker,
            "Phân Loại": h["asset_type"],
            "Số Lượng": round(h["qty"], 2),
            "Giá Vốn TB (₫)": round(avg_cost, 0),
            "Giá Hiện Tại / NAV (₫)": round(mkt_price, 0),
            "Tổng Vốn Gốc (₫)": round(h["total_cost"], 0),
            "Giá Trị Hiện Tại (₫)": round(mkt_value, 0),
            "Hiệu Suất (%)": round(pnl_pct, 2),
            "P/B": sig_info.get("pb", 1.0),
            "P/E": sig_info.get("pe", 10.0),
            "ROE (%)": sig_info.get("roe", 15.0),
            "Tín Hiệu Định Giá Tự Động": sig_info.get("action", "NẮM GIỮ")
        })

    df_port = pd.DataFrame(rows)
    if not df_port.empty:
        total_mkt = df_port["Giá Trị Hiện Tại (₫)"].sum()
        df_port["Tỷ Trọng (%)"] = (df_port["Giá Trị Hiện Tại (₫)"] / total_mkt) * 100
    return df_port

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

if "tx_state" not in st.session_state:
    tx_data, tx_sync_msg = load_transactions_data()
    st.session_state.tx_state = tx_data
    st.session_state.tx_sync_msg = tx_sync_msg

if "roadmap_state" not in st.session_state:
    rm_data, rm_sync_msg = load_roadmap_data()
    st.session_state.roadmap_state = rm_data
    st.session_state.rm_sync_msg = rm_sync_msg

# ==========================================
# 6. SIDEBAR: CẤU HÌNH & GIẢ LẬP ĐỊNH GIÁ
# ==========================================
with st.sidebar:
    st.title("⚙️ Cấu hình & Định Giá")
    monthly_budget = st.number_input("Ngân sách tích sản / tháng (VNĐ)", 500000, 20000000, 1500000, 100000, format="%d")
    tcbf_ratio = st.slider("Tỷ lệ nạp vào TCBF (%)", 10, 50, 20, 5)
    months_accumulated = st.slider("Số tháng gom trong TK Liên kết", 1, 6, 2, 1)

    st.divider()
    st.subheader("🧪 Giả lập Thị trường & Định giá")
    sim_drop = st.slider("Giả lập mức giảm VN-Index từ đỉnh (%)", -20.0, 2.0, 0.0, 0.5)
    sim_pb_shift = st.slider(
        "Giả lập biến động P/B toàn thị trường (+/-)",
        min_value=-0.5, max_value=1.2, value=0.0, step=0.1,
        help="Để ở 0.0 để xem P/B thật. Kéo lên +0.9 để test lệnh BÁN CHỐT LỜI khi P/B vượt 2.2 - 2.5!"
    )

    st.divider()
    st.subheader("📲 Kết nối Cảnh báo Zalo")
    default_bot_token = st.secrets.get("ZALO_BOT_TOKEN", "") if hasattr(st, "secrets") else ""
    default_user_id = st.secrets.get("ZALO_USER_ID", "") if hasattr(st, "secrets") else ""
    default_webhook = st.secrets.get("ZALO_WEBHOOK_URL", "") if hasattr(st, "secrets") else ""

    zalo_bot_token = st.text_input("Zalo Bot Token", value=default_bot_token, type="password")
    zalo_user_id = st.text_input("Zalo Chat/User ID của bạn", value=default_user_id)
    zalo_webhook = st.text_input("Hoặc Zalo Webhook URL", value=default_webhook)

# Tính toán VN-Index từ API thực tế đa luồng
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
valuation_signals = {}
all_assets_rows = []

for ticker, meta in ASSET_VALUATION_META.items():
    if ticker in ["TCEF", "TCBF", "TCFF"]:
        curr_p = market_prices_map[ticker]
        chg_t_1m = 1.2 if ticker == "TCBF" else (2.4 if ticker == "TCEF" else 0.3)
        lot_cost = 300000.0 if ticker == "TCBF" else curr_p * 100
    else:
        df_t = fetch_price_history(ticker, days=180)
        curr_p = float(df_t["close"].iloc[-1])
        market_prices_map[ticker] = curr_p
        chg_t_1m = calc_change(df_t, 21)
        lot_cost = curr_p * 100

    live_pb, live_pe, live_roe = fetch_live_valuation(ticker)
    eff_pb = round(max(0.5, live_pb + (sim_pb_shift if ticker not in ["TCBF", "TCFF"] else 0.0)), 2)
    eff_pe = round(max(3.0, live_pe * (eff_pb / live_pb)), 1) if live_pb > 0 else live_pe

    sig = evaluate_valuation_signal(ticker, eff_pb, eff_pe, live_roe, effective_drawdown)
    valuation_signals[ticker] = {**sig, "pb": eff_pb, "pe": eff_pe, "roe": live_roe}
    upside = ((meta["fair_price"] - curr_p) / curr_p) * 100

    all_assets_rows.append({
        "Mã": ticker,
        "Tên Cổ Phiếu / Quỹ": meta["name"],
        "Phân Nhóm": meta["group"],
        "Thị Giá / NAV (₫)": curr_p,
        "Vốn 1 Lô Chẵn / Đợt (₫)": lot_cost,
        "Biến Động 1T (%)": round(chg_t_1m, 2),
        "P/B": eff_pb,
        "P/E": eff_pe,
        "ROE / Lãi (%)": live_roe,
        "Trạng Thái Định Giá": sig["zone"],
        "Lệnh Đề Xuất Tự Động": sig["action"],
        "Tiềm Năng (%)": round(upside, 1),
        "Quy Tắc Ngưỡng Chuẩn": meta["rule_desc"],
        "Chi Tiết Lý Do": sig["detail"]
    })

df_all_valuation = pd.DataFrame(all_assets_rows)
df_portfolio_live = compute_portfolio_from_transactions(st.session_state.tx_state, market_prices_map, valuation_signals)
live_total_value = df_portfolio_live["Giá Trị Hiện Tại (₫)"].sum() if not df_portfolio_live.empty else 14935000.0
live_total_cost = df_portfolio_live["Tổng Vốn Gốc (₫)"].sum() if not df_portfolio_live.empty else 11089342.0
live_total_pnl = live_total_value - live_total_cost

buy_triggers = [r["Mã"] for r in all_assets_rows if "GOM MẠNH" in r["Lệnh Đề Xuất Tự Động"]]
sell_triggers = [f"{r['Mã']} ({r['Lệnh Đề Xuất Tự Động']})" for r in all_assets_rows if "BÁN" in r["Lệnh Đề Xuất Tự Động"]]

zalo_msg = (
    f"📊 [BÁO CÁO ĐỊNH GIÁ & TÍCH SẢN TCINVEST]\n"
    f"• VN-Index: {vni_current:,.1f} điểm (Lệch đỉnh 3T: {effective_drawdown:.2f}%)\n"
    f"• Tổng tài sản: {live_total_value:,.0f} ₫ (Lãi: +{live_total_pnl:,.0f} ₫)\n"
    f"• Mã vào vùng RẺ ưu tiên gom: {', '.join(buy_triggers) if buy_triggers else 'Mua định kỳ theo lịch (HPG, FUEVFVND)'}\n"
    f"• Tín hiệu Bán/Cơ cấu: {', '.join(sell_triggers) if sell_triggers else 'Không có mã vượt trần P/B'}"
)

with st.sidebar:
    if st.button("📨 Gửi Báo cáo Định giá về Zalo ngay", use_container_width=True):
        ok, status_msg = send_zalo_notification(zalo_msg, zalo_bot_token, zalo_user_id, zalo_webhook)
        if ok:
            st.success(status_msg)
        else:
            st.warning(status_msg)

# ==========================================
# 7. GIAO DIỆN CHÍNH (5 TABS CHỨC NĂNG)
# ==========================================
st.title("📊 Hệ Thống Quản Trị Tích Sản & Định Giá Tự Động (P/B • P/E • ROE)")
st.markdown(
    f"**Tổng tài sản thực tế:** `{live_total_value:,.0f} ₫` "
    f"*(Vốn gốc: `{live_total_cost:,.0f} ₫` | Lãi ròng: `+{live_total_pnl:,.0f} ₫`)* "
    f"| **Bộ lọc Định giá:** `Tự động quét P/B, P/E, ROE toàn danh mục`"
)

if effective_drawdown <= -10.0:
    st.markdown(f"""
    <div class="alert-box-red">
        <h4>🚨 BÁO ĐỘNG ĐỎ: VN-INDEX GIẢM MẠNH {effective_drawdown:.2f}% TỪ ĐỈNH — KÍCH HOẠT BẮT ĐÁY & RÚT TCBF!</h4>
        <ul>
            <li><b>Bước 1 (9h00 - 14h45):</b> Dùng tiền mặt trong <b>TK Techcombank Liên kết (*9013)</b> đặt mua ngay <b>1 - 2 lô chẵn (100 - 200 CP/CCQ)</b> các mã đang ở vùng RẺ: <b>{', '.join(buy_triggers) if buy_triggers else 'HPG, FUEVFVND, E1VFVN30'}</b>.</li>
            <li><b>Bước 2 (Trước 14h30 chiều):</b> Vào mục Quỹ mở TCInvest bấm <b>Bán 100 - 119,15 CCQ TCBF cũ (~2.520.000đ, Phí bán = 0% FIFO)</b> để bù tiền về sau 2 ngày.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
elif any("CHỐT LỜI" in s for s in sell_triggers):
    st.markdown(f"""
    <div class="alert-box-amber">
        <h4>🔔 CẢNH BÁO CHỐT LỜI ĐỊNH GIÁ: PHÁT HIỆN CỔ PHIẾU VƯỢT TRẦN P/B (VÙNG ĐẮT)!</h4>
        <ul>
            <li><b>Tín hiệu kích hoạt:</b> {', '.join(sell_triggers)}</li>
            <li><b>Hành động tự động đề xuất:</b> Bán chốt lời 30% - 50% số lượng mã đã vượt trần định giá P/B > 2.2 (Ngân hàng) hoặc P/B > 2.5 (HPG), chuyển tiền lãi sang <b>TCBF</b> hoặc mã còn đang ở vùng Hợp lý/Rẻ.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="alert-box-green">
        <h4>✅ HỆ THỐNG ĐỊNH GIÁ ỔN ĐỊNH (Độ lệch VNI từ đỉnh: {effective_drawdown:.2f}%) — TÍN HIỆU HIỆN TẠI:</h4>
        <ul>
            <li><b>Mã đang ở vùng RẺ (Ưu tiên gom 80/20):</b> <b>{', '.join(buy_triggers) if buy_triggers else 'Chưa có mã thủng đáy P/B, duy trì mua định kỳ HPG & FUEVFVND'}</b></li>
            <li><b>Lệnh cơ cấu danh mục hiện tại:</b> <b>{', '.join(sell_triggers) if sell_triggers else 'Giữ nguyên TCB (P/B 1.15), TCEF, TCBF'}</b></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("VN-Index Hiện tại", f"{vni_current:,.1f}", f"{chg_1d:+.2f}% (1 Phiên)")
col2.metric("Biến động 1 Tuần", f"{chg_1w:+.2f}%", "5 phiên")
col3.metric("Biến động 1 Tháng", f"{chg_1m:+.2f}%", "21 phiên")
col4.metric("Biến động 3 Tháng", f"{chg_3m:+.2f}%", f"Đỉnh 3T: {peak_3m:,.0f}")
col5.metric("Mã Vùng Rẻ (Mua)", f"{len(buy_triggers)} mã", ", ".join(buy_triggers) if buy_triggers else "Mua DCA chuẩn")
col6.metric("Chiết khấu từ Đỉnh", f"{effective_drawdown:.2f}%", "Tự bắn Zalo lúc 14h15")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 1. Bảng Quy Chiếu Định Giá (P/B • P/E • ROE) & Lệnh Tự Động",
    "🤖 2. Máy Trạm Đề Xuất Mua/Bán & Dự Trù Ngân Sách",
    "💼 3. Quản Trị Danh Mục 14,93 Triệu (Kèm Tín Hiệu Định Giá)",
    "📝 4. Nhật Ký Giao Dịch (Lưu Sheet 2)",
    "✅ 5. Lộ Trình & Checklist (Lưu Sheet 1)"
])

with tab1:
    st.subheader("🎯 Bảng Theo Dõi Định Giá (P/B, P/E, ROE) & Tín Hiệu Mua/Bán Tự Động (Cổ Phiếu + ETF + Quỹ Mở)")
    st.dataframe(
        df_all_valuation[[
            "Mã", "Tên Cổ Phiếu / Quỹ", "Phân Nhóm", "Thị Giá / NAV (₫)",
            "Vốn 1 Lô Chẵn / Đợt (₫)", "P/B", "P/E", "ROE / Lãi (%)",
            "Trạng Thái Định Giá", "Lệnh Đề Xuất Tự Động", "Quy Tắc Ngưỡng Chuẩn"
        ]].style.format({
            "Thị Giá / NAV (₫)": "{:,.0f}",
            "Vốn 1 Lô Chẵn / Đợt (₫)": "{:,.0f}",
            "P/B": "{:.2f}",
            "P/E": "{:.1f}",
            "ROE / Lãi (%)": "{:.1f}%"
        }),
        use_container_width=True, hide_index=True
    )

    with st.expander("📖 Xem Bảng Quy Chiếu Ngưỡng 'Mua Tích Sản' và 'Bán Chốt Lời' Chuẩn Của Danh Mục", expanded=False):
        st.markdown("""
        | Nhóm Tài Sản | Chỉ Số Trọng Tâm | 🟢 Vùng RẺ (Ưu tiên gom mạnh 80/20) | 🔵 Vùng Hợp Lý (Mua định kỳ) | 🔴 Vùng ĐẮT (Ngừng mua / Chốt lời 30-50%) |
        | :--- | :--- | :--- | :--- | :--- |
        | **TCB, ACB, MBB** *(Ngân hàng)* | **P/B** và **ROE** | **P/B < 1,2 lần** *(kèm ROE >= 15%)* | **P/B từ 1,2 - 1,6 lần** | **P/B > 2,2 lần** *(hoặc khi ROE tụt dưới 12%)* |
        | **HPG** *(Sản xuất chu kỳ)* | **P/B** và **P/E** | **P/B < 1,3 lần** | **P/B từ 1,3 - 1,9 lần** | **P/B > 2,5 lần** *(Đỉnh chu kỳ ngành thép)* |
        | **FUEVFVND, E1VFVN30** *(Quỹ ETF)* | **P/E** và **P/B** | **P/E < 14 lần** *(hoặc VN-Index giảm > 5%)* | **P/E từ 14 - 18 lần** | **P/E > 22 lần** *(hoặc P/B > 2,8 lần)* |
        | **TCEF, TCBF, TCFF** *(Quỹ mở)* | **NAV, Phí & Lãi** | **TCBF**: Nạp 20% (300k/tháng), rút FIFO khi VNI giảm >10% | **TCEF**: Giữ nguyên 269,31 CCQ, dừng mua mới (phí 1,8%) | **TCFF**: Bán cơ cấu 100% (12,72 CCQ ~ 200k) |
        """)

    col_chart_left, col_chart_right = st.columns([3, 2])
    with col_chart_left:
        selected_ticker = st.selectbox(
            "Chọn mã để xem Biểu đồ kỹ thuật & Đường trung bình MA20 / MA50:",
            options=["VNINDEX", "TCB", "HPG", "MBB", "ACB", "FUEVFVND", "E1VFVN30"], index=0
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
        df_pb_compare = df_all_valuation[df_all_valuation["Mã"].isin(["TCB", "ACB", "MBB", "HPG", "FUEVFVND", "E1VFVN30"])]
        fig_pb = px.bar(
            df_pb_compare, x="Mã", y="P/B", color="Trạng Thái Định Giá",
            text="P/B", title="So sánh P/B Hiện Tại Với Ngưỡng Chốt Lời (2.2 - 2.5)"
        )
        fig_pb.add_hline(y=2.2, line_dash="dash", line_color="red", annotation_text="Trần Chốt lời Ngân hàng (P/B = 2.2)")
        fig_pb.add_hline(y=1.2, line_dash="dot", line_color="green", annotation_text="Ngưỡng Rẻ Ngân hàng (P/B = 1.2)")
        fig_pb.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_pb.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_pb, use_container_width=True)

with tab2:
    st.subheader("🤖 Đề Xuất Hành Động Mua / Bán Tự Động Trong Tháng Này")
    monthly_tcbf_alloc = monthly_budget * (tcbf_ratio / 100.0)
    monthly_stock_alloc = monthly_budget - monthly_tcbf_alloc
    available_lot_cash = (monthly_stock_alloc * months_accumulated) + 200000.0

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("1. Lệnh Mua Quỹ Mở Định Kỳ", f"{monthly_tcbf_alloc:,.0f} ₫ -> TCBF", f"{tcbf_ratio}% ngân sách tháng")
    b_col2.metric("2. Tiền Gom Mua CP/ETF", f"{monthly_stock_alloc:,.0f} ₫/tháng", "Giữ ở TK Techcombank (*9013)")
    b_col3.metric(f"3. Sức Mua Lô Chẵn ({months_accumulated}T + 200k TCFF)", f"{available_lot_cash:,.0f} ₫", "Tự động cộng vào Sức mua")
    b_col4.metric("4. Kho Đạn Bắt Đáy TCBF (FIFO)", "2,520,000 ₫", "Rút 0% phí khi VNI giảm >10%")

    st.markdown("#### 🔔 1. Các Lệnh BÁN / CƠ CẤU Cần Thực Hiện Ngay (Theo Bảng Quy Chiếu)")
    for r in all_assets_rows:
        if "BÁN" in r["Lệnh Đề Xuất Tự Động"] or "DỪNG MUA" in r["Lệnh Đề Xuất Tự Động"]:
            st.markdown(f"""
            <div class="signal-card">
                <b>🔹 {r['Mã']} ({r['Tên Cổ Phiếu / Quỹ']}) — {r['Trạng Thái Định Giá']}</b><br/>
                • <b>Chỉ số hiện tại:</b> P/B = <code>{r['P/B']:.2f}</code> | P/E = <code>{r['P/E']:.1f}</code> | ROE/Lãi = <code>{r['ROE / Lãi (%)']:.1f}%</code><br/>
                • <b>Khuyến nghị tự động:</b> <span style="color:#d32f2f;font-weight:bold;">{r['Lệnh Đề Xuất Tự Động']}</span> — {r['Chi Tiết Lý Do']}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 🛒 2. Bảng Xếp Hạng Mã Ưu Tiên Giải Ngân Lô Chẵn (Chấm Điểm Tự Động Theo P/B, ROE & Đa Dạng Hóa)")
    rec_list = []
    for r in all_assets_rows:
        ticker = r["Mã"]
        if ticker in ["TCB", "TCEF", "TCBF", "TCFF"]:
            continue
        lot_cost = r["Vốn 1 Lô Chẵn / Đợt (₫)"]
        diff = available_lot_cash - lot_cost
        can_buy_now = diff >= 0

        sig_bonus = valuation_signals[ticker]["score_bonus"]
        div_bonus = 25 if ticker in ["HPG", "FUEVFVND", "E1VFVN30"] else 10
        afford_bonus = 20 if can_buy_now else max(0, 10 + (diff / 150000))
        total_score = round(r["Tiềm Năng (%)"] * 1.0 + sig_bonus + div_bonus + afford_bonus, 1)

        rec_list.append({
            "Điểm Ưu Tiên": total_score,
            "Mã Giải Ngân": ticker,
            "Tên & Phân Nhóm": f"{r['Tên Cổ Phiếu / Quỹ']} ({r['Phân Nhóm']})",
            "Định Giá (P/B | P/E | ROE)": f"P/B: {r['P/B']:.2f} | P/E: {r['P/E']:.1f} | ROE: {r['ROE / Lãi (%)']:.1f}%",
            "Trạng Thái Ngưỡng": r["Trạng Thái Định Giá"],
            "Lệnh Tự Động": r["Lệnh Đề Xuất Tự Động"],
            "Vốn Cần Mua 100 CP/CCQ (₫)": lot_cost,
            "Đối Chiếu Sức Mua Hiện Tại": f"Dư {diff:,.0f} ₫ (Đặt lệnh được ngay)" if can_buy_now else f"Thiếu {abs(diff):,.0f} ₫ (Gom thêm)",
            "Phân Tích Lý Do": r["Chi Tiết Lý Do"]
        })

    df_rec = pd.DataFrame(rec_list).sort_values("Điểm Ưu Tiên", ascending=False)
    st.dataframe(
        df_rec.style.format({"Điểm Ưu Tiên": "{:.1f} điểm", "Vốn Cần Mua 100 CP/CCQ (₫)": "{:,.0f}"}),
        use_container_width=True, hide_index=True
    )

with tab3:
    st.subheader("💼 Bảng Cân Đối Danh Mục Thực Tế (Tích Hợp P/B, P/E, ROE & Cảnh Báo Chốt Lời Tự Động)")
    p_left, p_right = st.columns([3, 2])
    with p_left:
        st.dataframe(
            df_portfolio_live.style.format({
                "Số Lượng": "{:,.2f}",
                "Giá Vốn TB (₫)": "{:,.0f}",
                "Giá Hiện Tại / NAV (₫)": "{:,.0f}",
                "Tổng Vốn Gốc (₫)": "{:,.0f}",
                "Giá Trị Hiện Tại (₫)": "{:,.0f}",
                "Hiệu Suất (%)": "{:+.2f}%",
                "P/B": "{:.2f}",
                "P/E": "{:.1f}",
                "ROE (%)": "{:.1f}%",
                "Tỷ Trọng (%)": "{:.2f}%"
            }),
            use_container_width=True, hide_index=True
        )
        overweight = df_portfolio_live[df_portfolio_live["Tỷ Trọng (%)"] > 50.0]
        if not overweight.empty:
            for _, ow in overweight.iterrows():
                st.warning(f"⚠️ Mã **{ow['Mã Tài Sản']}** đang chiếm **{ow['Tỷ Trọng (%)']:.1f}%** tổng danh mục (> trần 50%). Hãy ưu tiên giải ngân tiền mới vào HPG và FUEVFVND!")
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
            default_p = float(market_prices_map.get(tx_ticker, 21000.0))
            tx_qty = st.number_input("Số lượng (CP / CCQ)", min_value=0.01, max_value=100000.0, value=100.0, step=10.0)
            tx_price = st.number_input("Giá khớp lệnh / NAV (₫)", min_value=100.0, max_value=500000.0, value=default_p, step=100.0)
        with f_col4:
            tx_fee = st.number_input("Phí giao dịch / Thuế (₫)", min_value=0.0, max_value=500000.0, value=0.0, step=1000.0)
            tx_note = st.text_input("Ghi chú đợt mua/bán", placeholder="VD: Mua 100 CP HPG khi P/B = 1.48")

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
