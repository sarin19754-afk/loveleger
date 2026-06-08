import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import json
import os

st.set_page_config(
    page_title="LoveLedger 🐱",
    page_icon="🐱",
    layout="wide",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

* { font-family: 'Kanit', sans-serif !important; }

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a0533 0%, #3b1a6b 50%, #6b2fa0 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.1);
}
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox select {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 10px !important;
    color: white !important;
}
[data-testid="stSidebar"] .stFormSubmitButton button {
    background: linear-gradient(90deg, #f953c6, #b91d73) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(249,83,198,0.4) !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.07) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
    transition: transform 0.2s;
}
[data-testid="stMetric"]:hover { transform: translateY(-3px); }
[data-testid="stMetricLabel"] { color: rgba(255,255,255,0.7) !important; font-size: 0.85rem !important; }
[data-testid="stMetricValue"] { color: #fff !important; font-weight: 700 !important; font-size: 1.6rem !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    padding: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: rgba(255,255,255,0.6) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #f953c6, #b91d73) !important;
    color: white !important;
}

/* Buttons */
.stButton button {
    border-radius: 12px !important;
    font-weight: 600 !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.1) !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 15px !important; overflow: hidden; }

/* Warning/Success/Info boxes */
.stAlert { border-radius: 12px !important; }

/* Material Icons font fix */
.material-icons, .material-symbols-rounded, span.material-icons {
    font-family: 'Material Icons' !important;
}
/* ซ่อนข้อความ keyboard_double_arrow */
[data-testid="collapsedControl"] { overflow: hidden; }
[data-testid="collapsedControl"] span {
    font-family: 'Material Icons' !important;
    font-size: 20px !important;
}
button[data-testid="baseButton-header"] span {
    font-family: 'Material Icons' !important;
    font-size: 20px !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}
</style>
""", unsafe_allow_html=True)

SPREADSHEET_ID = "1sVW_1Ssf8SFCKzGJmrXOJyRwsxvY0C9cvR9nFv_ujKg"
SHEET_NAME = "รายการ"

CATEGORIES = [
    "อาหาร/เครื่องดื่ม",
    "ท่องเที่ยว",
    "ของใช้/อุปกรณ์",
    "สุขภาพ/ยา",
    "เสื้อผ้า/แฟชั่น",
    "ความบันเทิง",
    "การเดินทาง",
    "อื่นๆ",
]

COLUMNS = ["วันที่", "รายการ", "หมวดหมู่", "ยอดรวม", "ประเภท", "หม่ามี้ติดปะป๊า", "ปะป๊าติดหม่ามี้", "หมายเหตุ"]

SPLIT_OPTIONS = [
    "ปะป๊าจ่าย หาร 2",        # ปะป๊าจ่าย แต่หารกัน → หม่ามี้ติดปะป๊า amount/2
    "หม่ามี้จ่าย หาร 2",       # หม่ามี้จ่าย แต่หารกัน → ปะป๊าติดหม่ามี้ amount/2
    "ปะป๊าจ่ายแทนหม่ามี้",     # ปะป๊าจ่ายแทน → หม่ามี้ติดปะป๊า amount
    "หม่ามี้จ่ายแทนปะป๊า",     # หม่ามี้จ่ายแทน → ปะป๊าติดหม่ามี้ amount
    "ไม่คิด",
]

# ─── Google Sheets connection ───────────────────────────────────────────────

def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if os.path.exists(creds_path):
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    else:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
    return gspread.authorize(creds)


@st.cache_resource(ttl=30)
def get_sheet():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = spreadsheet.worksheet(SHEET_NAME)
        # อัพเดต header ให้เป็นชื่อใหม่เสมอ
        ws.update('A1', [COLUMNS])
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=10)
        ws.append_row(COLUMNS)
    return ws


def load_data() -> pd.DataFrame:
    ws = get_sheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(records)
    df["ยอดรวม"] = pd.to_numeric(df["ยอดรวม"], errors="coerce").fillna(0)
    # รองรับ column ชื่อเก่า (ปะป๊า/หม่ามี้) และชื่อใหม่
    if "หม่ามี้ติดปะป๊า" not in df.columns:
        df["หม่ามี้ติดปะป๊า"] = pd.to_numeric(df.get("หม่ามี้", 0), errors="coerce").fillna(0)
    else:
        df["หม่ามี้ติดปะป๊า"] = pd.to_numeric(df["หม่ามี้ติดปะป๊า"], errors="coerce").fillna(0)
    if "ปะป๊าติดหม่ามี้" not in df.columns:
        df["ปะป๊าติดหม่ามี้"] = pd.to_numeric(df.get("ปะป๊า", 0), errors="coerce").fillna(0)
    else:
        df["ปะป๊าติดหม่ามี้"] = pd.to_numeric(df["ปะป๊าติดหม่ามี้"], errors="coerce").fillna(0)
    if "ประเภท" not in df.columns:
        df["ประเภท"] = ""
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    return df


def append_row(row: list):
    ws = get_sheet()
    ws.append_row(row, value_input_option="USER_ENTERED")
    st.cache_resource.clear()


def delete_row(row_index: int):
    ws = get_sheet()
    ws.delete_rows(row_index + 2)  # +2: header row + 0-indexed
    st.cache_resource.clear()


# ─── UI ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex; align-items:center; gap:20px; margin-bottom:10px;">
    <div style="font-size:80px; line-height:1; filter:drop-shadow(0 0 20px rgba(255,255,255,0.5));">
        🐱
    </div>
    <div>
        <div style="font-size:2.4rem; font-weight:700; color:white; line-height:1.1;
                    text-shadow: 0 0 30px rgba(249,83,198,0.8);">
            LoveLedger
        </div>
        <div style="font-size:1rem; color:rgba(255,255,255,0.6); margin-top:4px;">
            💕 บัญชีค่าใช้จ่าย ปะป๊า & หม่ามี้
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar — add expense
with st.sidebar:
    st.header("➕ เพิ่มรายการ")
    with st.form("add_form", clear_on_submit=True):
        expense_date = st.date_input("วันที่", value=date.today())
        description = st.text_input("รายการ", placeholder="เช่น ข้าวเที่ยง, ตั๋วหนัง")
        category = st.selectbox("หมวดหมู่", CATEGORIES)
        amount = st.number_input("ยอดรวม (บาท)", min_value=0.0, step=1.0, format="%.2f")
        split_mode = st.radio(
            "ประเภทการจ่าย",
            SPLIT_OPTIONS,
            captions=[
                f"หม่ามี้ติดปะป๊า ครึ่งนึง",
                f"ปะป๊าติดหม่ามี้ ครึ่งนึง",
                f"หม่ามี้ติดปะป๊า เต็มจำนวน",
                f"ปะป๊าติดหม่ามี้ เต็มจำนวน",
                f"ไม่นับหนี้",
            ]
        )
        note = st.text_input("หมายเหตุ (ถ้ามี)")
        submitted = st.form_submit_button("บันทึก", use_container_width=True, type="primary")

    if submitted:
        if not description:
            st.error("กรุณากรอกรายการ")
        elif amount <= 0:
            st.error("กรุณากรอกยอดเงิน")
        else:
            if split_mode == "ปะป๊าจ่าย หาร 2":
                mama_owes, papa_owes = amount / 2, 0.0
            elif split_mode == "หม่ามี้จ่าย หาร 2":
                mama_owes, papa_owes = 0.0, amount / 2
            elif split_mode == "ปะป๊าจ่ายแทนหม่ามี้":
                mama_owes, papa_owes = amount, 0.0
            elif split_mode == "หม่ามี้จ่ายแทนปะป๊า":
                mama_owes, papa_owes = 0.0, amount
            else:  # ไม่คิด
                mama_owes = papa_owes = 0.0

            row = [
                expense_date.strftime("%Y-%m-%d"),
                description,
                category,
                amount,
                split_mode,
                mama_owes,
                papa_owes,
                note,
            ]
            append_row(row)
            # แสดงผลสรุป
            if mama_owes > 0:
                st.success(f"✅ บันทึกแล้ว — หม่ามี้ติดปะป๊า {mama_owes:,.2f} ฿")
            elif papa_owes > 0:
                st.success(f"✅ บันทึกแล้ว — ปะป๊าติดหม่ามี้ {papa_owes:,.2f} ฿")
            else:
                st.success(f"✅ บันทึกแล้ว: {description} {amount:,.2f} ฿")

# ─── Load data ───────────────────────────────────────────────────────────────

df = load_data()

if df.empty:
    st.info("ยังไม่มีข้อมูล กรุณาเพิ่มรายการทางซ้าย")
    st.stop()

# ─── Filters ─────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    months = sorted(df["วันที่"].dropna().dt.to_period("M").unique(), reverse=True)
    month_options = ["ทั้งหมด"] + [str(m) for m in months]
    selected_month = st.selectbox("เดือน", month_options)
with col_f2:
    cat_options = ["ทั้งหมด"] + CATEGORIES
    selected_cat = st.selectbox("หมวดหมู่", cat_options)
with col_f3:
    search = st.text_input("ค้นหารายการ", placeholder="พิมพ์ชื่อรายการ...")

filtered = df.copy()
if selected_month != "ทั้งหมด":
    filtered = filtered[filtered["วันที่"].dt.to_period("M").astype(str) == selected_month]
if selected_cat != "ทั้งหมด":
    filtered = filtered[filtered["หมวดหมู่"] == selected_cat]
if search:
    filtered = filtered[filtered["รายการ"].str.contains(search, case=False, na=False)]

# ─── Summary cards ───────────────────────────────────────────────────────────

# แยก row ปกติ กับ row เคลียร์หนี้
normal = filtered[filtered["ประเภท"] != "เคลียร์หนี้"]
total = normal["ยอดรวม"].sum()
mama_owes_total = filtered["หม่ามี้ติดปะป๊า"].sum()
papa_owes_total = filtered["ปะป๊าติดหม่ามี้"].sum()
net = mama_owes_total - papa_owes_total  # บวก = หม่ามี้ยังติดอยู่, ลบ = ปะป๊ายังติดอยู่

# ยอดสุทธิที่ค้างจริงๆ (บวก = หม่ามี้ติดปะป๊า, ลบ = ปะป๊าติดหม่ามี้)
mama_net = max(0.0, float(net))   # หม่ามี้ยังติดปะป๊าอยู่
papa_net = max(0.0, float(-net))  # ปะป๊ายังติดหม่ามี้อยู่

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 ยอดรวมทั้งหมด", f"{total:,.2f} ฿")
c2.metric("👨 หม่ามี้ติดปะป๊า", f"{mama_net:,.2f} ฿")
c3.metric("👩 ปะป๊าติดหม่ามี้", f"{papa_net:,.2f} ฿")
if abs(net) < 0.01:
    c4.metric("🎉 สรุปหนี้", "เคลียร์แล้ว ✅")
elif net > 0:
    c4.metric("🧾 สรุปหนี้", f"หม่ามี้ติดปะป๊า {net:,.2f} ฿", delta=f"หม่ามี้ต้องจ่าย {net:,.2f} ฿", delta_color="inverse")
else:
    c4.metric("🧾 สรุปหนี้", f"ปะป๊าติดหม่ามี้ {-net:,.2f} ฿", delta=f"ปะป๊าต้องจ่าย {-net:,.2f} ฿", delta_color="inverse")

# ─── ปุ่มเคลียร์หนี้ ──────────────────────────────────────────────────────────
if abs(net) > 0.01:
    st.divider()
    col_clear1, col_clear2 = st.columns([3, 1])
    with col_clear1:
        if net > 0:
            st.warning(f"💸 หม่ามี้ยังติดปะป๊าอยู่ **{net:,.2f} ฿**")
        else:
            st.warning(f"💸 ปะป๊ายังติดหม่ามี้อยู่ **{-net:,.2f} ฿**")
    with col_clear2:
        if st.button("✅ เคลียร์หนี้แล้ว!", type="primary", use_container_width=True):
            net_val = float(net)
            if net_val > 0:
                clear_row = [date.today().strftime("%Y-%m-%d"), "เคลียร์หนี้", "อื่นๆ", round(net_val, 2), "เคลียร์หนี้", round(-net_val, 2), 0.0, "เคลียร์หนี้กัน"]
            else:
                clear_row = [date.today().strftime("%Y-%m-%d"), "เคลียร์หนี้", "อื่นๆ", round(-net_val, 2), "เคลียร์หนี้", 0.0, round(net_val, 2), "เคลียร์หนี้กัน"]
            append_row(clear_row)
            st.success("✅ เคลียร์หนี้เรียบร้อย!")
            st.rerun()

st.divider()

# ─── Charts ──────────────────────────────────────────────────────────────────

tab_table, tab_chart = st.tabs(["📋 รายการ", "📊 กราฟ"])

with tab_chart:
    ch1, ch2 = st.columns(2)

    with ch1:
        if not filtered.empty and "หมวดหมู่" in filtered.columns:
            cat_df = filtered.groupby("หมวดหมู่")["ยอดรวม"].sum().reset_index()
            cat_df = cat_df[cat_df["ยอดรวม"] > 0]
            fig_pie = px.pie(
                cat_df,
                values="ยอดรวม",
                names="หมวดหมู่",
                title="สัดส่วนค่าใช้จ่ายตามหมวดหมู่",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with ch2:
        compare_df = pd.DataFrame({
            "คน": ["หม่ามี้ติดปะป๊า", "ปะป๊าติดหม่ามี้"],
            "ยอดรวม": [mama_owes_total, papa_owes_total],
        })
        fig_bar = px.bar(
            compare_df,
            x="คน",
            y="ยอดรวม",
            title="เปรียบเทียบยอดรวม",
            color="คน",
            color_discrete_map={"ปะป๊า": "#4C72B0", "หม่ามี้": "#DD8452"},
            text_auto=".2f",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Timeline
    if not filtered.empty:
        timeline = (
            filtered.dropna(subset=["วันที่"])
            .groupby(filtered["วันที่"].dt.date)["ยอดรวม"]
            .sum()
            .reset_index()
        )
        timeline.columns = ["วันที่", "ยอดรวม"]
        fig_line = px.line(timeline, x="วันที่", y="ยอดรวม", title="ค่าใช้จ่ายรายวัน", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

# ─── Table + delete ──────────────────────────────────────────────────────────

with tab_table:
    display = filtered.copy()
    display["วันที่"] = display["วันที่"].dt.strftime("%Y-%m-%d")
    display["ยอดรวม"] = display["ยอดรวม"].map("{:,.2f}".format)
    display["หม่ามี้ติดปะป๊า"] = display["หม่ามี้ติดปะป๊า"].map("{:,.2f}".format)
    display["ปะป๊าติดหม่ามี้"] = display["ปะป๊าติดหม่ามี้"].map("{:,.2f}".format)

    st.dataframe(display.reset_index(drop=True), use_container_width=True, height=400)

    # Export Excel
    if st.button("⬇️ Export Excel"):
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="ค่าใช้จ่าย")
        st.download_button(
            label="คลิกเพื่อดาวน์โหลด",
            data=buf.getvalue(),
            file_name=f"expense_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.divider()
    # Delete
    with st.expander("🗑️ ลบรายการ"):
        st.markdown("⚠️ **การลบจะแก้ไข Google Sheets โดยตรง**")
        row_nums = list(filtered.index)
        if row_nums:
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                del_idx = st.selectbox(
                    "เลือกรายการที่ต้องการลบ",
                    options=row_nums,
                    format_func=lambda i: f"📌 {df.loc[i, 'วันที่'].strftime('%Y-%m-%d') if pd.notna(df.loc[i, 'วันที่']) else ''} | {df.loc[i, 'รายการ']} | {float(df.loc[i, 'ยอดรวม']):,.0f} ฿",
                )
            with col_del2:
                st.write("")
                st.write("")
                if st.button("🗑️ ลบ", type="primary", use_container_width=True):
                    delete_row(del_idx)
                    st.success("✅ ลบเรียบร้อย!")
                    st.rerun()
        else:
            st.info("ไม่มีรายการให้ลบ")
