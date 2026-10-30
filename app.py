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
            with open(CHECKLIST_FILE
