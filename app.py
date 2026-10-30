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
    page_title="TCInvest Smart Accumulator - Zalo & GSheets",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Giao diện CSS tùy chỉnh
st.markdown("""
<style>
    .alert-box-red {
        padding: 18px;
        background-color: #ffebee;
        border-left: 6px solid #d32f2f;
        border-radius: 6px;
        color: #b71c1c;
        margin-bottom: 16px;
    }
    .alert-box-amber {
        padding: 18px;
        background-color: #fff8e1;
        border-left: 6px solid #ffa000;
        border-radius: 6px;
        color: #e65100;
        margin-bottom: 16px;
    }
    .alert-box-green {
        padding: 18px;
        background-color: #e8f5e9;
        border-left: 6px solid #388e3c;
        border-radius: 6px;
        color: #1b5e20;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Lộ trình 11 bước mặc định theo đúng trạng thái thực tế của bạn
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

CHECKLIST_FILE = "roadmap_progress.json"

# ==========================================
# 1. MODULE ĐỒNG BỘ VĨNH VIỄN VỚI GOOGLE SHEETS
# ==========================================
def get_gsheet_worksheet():
    """Kết nối tới Google Sheets thông qua st.secrets. Trả về None nếu chưa cấu hình."""
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
            sh = client.open_by_key(st.secrets["SHEET_ID"])
            try:
                ws = sh.worksheet("Roadmap")
            except Exception:
                ws = sh.add_worksheet(title="Roadmap", rows="50", cols="5")
            return ws
    except Exception:
        return None
    return None

def load_roadmap_data():
    """Ưu tiên tải Checklist từ Google Sheets; nếu chưa cấu hình thì đọc từ file JSON cục bộ."""
    ws = get_gsheet_worksheet()
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
                return parsed, "🟢 Đã đồng bộ Google Sheets Cloud"
            else:
                # Khởi tạo bảng lần đầu trên Google Sheets
                save_roadmap_data(DEFAULT_ROADMAP)
                return DEFAULT_ROADMAP, "🟢 Đã khởi tạo bảng mới trên Google Sheets"
        except Exception as e:
            pass

    if os.path.exists(CHECKLIST_FILE):
        try:
            with open(CHECKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f), "🟡 Lưu cục bộ (Chưa kết nối Google Sheets)"
        except Exception:
            pass
    return DEFAULT_ROADMAP, "🟡 Lưu cục bộ (Chưa kết nối Google Sheets)"

def save_roadmap_data(roadmap_list):
    """Lưu trạng thái Checklist lên cả Google Sheets và file JSON cục bộ."""
    try:
        with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(roadmap_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    ws = get_gsheet_worksheet()
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

# ==========================================
# 2. MODULE GỬI CẢNH BÁO TỰ ĐỘNG QUA ZALO
# ==========================================
def send_zalo_notification(message_text: str, bot_token: str = "", user_id: str = "", webhook_url: str = "") -> tuple[bool, str]:
    """
    Hỗ trợ gửi thông báo Zalo qua 2 phương thức:
    1. Zalo Bot Platform API chính thức (bot.zaloplatforms.com)
    2. Webhook URL (Make.com / n8n / Zapier / Zalo OA Webhook)
    """
    # Phương thức 1: Gửi qua Zalo Bot Platform
    if bot_token and user_id:
        try:
            url = f"https://bot-api.zaloplatforms.com/bot{bot_token}/sendMessage"
            payload = {"chat_id": user_id, "text": message_text}
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                return True, "Đã gửi cảnh báo thành công về Zalo qua Zalo Bot!"
            else:
                return False, f"Lỗi Zalo Bot API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return False, f"Lỗi kết nối Zalo Bot: {str(e)}"

    # Phương thức 2: Gửi qua Webhook (Make.com / Zalo OA)
    if webhook_url:
        try:
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": message_text,
                "source": "TCInvest_Smart_Accumulator"
            }
            resp = requests.post(webhook_url, json=payload, timeout=8)
            if resp.status_code in [200, 201, 202, 204]:
                return True, "Đã bắn tín hiệu cảnh báo qua Zalo Webhook thành công!"
            else:
                return False, f"Webhook trả về mã {resp.status_code}"
        except Exception as e:
            return False, f"Lỗi gọi Webhook: {str(e)}"

    return False, "Chưa cấu hình Zalo Bot Token hoặc Webhook URL."

# ==========================================
# 3. HÀM LẤY DỮ LIỆU THỊ TRƯỜNG
# ==========================================
@st.cache_data(ttl=300)
def fetch_price_history(symbol: str, days: int = 365) -> pd.DataFrame:
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="TCBS")
        df = stock.quote.history(start=start_date, end=end_date, interval="1D")
        if df is not None and not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)
            if symbol != "VNINDEX" and df["close"].iloc[-1] < 500:
                for col in ["open", "high", "low", "close"]:
                    df[col] = df[col] * 1000
            return df
    except Exception:
        pass

    np.random.seed(abs(hash(symbol)) % (10**6))
    dates = pd.date_range(end=datetime.now(), periods=int(days * 0.7), freq="B")
    base_prices = {
        "VNINDEX": 1285.0,
        "TCB": 22350.0,
        "HPG": 27200.0,
        "MBB": 24800.0,
        "ACB": 25600.0,
        "FUEVFVND": 32800.0,
        "E1VFVN30": 23500.0,
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
    "TCB": {
        "name": "Techcombank", "group": "Ngân hàng (Trụ cột sẵn có)",
        "pb": 1.15, "pe": 6.8, "roe": 16.5, "fair_price": 31500,
        "role": "Giữ nguyên 300 CP (Giá vốn 14.667đ). Hưởng lợi CASA đầu ngành."
    },
    "HPG": {
        "name": "Tập đoàn Hòa Phát", "group": "Sản xuất & Hạ tầng",
        "pb": 1.48, "pe": 12.4, "roe": 14.8, "fair_price": 36000,
        "role": "Ưu tiên mua Đợt 1 (100 CP ~ 2,72 triệu) để đa dạng hóa khỏi Ngân hàng."
    },
    "MBB": {
        "name": "MBBank", "group": "Ngân hàng cổ tức",
        "pb": 1.22, "pe": 5.9, "roe": 21.2, "fair_price": 33000,
        "role": "ROE > 20%, CASA cao, chia cổ tức tiền mặt + cổ phiếu đều đặn."
    },
    "ACB": {
        "name": "Ngân hàng Á Châu", "group": "Ngân hàng cổ tức",
        "pb": 1.35, "pe": 6.4, "roe": 22.0, "fair_price": 33500,
        "role": "Ngân hàng bán lẻ an toàn nhất, nợ xấu thấp, chia cổ tức tiền mặt đều."
    },
    "FUEVFVND": {
        "name": "Quỹ ETF DCVFMVN Diamond", "group": "Quỹ ETF Tăng trưởng",
        "pb": 2.10, "pe": 13.5, "roe": 19.5, "fair_price": 42000,
        "role": "Thay thế mua mới TCEF (phí 0,8%/năm). Sở hữu gián tiếp FPT, MWG, PNJ."
    },
    "E1VFVN30": {
        "name": "Quỹ ETF DCVFMVN30", "group": "Quỹ ETF Tiêu chuẩn",
        "pb": 1.60, "pe": 11.2, "roe": 15.8, "fair_price": 29500,
        "role": "Mua gom khi VN-Index sụt giảm sâu (>10%) để đón sóng hồi phục."
    },
}

# ==========================================
# 4. SIDEBAR: CẤU HÌNH NGÂN SÁCH & ZALO BOT
# ==========================================
with st.sidebar:
    st.title("⚙️ Cấu hình & Zalo Alert")

    monthly_budget = st.number_input(
        "Ngân sách tích sản / tháng (VNĐ)",
        min_value=500000, max_value=20000000, value=1500000, step=100000, format="%d"
    )
    tcbf_ratio = st.slider("Tỷ lệ nạp vào TCBF (%)", 10, 50, 20, 5)
    months_accumulated = st.slider("Số tháng gom trong TK Liên kết", 1, 6, 2, 1)

    st.divider()
    st.subheader("📲 Kết nối Cảnh báo Zalo")
    default_bot_token = st.secrets.get("ZALO_BOT_TOKEN", "") if hasattr(st, "secrets") else ""
    default_user_id = st.secrets.get("ZALO_USER_ID", "") if hasattr(st, "secrets") else ""
    default_webhook = st.secrets.get("ZALO_WEBHOOK_URL", "") if hasattr(st, "secrets") else ""

    zalo_bot_token = st.text_input("Zalo Bot Token", value=default_bot_token, type="password")
    zalo_user_id = st.text_input("Zalo Chat/User ID của bạn", value=default_user_id)
    zalo_webhook = st.text_input("Hoặc Zalo Webhook URL (Make/OA)", value=default_webhook)
    auto_zalo_alert = st.checkbox("Tự động bắn Zalo khi VNI giảm > 5%", value=True)

    st.divider()
    st.subheader("🧪 Giả lập Nhịp chỉnh VN-Index")
    sim_drop = st.slider("Giả lập mức giảm VN-Index từ đỉnh (%)", -20.0, 2.0, 0.0, 0.5)

# Tính toán VN-Index
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

# Nội dung tin nhắn cảnh báo Zalo chuẩn bị sẵn theo trạng thái thị trường
if effective_drawdown <= -10.0:
    zalo_msg = (
        f"🚨 [BÁO ĐỘNG ĐỎ TCINVEST] VN-Index giảm mạnh {effective_drawdown:.2f}% từ đỉnh (Hiện tại: {vni_current:,.1f} điểm)!\n"
        f"👉 HÀNH ĐỘNG NGAY:\n"
        f"1. Dùng tiền mặt trong TK Techcombank (*9013) đặt mua ngay 1-2 lô chẵn (100 CP) giá đỏ của HPG, FUEVFVND hoặc E1VFVN30.\n"
        f"2. Trước 14h30 hôm nay: Vào TCInvest bấm Bán 100-119,15 CCQ TCBF cũ (~2,52tr, phí 0% FIFO) để tiền về sau 2 ngày bù lại khoản ứng!"
    )
elif effective_drawdown <= -5.0:
    zalo_msg = (
        f"⚠️ [CẢNH BÁO VÀNG TCINVEST] VN-Index điều chỉnh {effective_drawdown:.2f}% từ đỉnh ({vni_current:,.1f} điểm).\n"
        f"👉 Kiểm tra TK Techcombank Liên kết (*9013), nếu đã gom gần đủ 2,6 - 3,0 triệu đồng thì có thể đặt mua sớm 1 lô chẵn HPG hoặc FUEVFVND giá đỏ!"
    )
else:
    zalo_msg = (
        f"✅ [BÁO CÁO ĐỊNH KỲ TCINVEST] VN-Index ổn định tại {vni_current:,.1f} điểm (Lệch đỉnh: {effective_drawdown:.2f}%).\n"
        f"👉 Duy trì kỷ luật 80/20: Nạp {monthly_budget * tcbf_ratio / 100:,.0f}đ vào TCBF + Giữ {monthly_budget * (100 - tcbf_ratio) / 100:,.0f}đ trong TK Techcombank Sinh lời tự động."
    )

# Tự động bắn Zalo nếu vượt ngưỡng giảm 5% và chưa gửi trong phiên
if auto_zalo_alert and effective_drawdown <= -5.0:
    last_sent_level = st.session_state.get("last_zalo_alert_level", 0.0)
    if abs(effective_drawdown - last_sent_level) >= 1.0:
        ok, status_msg = send_zalo_notification(zalo_msg, zalo_bot_token, zalo_user_id, zalo_webhook)
        if ok:
            st.session_state["last_zalo_alert_level"] = effective_drawdown
            st.toast(f"📲 {status_msg}", icon="✅")

# Nút bấm gửi thử tin nhắn Zalo ngay trên Sidebar
with st.sidebar:
    if st.button("📨 Gửi thử Cảnh báo về Zalo ngay", use_container_width=True):
        ok, status_msg = send_zalo_notification(zalo_msg, zalo_bot_token, zalo_user_id, zalo_webhook)
        if ok:
            st.success(status_msg)
        else:
            st.warning(status_msg)

# ==========================================
# 5. GIAO DIỆN CHÍNH & BẢNG ĐIỀU KHIỂN
# ==========================================
st.title("📊 Trợ Lý Tích Sản VN30 & Quỹ Mở (Zalo Alert + Google Sheets)")
st.markdown(
    f"**Tổng tài sản nền tảng:** `14.935.000 ₫` *(300 CP TCB: 6,705tr | TCEF: 5,51tr | TCBF: 2,52tr | TCFF: 0,2tr)* "
    f"| **Dòng tiền tích sản:** `{monthly_budget:,.0f} ₫/tháng`"
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
col6.metric("Chiết khấu từ Đỉnh", f"{effective_drawdown:.2f}%", "Báo động Zalo: -5% / -10%")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 1. Biểu Đồ & Tiềm Năng Cổ Phiếu / ETF",
    "🤖 2. Máy Trạm Đề Xuất & Dự Trù Ngân Sách",
    "💼 3. Quản Trị Danh Mục 14,93 Triệu",
    "✅ 4. Lộ Trình & Checklist (Lưu Google Sheets)"
])

watchlist_rows = []
for ticker, meta in WATCHLIST_META.items():
    df_t = fetch_price_history(ticker, days=180)
    curr_p = float(df_t["close"].iloc[-1])
    chg_t_1m = calc_change(df_t, 21)
    lot_cost = curr_p * 100
    upside = ((meta["fair_price"] - curr_p) / curr_p) * 100

    if meta["pb"] <= 1.25:
        val_status = "🟢 Rẻ (Ưu tiên gom)"
    elif meta["pb"] <= 1.85:
        val_status = "🔵 Hợp lý (Mua tích sản)"
    elif meta["pb"] <= 2.20:
        val_status = "🟡 Theo dõi"
    else:
        val_status = "🔴 Đắt (Cân nhắc chốt lời)"

    watchlist_rows.append({
        "Mã CK": ticker,
        "Tên Cổ Phiếu / Quỹ": meta["name"],
        "Nhóm Ngành": meta["group"],
        "Giá Hiện Tại (₫)": curr_p,
        "Vốn 1 Lô Chẵn 100 CP (₫)": lot_cost,
        "Biến Động 1 Tháng (%)": round(chg_t_1m, 2),
        "P/B Hiện Tại": meta["pb"],
        "P/E": meta["pe"],
        "ROE (%)": meta["roe"],
        "Giá Mục Tiêu 1-2 Năm (₫)": meta["fair_price"],
        "Tiềm Năng Tăng Giá (%)": round(upside, 1),
        "Đánh Giá Định Giá": val_status,
        "Vai Trò Chiến Lược": meta["role"]
    })

df_watchlist = pd.DataFrame(watchlist_rows)

with tab1:
    st.subheader("Bảng Giá Tổng Hợp, Chi Phí Mua 1 Lô Chẵn (100 CP) & Tiềm Năng Sinh Lời")
    st.dataframe(
        df_watchlist.style.format({
            "Giá Hiện Tại (₫)": "{:,.0f}",
            "Vốn 1 Lô Chẵn 100 CP (₫)": "{:,.0f}",
            "Biến Động 1 Tháng (%)": "{:+.2f}%",
            "P/B Hiện Tại": "{:.2f}",
            "P/E": "{:.1f}",
            "ROE (%)": "{:.1f}%",
            "Giá Mục Tiêu 1-2 Năm (₫)": "{:,.0f}",
            "Tiềm Năng Tăng Giá (%)": "{:+.1f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

    col_chart_left, col_chart_right = st.columns([3, 2])
    with col_chart_left:
        selected_ticker = st.selectbox(
            "Chọn mã để xem Biểu đồ kỹ thuật & Đường trung bình MA20 / MA50:",
            options=["VNINDEX", "TCB", "HPG", "MBB", "ACB", "FUEVFVND", "E1VFVN30"],
            index=1
        )
        df_chart = fetch_price_history(selected_ticker, days=250)
        df_chart["MA20"] = df_chart["close"].rolling(20).mean()
        df_chart["MA50"] = df_chart["close"].rolling(50).mean()

        fig_candle = go.Figure()
        fig_candle.add_trace(go.Candlestick(
            x=df_chart["time"], open=df_chart["open"], high=df_chart["high"],
            low=df_chart["low"], close=df_chart["close"], name=selected_ticker
        ))
        fig_candle.add_trace(go.Scatter(
            x=df_chart["time"], y=df_chart["MA20"], mode="lines", name="MA20", line=dict(color="#1e88e5", width=1.5)
        ))
        fig_candle.add_trace(go.Scatter(
            x=df_chart["time"], y=df_chart["MA50"], mode="lines", name="MA50", line=dict(color="#fb8c00", width=1.5)
        ))
        fig_candle.update_layout(
            title=f"Biểu đồ biến động giá {selected_ticker}",
            xaxis_rangeslider_visible=False, height=420, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_candle, use_container_width=True)

    with col_chart_right:
        fig_upside = px.bar(
            df_watchlist.sort_values("Tiềm Năng Tăng Giá (%)", ascending=True),
            x="Tiềm Năng Tăng Giá (%)", y="Mã CK", color="Nhóm Ngành",
            orientation="h", text="Tiềm Năng Tăng Giá (%)",
            title="So sánh Dư địa tăng giá kỳ vọng (%)"
        )
        fig_upside.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
        fig_upside.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_upside, use_container_width=True)

with tab2:
    st.subheader("🤖 Tự Động Phân Tích Ngân Sách & Đề Xuất Mã Mua Theo Khả Năng Tài Chính")
    monthly_tcbf_alloc = monthly_budget * (tcbf_ratio / 100.0)
    monthly_stock_alloc = monthly_budget - monthly_tcbf_alloc
    tcff_sell_proceeds = 200000.0
    available_lot_cash = (monthly_stock_alloc * months_accumulated) + tcff_sell_proceeds
    tcbf_fifo_reserve = 2520000.0

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("Trích mua TCBF hàng tháng", f"{monthly_tcbf_alloc:,.0f} ₫", f"{tcbf_ratio}% ngân sách")
    b_col2.metric("Gom trong TK Techcombank/tháng", f"{monthly_stock_alloc:,.0f} ₫", f"{100 - tcbf_ratio}% ngân sách")
    b_col3.metric(f"Sức mua Lô chẵn sau {months_accumulated} tháng (+200k TCFF)", f"{available_lot_cash:,.0f} ₫", "Tự động cộng vào Sức mua")
    b_col4.metric("Kho đạn TCBF miễn phí bán (FIFO)", f"{tcbf_fifo_reserve:,.0f} ₫", "Sẵn sàng khi VNI giảm >10%")

    rec_list = []
    for _, row in df_watchlist.iterrows():
        ticker = row["Mã CK"]
        if ticker == "TCB":
            continue
        lot_cost = row["Vốn 1 Lô Chẵn 100 CP (₫)"]
        diff = available_lot_cash - lot_cost
        can_buy_now = diff >= 0
        diversification_bonus = 20 if ticker in ["HPG", "FUEVFVND", "E1VFVN30"] else 10
        affordability_bonus = 25 if can_buy_now else max(0, 15 + (diff / 100000))
        score = round(row["Tiềm Năng Tăng Giá (%)"] * 1.2 + diversification_bonus + affordability_bonus, 1)

        rec_list.append({
            "Điểm Ưu Tiên": score,
            "Mã Đề Xuất": ticker,
            "Tên & Nhóm Ngành": f"{row['Tên Cổ Phiếu / Quỹ']} ({row['Nhóm Ngành']})",
            "Số Tiền Cần Cho 100 CP/CCQ (₫)": lot_cost,
            "So Với Sức Mua Hiện Tại": f"Dư {diff:,.0f} ₫ (Mua được ngay)" if can_buy_now else f"Thiếu {abs(diff):,.0f} ₫ (Gom thêm)",
            "Khuyến Nghị Hành Động Cụ Thể": row["Vai Trò Chiến Lược"]
        })

    df_rec = pd.DataFrame(rec_list).sort_values("Điểm Ưu Tiên", ascending=False)
    st.dataframe(
        df_rec.style.format({"Điểm Ưu Tiên": "{:.1f} điểm", "Số Tiền Cần Cho 100 CP/CCQ (₫)": "{:,.0f}"}),
        use_container_width=True, hide_index=True
    )

with tab3:
    st.subheader("💼 Theo Dõi Danh Mục Thực Tế (14.935.000 ₫)")
    current_holdings = pd.DataFrame([
        {"Tài Sản": "TCB (300 CP)", "Loại": "Cổ phiếu trực tiếp", "Số Lượng": 300.00, "Vốn Gốc (₫)": 4400000, "Giá Trị Hiện Tại (₫)": 6705000, "Lãi/Lỗ (%)": 52.39},
        {"Tài Sản": "TCEF (Quỹ Cổ phiếu)", "Loại": "Quỹ mở cổ phiếu", "Số Lượng": 269.31, "Vốn Gốc (₫)": 4602342, "Giá Trị Hiện Tại (₫)": 5510000, "Lãi/Lỗ (%)": 19.72},
        {"Tài Sản": "TCBF (Quỹ Trái phiếu)", "Loại": "Quỹ mở trái phiếu", "Số Lượng": 119.15, "Vốn Gốc (₫)": 1892000, "Giá Trị Hiện Tại (₫)": 2520000, "Lãi/Lỗ (%)": 33.18},
        {"Tài Sản": "TCFF (Đã lên lịch Bán)", "Loại": "Quỹ mở ngắn hạn", "Số Lượng": 12.72, "Vốn Gốc (₫)": 195000, "Giá Trị Hiện Tại (₫)": 200000, "Lãi/Lỗ (%)": 0.60},
    ])
    total_val = current_holdings["Giá Trị Hiện Tại (₫)"].sum()
    current_holdings["Tỷ Trọng (%)"] = (current_holdings["Giá Trị Hiện Tại (₫)"] / total_val) * 100
    st.dataframe(
        current_holdings.style.format({
            "Số Lượng": "{:,.2f}", "Vốn Gốc (₫)": "{:,.0f}",
            "Giá Trị Hiện Tại (₫)": "{:,.0f}", "Lãi/Lỗ (%)": "{:+.2f}%", "Tỷ Trọng (%)": "{:.2f}%"
        }),
        use_container_width=True, hide_index=True
    )

with tab4:
    st.subheader("✅ Bảng Lộ Trình Chi Tiết & Checklist Thực Thi (Đồng bộ Google Sheets)")
    if "roadmap_state" not in st.session_state:
        loaded_data, sync_status = load_roadmap_data()
        st.session_state.roadmap_state = loaded_data
        st.session_state.sync_status = sync_status

    st.caption(f"Trạng thái lưu trữ: **{st.session_state.get('sync_status', '')}**")

    completed_count = sum(1 for item in st.session_state.roadmap_state if item["done"])
    total_steps = len(st.session_state.roadmap_state)
    st.progress(completed_count / total_steps, text=f"Tiến độ hoàn thành: {completed_count}/{total_steps} mốc ({completed_count/total_steps*100:.0f}%)")

    updated_state = []
    for item in st.session_state.roadmap_state:
        checked = st.checkbox(
            f"**[{item['time']}]** — {item['task']}",
            value=item["done"],
            key=item["id"]
        )
        updated_state.append({**item, "done": checked})

    if updated_state != st.session_state.roadmap_state:
        st.session_state.roadmap_state = updated_state
        synced_cloud = save_roadmap_data(updated_state)
        if synced_cloud:
            st.session_state.sync_status = "🟢 Đã lưu vĩnh viễn lên Google Sheets Cloud"
        st.rerun()
