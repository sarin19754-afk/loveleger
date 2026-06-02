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
    page_title="บัญชีค่าใช้จ่าย 💑",
    page_icon="💑",
    layout="wide",
)

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

COLUMNS = ["วันที่", "รายการ", "หมวดหมู่", "ยอดรวม", "ปะป๊า", "หม่ามี้", "หมายเหตุ"]

# ─── Google Sheets connection ───────────────────────────────────────────────

def get_gspread_client():
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_resource(ttl=30)
def get_sheet():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = spreadsheet.worksheet(SHEET_NAME)
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
    df["ปะป๊า"] = pd.to_numeric(df["ปะป๊า"], errors="coerce").fillna(0)
    df["หม่ามี้"] = pd.to_numeric(df["หม่ามี้"], errors="coerce").fillna(0)
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

st.title("💑 บัญชีค่าใช้จ่าย ปะป๊า & หม่ามี้")

# Sidebar — add expense
with st.sidebar:
    st.header("➕ เพิ่มรายการ")
    with st.form("add_form", clear_on_submit=True):
        expense_date = st.date_input("วันที่", value=date.today())
        description = st.text_input("รายการ", placeholder="เช่น ข้าวเที่ยง, ตั๋วหนัง")
        category = st.selectbox("หมวดหมู่", CATEGORIES)
        amount = st.number_input("ยอดรวม (บาท)", min_value=0.0, step=1.0, format="%.2f")
        split_mode = st.radio("การแบ่ง", ["หาร 2", "ปะป๊าจ่าย", "หม่ามี้จ่าย", "ไม่คิด"])
        note = st.text_input("หมายเหตุ (ถ้ามี)")
        submitted = st.form_submit_button("บันทึก", use_container_width=True, type="primary")

    if submitted:
        if not description:
            st.error("กรุณากรอกรายการ")
        elif amount <= 0:
            st.error("กรุณากรอกยอดเงิน")
        else:
            if split_mode == "หาร 2":
                papa = mama = amount / 2
            elif split_mode == "ปะป๊าจ่าย":
                papa, mama = amount, 0.0
            elif split_mode == "หม่ามี้จ่าย":
                papa, mama = 0.0, amount
            else:  # ไม่คิด
                papa = mama = 0.0

            row = [
                expense_date.strftime("%Y-%m-%d"),
                description,
                category,
                amount,
                papa,
                mama,
                note,
            ]
            append_row(row)
            st.success(f"บันทึกแล้ว: {description} {amount:,.2f} บาท")

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

total = filtered["ยอดรวม"].sum()
papa_total = filtered["ปะป๊า"].sum()
mama_total = filtered["หม่ามี้"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("ยอดรวมทั้งหมด", f"{total:,.2f} ฿")
c2.metric("ปะป๊าจ่าย", f"{papa_total:,.2f} ฿")
c3.metric("หม่ามี้จ่าย", f"{mama_total:,.2f} ฿")
diff = papa_total - mama_total
if abs(diff) < 0.01:
    c4.metric("ส่วนต่าง", "เท่ากัน ✅")
elif diff > 0:
    c4.metric("ส่วนต่าง", f"ปะป๊าจ่ายเกิน {diff:,.2f} ฿", delta=f"หม่ามี้ต้องคืน {diff:,.2f} ฿", delta_color="inverse")
else:
    c4.metric("ส่วนต่าง", f"หม่ามี้จ่ายเกิน {-diff:,.2f} ฿", delta=f"ปะป๊าต้องคืน {-diff:,.2f} ฿", delta_color="inverse")

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
            "คน": ["ปะป๊า", "หม่ามี้"],
            "ยอดรวม": [papa_total, mama_total],
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
    display["ปะป๊า"] = display["ปะป๊า"].map("{:,.2f}".format)
    display["หม่ามี้"] = display["หม่ามี้"].map("{:,.2f}".format)

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

    # Delete
    with st.expander("🗑️ ลบรายการ"):
        st.warning("การลบจะแก้ไข Google Sheets โดยตรง")
        row_nums = list(filtered.index)
        if row_nums:
            del_idx = st.selectbox(
                "เลือกแถวที่ต้องการลบ (index จาก 0)",
                options=row_nums,
                format_func=lambda i: f"{i}: {df.loc[i, 'รายการ']} — {df.loc[i, 'ยอดรวม']} ฿",
            )
            if st.button("ลบรายการนี้", type="primary"):
                delete_row(del_idx)
                st.success("ลบแล้ว")
                st.rerun()
