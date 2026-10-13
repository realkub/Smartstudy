"""
app.py - SmartStudy: ระบบจัดการการบ้านและวางแผนการเรียนอัจฉริยะ (Clean Light & Dark Mode)

พัฒนาด้วย Python, Streamlit, SQLite, Pandas และ Altair
- ค่าเริ่มต้นเป็น โหมดสว่าง (Light Theme) สีขาวคลีน สบายตา ตัวหนังสือคมชัด 100%
- มีตัวเลือกสลับไป โหมดมืด สบายตา (Dark Theme) ได้ในปุ่มตั้งค่า ⚙️
- กราฟทุกตัวแสดงผลแนวนอน 100% และตัวหนังสือคมชัด ไม่กลืนกับพื้นหลังในทุกโหมด
- โหมดดูตัวอย่าง (Guest Mode) สำหรับผู้เข้าชม และระบบล็อกอินแยกข้อมูล
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
import database
import planner
import chatbot

# ตั้งค่าหน้าเว็บ Streamlit
st.set_page_config(
    page_title="SmartStudy | วางแผนการเรียน สบายตา คลีนๆ",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# เตรียมค่าเริ่มต้นใน Session State (Default: โหมดสว่าง สีขาว คลีนๆ ตัวหนังสือชัดเจน)
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "light"  # ค่าเริ่มต้น: โหมดสว่าง คลีนๆ (Light Theme)
if "accent_color" not in st.session_state:
    st.session_state["accent_color"] = "#4f46e5"  # สีม่วงครามสุขุม สบายตา
if "font_size_choice" not in st.session_state:
    st.session_state["font_size_choice"] = "ปกติ (Normal)"
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []
if "chat_api_key" not in st.session_state:
    st.session_state["chat_api_key"] = ""
if "chat_provider" not in st.session_state:
    st.session_state["chat_provider"] = "auto"

is_dark = st.session_state["theme_mode"] == "dark"

if is_dark:
    # 🌙 DARK THEME (โหมดมืด สบายตา ไม่ดำสนิท และไม่แสบตา)
    bg_main = "#17191e"          # สีเทาชาร์โคลนุ่มลึก
    bg_card = "#20242c"          # พื้นหลังการ์ดสีเข้ม
    bg_sidebar = "#131519"       # แถบซ้ายสีเข้มเรียบร้อย
    text_main = "#eef2f6"        # ตัวหนังสือสีขาวนวล คมชัด สบายตา
    text_muted = "#9aa5b5"       # ตัวหนังสือสีเทากลาง ชัดเจน
    border_color = "#2d333f"     # เส้นขอบบางๆ
    hover_bg = "#292f3a"
    rec_box_bg = "#1e2230"
    rec_box_border = "#4f46e5"
    pill_bg = "#282e39"
    pill_text = "#cbd5e1"
else:
    # ☀️ LIGHT THEME (ค่าเริ่มต้น: พื้นขาว คลีน สบายตา ตัวหนังสือคมชัด 100%)
    bg_main = "#f8fafc"          # สีขาวนวลสะอาดตา
    bg_card = "#ffffff"          # การ์ดสีขาวสะอาด
    bg_sidebar = "#ffffff"       # แถบข้างสีขาว
    text_main = "#0f172a"        # ตัวหนังสือสีเทากรมท่าเข้ม คมชัด อ่านง่ายมาก 100%
    text_muted = "#475569"       # สีข้อความรองชัดเจน ไม่อ่อนเกินไป
    border_color = "#e2e8f0"     # เส้นขอบบางๆ สวยงาม
    hover_bg = "#f1f5f9"
    rec_box_bg = "#f0f4ff"       # กล่องแนะนำสีฟ้าอ่อนนุ่มนวล
    rec_box_border = "#c7d2fe"
    pill_bg = "#f1f5f9"
    pill_text = "#0f172a"

theme_accent = st.session_state["accent_color"]
font_base_size = "1.06rem" if st.session_state["font_size_choice"] == "ใหญ่ขึ้น (Large)" else "0.98rem"


def init_application():
    """เตรียมฐานข้อมูลเมื่อแอปเริ่มทำงาน และโหลดข้อมูลตัวอย่างสำหรับโหมด Guest"""
    database.init_db()
    database.seed_sample_data(user_id=1)


init_application()


# ----------------- POPUP MODAL: กล่องล็อกอิน / สมัครสมาชิก -----------------
@st.dialog("🔑 เข้าสู่ระบบ / สมัครสมาชิก SmartStudy")
def open_auth_modal():
    tab_login, tab_register = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิกใหม่ (Register)"])

    with tab_login:
        st.markdown("##### ยินดีต้อนรับครับ! เข้าสู่ระบบเพื่อจัดการงานของคุณ ✨")
        login_user = st.text_input("ชื่อผู้ใช้ (Username)", key="modal_login_user", placeholder="เช่น student")
        login_pass = st.text_input("รหัสผ่าน (Password)", type="password", key="modal_login_pass", placeholder="••••••••")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("เข้าสู่ระบบ 🚀", type="primary", use_container_width=True):
                if not login_user or not login_pass:
                    st.warning("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
                else:
                    ok, user_data, msg = database.authenticate_user(login_user, login_pass)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = user_data
                        st.success(f"ยินดีต้อนรับคุณ {user_data['full_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        with col_b2:
            if st.button("⚡ บัญชีทดลอง (1 คลิก)", use_container_width=True, help="คลิกเดียวเข้าใช้งานด้วยบัญชีตัวอย่าง"):
                ok, user_data, _ = database.authenticate_user("student", "password123")
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = user_data
                    st.rerun()

        st.caption("💡 บัญชีทดลอง: Username = `student` | Password = `password123`")

    with tab_register:
        st.markdown("##### สร้างบัญชีนักเรียนใหม่ 📚")
        reg_name = st.text_input("ชื่อ-นามสกุล", placeholder="เช่น ด.ญ. พิมพ์มาดา ตั้งใจเรียน")
        reg_user = st.text_input("ตั้งชื่อผู้ใช้ (Username)", placeholder="เช่น pimmada")
        reg_pass = st.text_input("ตั้งรหัสผ่าน", type="password", placeholder="อย่างน้อย 4 ตัวอักษร")
        reg_pass_confirm = st.text_input("ยืนยันรหัสผ่านอีกครั้ง", type="password", placeholder="••••••••")

        if st.button("สร้างบัญชีนักเรียน 📝", type="primary", use_container_width=True):
            if reg_pass != reg_pass_confirm:
                st.error("⚠️ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                success, reg_msg = database.register_user(reg_user, reg_pass, reg_name)
                if success:
                    st.success(f"🎉 {reg_msg}")
                    st.info("กรุณาสลับไปแท็บ 'เข้าสู่ระบบ' เพื่อล็อกอินได้เลยครับ")
                else:
                    st.error(f"⚠️ {reg_msg}")


# ----------------- POPUP MODAL: กล่องตั้งค่าสไตล์ & ธีม ⚙️ -----------------
@st.dialog("⚙️ ปรับแต่งสไตล์หน้าเว็บ (Theme Settings)")
def open_settings_modal():
    st.markdown("สลับระหว่างโหมดสว่างและโหมดมืด พร้อมปรับสีสันตามต้องการ")
    st.markdown("---")

    # 1. เลือกระหว่างโหมดสว่าง (Default) หรือโหมดมืด
    st.markdown("##### 🌓 โหมดหน้าจอ (Theme Mode)")
    current_mode_idx = 0 if st.session_state["theme_mode"] == "light" else 1
    selected_mode = st.radio(
        "เลือกโหมดการแสดงผล",
        ["☀️ โหมดสว่าง คลีนๆ (Light Mode - ค่าเริ่มต้น)", "🌙 โหมดมืด สบายตา (Dark Mode)"],
        index=current_mode_idx
    )
    new_theme_mode = "light" if "Light Mode" in selected_mode else "dark"

    # 2. โทนสีเน้น
    st.markdown("##### 🎨 โทนสีเน้นสุภาพ (Accent Color)")
    accent_options = {
        "💜 ม่วงอินดิโก้ (Soft Indigo)": "#4f46e5",
        "💙 ฟ้าครามสุขุม (Calm Blue)": "#2563eb",
        "🌿 เขียวเซจธรรมชาติ (Forest Sage)": "#059669",
        "🤎 เอิร์ธโทนอบอุ่น (Warm Earth)": "#d97706"
    }
    current_acc_idx = list(accent_options.values()).index(st.session_state["accent_color"]) if st.session_state["accent_color"] in accent_options.values() else 0
    selected_accent_name = st.selectbox("เลือกสีเน้น", list(accent_options.keys()), index=current_acc_idx)

    # 3. ขนาดฟอนต์
    st.markdown("##### 🔤 ขนาดตัวอักษร")
    selected_font_size = st.radio(
        "ขนาดฟอนต์",
        ["ปกติ (Normal)", "ใหญ่ขึ้น (Large)"],
        index=0 if st.session_state["font_size_choice"] == "ปกติ (Normal)" else 1,
        horizontal=True
    )

    st.markdown("---")
    st.markdown("##### 💾 จัดการฐานข้อมูล (Database)")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("📥 โหลดการบ้านตัวอย่าง", use_container_width=True):
            user_id_to_seed = st.session_state["current_user"]["id"] if st.session_state["authenticated"] else 1
            database.seed_sample_data(user_id=user_id_to_seed)
            st.success("โหลดข้อมูลตัวอย่างเรียบร้อย!")
            st.rerun()

    with col_d2:
        if st.button("🗑️ ล้างข้อมูลการบ้าน", use_container_width=True, type="secondary"):
            user_id_to_clear = st.session_state["current_user"]["id"] if st.session_state["authenticated"] else 1
            conn = database.get_connection()
            try:
                conn.execute("DELETE FROM tasks WHERE user_id = ?", (user_id_to_clear,))
                conn.commit()
                st.warning("ล้างข้อมูลเรียบร้อยแล้ว")
                st.rerun()
            finally:
                conn.close()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("บันทึกและใช้ธีมนี้ ✅", type="primary", use_container_width=True):
        st.session_state["theme_mode"] = new_theme_mode
        st.session_state["accent_color"] = accent_options[selected_accent_name]
        st.session_state["font_size_choice"] = selected_font_size
        st.rerun()


# ----------------- INJECT CUSTOM CSS -----------------
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
    /* ฟอนต์ Prompt และสีข้อความหลัก คมชัด 100% */
    html, body, [class*="css"], .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, input, select, textarea {{
        font-family: 'Prompt', sans-serif !important;
        font-size: {font_base_size};
        color: {text_main};
    }}
    /* ฟอนต์ปุ่ม - ไม่ใส่ color ที่นี่ เพื่อให้ primary button ตั้งสีเองได้ */
    button {{
        font-family: 'Prompt', sans-serif !important;
        font-size: {font_base_size};
    }}


    /* สีพื้นหลังของแอปหลัก */
    .stApp {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
    }}

    /* สไตล์การ์ดงาน คลีน สบายตา */
    .tech-card {{
        background-color: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .tech-card:hover {{
        border-color: {theme_accent} !important;
        transform: translateY(-2px);
    }}

    /* กล่องแนะนำงานอันดับ 1 */
    .recommendation-box {{
        background-color: {rec_box_bg};
        border: 1.5px solid {rec_box_border} !important;
        border-radius: 16px;
        padding: 22px 24px;
        margin-bottom: 24px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.04);
    }}

    /* ป้ายชื่อวิชา */
    .subject-pill {{
        background-color: {pill_bg};
        color: {pill_text};
        border: 1px solid {border_color};
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.88em;
        font-weight: 500;
    }}

    /* แถบ Sidebar กว้าง นุ่มนวล */
    section[data-testid="stSidebar"] {{
        min-width: 380px !important;
        max-width: 420px !important;
        width: 380px !important;
        background-color: {bg_sidebar} !important;
        border-right: 1.5px solid {border_color};
    }}

    /* เมนู Radio นำทางขนาดใหญ่ ชัดเจน */
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 12px 18px !important;
        margin-bottom: 10px !important;
        border-radius: 14px !important;
        background-color: {bg_card};
        border: 1px solid {border_color};
        transition: all 0.2s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        border-color: {theme_accent} !important;
        background-color: {hover_bg};
        transform: translateX(4px);
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
        font-size: 1.2rem !important;
        font-weight: 500 !important;
        color: {text_main} !important;
    }}

    /* ปุ่มใน Sidebar (รวมถึงปุ่มตั้งค่าและปุ่มล็อกอิน) */
    section[data-testid="stSidebar"] button {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
        border: 1.5px solid {border_color} !important;
        font-size: 1.12rem !important;
        font-weight: 600 !important;
        padding: 12px 18px !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }}
    section[data-testid="stSidebar"] button:hover {{
        border-color: {theme_accent} !important;
        background-color: {hover_bg} !important;
        color: {theme_accent} !important;
    }}
    section[data-testid="stSidebar"] button[kind="primary"] {{
        background-color: {theme_accent} !important;
        color: #ffffff !important;
        border: none !important;
    }}

    /* ปุ่ม Primary ทั่วทั้งเว็บ - ข้อความขาวเสมอ */
    button[kind="primary"] {{
        background-color: {theme_accent} !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    button[kind="primary"] p,
    button[kind="primary"] span,
    button[kind="primary"] * {{
        color: #ffffff !important;
    }}

    /* ปุ่ม Secondary ทั่วทั้งเว็บ */
    button[kind="secondary"] {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
        border: 1px solid {border_color} !important;
    }}
    button[kind="secondary"]:hover {{
        background-color: {hover_bg} !important;
        border-color: {theme_accent} !important;
    }}

    /* =========================================================
       POPUP DIALOG — Streamlit 1.65+ ใช้ data-testid="stDialog"
       (เก่า: stModal / role="dialog" → ใช้ไม่ได้แล้ว)
       ========================================================= */

    /* กล่องกระจกสีขาว/เข้มของ dialog (ลูกโดยตรงของ stDialog) */
    div[data-testid="stDialog"] > div {{
        background-color: {bg_card} !important;
        border: 1.5px solid {border_color} !important;
        border-radius: 18px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35) !important;
    }}

    /* Layer ถัดเข้าไปอีก (Streamlit wrapper divs) */
    div[data-testid="stDialog"] > div > div,
    div[data-testid="stDialog"] > div > div > div {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
    }}

    /* Text elements ภายใน dialog */
    div[data-testid="stDialog"] h1,
    div[data-testid="stDialog"] h2,
    div[data-testid="stDialog"] h3,
    div[data-testid="stDialog"] h4,
    div[data-testid="stDialog"] h5,
    div[data-testid="stDialog"] h6,
    div[data-testid="stDialog"] p,
    div[data-testid="stDialog"] label {{
        color: {text_main} !important;
    }}
    div[data-testid="stDialog"] span {{
        color: {text_main} !important;
    }}

    /* Streamlit Markdown inside dialog */
    div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] h5 {{
        color: {text_main} !important;
    }}

    /* Widget labels */
    div[data-testid="stDialog"] [data-testid="stWidgetLabel"] p,
    div[data-testid="stDialog"] [data-testid="stWidgetLabel"] label {{
        color: {text_main} !important;
    }}

    /* Caption */
    div[data-testid="stDialog"] [data-testid="stCaptionContainer"] p {{
        color: {text_muted} !important;
    }}

    /* Input fields ใน dialog */
    div[data-testid="stDialog"] input,
    div[data-testid="stDialog"] textarea {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
        border: 1.5px solid {border_color} !important;
        border-radius: 10px !important;
    }}
    div[data-testid="stDialog"] [data-baseweb="input"],
    div[data-testid="stDialog"] [data-baseweb="base-input"] {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
    }}

    /* Dropdown ใน dialog */
    div[data-testid="stDialog"] [data-baseweb="select"] > div {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
        border-color: {border_color} !important;
    }}
    div[data-testid="stDialog"] [data-baseweb="select"] span {{
        color: {text_main} !important;
    }}

    /* Popover / listbox (dropdown options) */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
        border: 1px solid {border_color} !important;
    }}
    li[role="option"]:hover {{
        background-color: {hover_bg} !important;
        color: {theme_accent} !important;
    }}

    /* Radio ใน dialog */
    div[data-testid="stDialog"] [data-testid="stRadio"] label p,
    div[data-testid="stDialog"] [data-testid="stRadio"] label span {{
        color: {text_main} !important;
    }}

    /* Tab bar ใน dialog (login / register) */
    div[data-testid="stDialog"] [data-baseweb="tab-list"] {{
        background-color: {bg_main} !important;
        border-radius: 12px !important;
        padding: 4px !important;
    }}
    div[data-testid="stDialog"] button[data-baseweb="tab"] {{
        color: {text_muted} !important;
        font-weight: 500 !important;
        background-color: transparent !important;
        border: none !important;
    }}
    div[data-testid="stDialog"] button[data-baseweb="tab"] p {{
        color: {text_muted} !important;
    }}
    div[data-testid="stDialog"] button[data-baseweb="tab"][aria-selected="true"],
    div[data-testid="stDialog"] button[data-baseweb="tab"][aria-selected="true"] p {{
        color: {theme_accent} !important;
        font-weight: 700 !important;
        border-bottom-color: {theme_accent} !important;
    }}

    /* Primary button ใน dialog — ข้อความขาวเสมอ */
    div[data-testid="stDialog"] button[kind="primary"] {{
        background-color: {theme_accent} !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stDialog"] button[kind="primary"] p,
    div[data-testid="stDialog"] button[kind="primary"] span,
    div[data-testid="stDialog"] button[kind="primary"] * {{
        color: #ffffff !important;
    }}

    /* Secondary / default buttons ใน dialog */
    div[data-testid="stDialog"] button:not([kind="primary"]):not([data-baseweb="tab"]):not([aria-label="Close"]) {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
        border: 1.5px solid {border_color} !important;
        border-radius: 10px !important;
    }}
    div[data-testid="stDialog"] button:not([kind="primary"]):not([data-baseweb="tab"]):not([aria-label="Close"]) p,
    div[data-testid="stDialog"] button:not([kind="primary"]):not([data-baseweb="tab"]):not([aria-label="Close"]) span {{
        color: {text_main} !important;
    }}

    /* ปุ่ม X ปิด dialog */
    div[data-testid="stDialog"] button[aria-label="Close"] {{
        color: {text_main} !important;
        background-color: transparent !important;
        border: none !important;
    }}

    /* HR divider ใน dialog */
    div[data-testid="stDialog"] hr {{
        border-color: {border_color} !important;
    }}

    /* กล่องโปรไฟล์ผู้ใช้ */
    .user-profile-badge {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 14px;
    }}

    /* กล่องคำคมให้กำลังใจ */
    .quote-box {{
        background-color: {rec_box_bg};
        border-left: 4px solid {theme_accent};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 22px;
        color: {text_main};
        font-size: 1.02em;
    }}

    /* ปรับแต่งการแสดงผลกล่องกราฟและ SVG canvas ภายใน */
    div[data-testid="stAltairChart"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 14px !important;
        padding: 16px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
    }}
    /* SVG canvas ของกราฟ Vega/Altair */
    div[data-testid="stAltairChart"] canvas,
    div[data-testid="stAltairChart"] svg {{
        background-color: {bg_card} !important;
        border-radius: 10px !important;
    }}
    /* ตัวหนังสือทุกตัวใน SVG กราฟ (label แกน X/Y, legend, ตัวเลข) */
    div[data-testid="stAltairChart"] svg text {{
        fill: {text_main} !important;
        font-family: 'Prompt', sans-serif !important;
    }}
    /* เส้น grid ใน SVG */
    div[data-testid="stAltairChart"] svg .mark-rule line,
    div[data-testid="stAltairChart"] svg line {{
        stroke: {border_color} !important;
    }}

    header[data-testid="stHeader"] {{
        background: transparent;
    }}

    /* กล่องแชท AI ให้เข้าธีม */
    [data-testid="stChatMessage"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
        padding: 10px 14px !important;
        margin-bottom: 10px !important;
    }}
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] span {{
        color: {text_main} !important;
    }}
    [data-testid="stChatInput"] {{
        background-color: {bg_card} !important;
        border: 1.5px solid {border_color} !important;
        border-radius: 16px !important;
    }}
    .quick-chip {{
        display: inline-block;
        background: {pill_bg};
        color: {pill_text};
        border: 1px solid {border_color};
        border-radius: 999px;
        padding: 6px 12px;
        margin: 0 6px 8px 0;
        font-size: 0.88em;
    }}
</style>
""", unsafe_allow_html=True)


# ----------------- ตรวจสอบสถานะผู้ใช้ -----------------
is_logged_in = st.session_state["authenticated"]
current_user = st.session_state["current_user"]
active_user_id = current_user["id"] if is_logged_in else 1


def get_task_data():
    raw_df = database.get_all_tasks(user_id=active_user_id)
    if raw_df.empty:
        return pd.DataFrame()
    return planner.analyze_and_rank_tasks(raw_df)


# ----------------- ฟังก์ชันปรับแต่งธีมกราฟ ALTAIR ให้คมชัด 100% ทั้ง LIGHT และ DARK -----------------
def format_chart(chart):
    """
    ปรับแต่งกราฟให้พื้นหลังตรงกับธีม และตัวหนังสือแกน X/Y คมชัด มองเห็นชื่อวิชาได้ 100% ในทุกโหมด
    """
    return (
        chart
        .configure(
            background=bg_card,   # ✅ Vega top-level background — ครอบคลุมทั้ง chart
            font="Prompt"
        )
        .configure_view(
            stroke=None
        )
        .configure_axis(
            domain=False,
            labelColor=text_main,
            titleColor=text_muted,
            gridColor=border_color,
            tickColor=border_color,
            labelFont="Prompt",
            titleFont="Prompt",
            labelFontSize=13,
            labelFontWeight="bold",
            titleFontSize=12
        )
        .configure_legend(
            labelColor=text_main,
            titleColor=text_main,
            labelFont="Prompt",
            titleFont="Prompt",
            labelFontSize=12,
            labelFontWeight="bold",
            fillColor=bg_card
        )
        .configure_text(
            color=text_main,
            font="Prompt",
            fontSize=12,
            fontWeight="bold"
        )
        .configure_title(
            color=text_main,
            font="Prompt"
        )
    )



# ----------------- SIDEBAR เมนูนำทางฝั่งซ้าย (LEFT NAVIGATION) -----------------
with st.sidebar:
    # โลโก้ & ชื่อโปรเจกต์
    st.markdown(
        f"""
        <div style="padding: 10px 0 14px 0;">
            <div style="font-size: 2.1em; font-weight: 700; color: {theme_accent}; display: flex; align-items: center; gap: 10px; line-height: 1.2;">
                🎓 SmartStudy
            </div>
            <div style="color: {text_muted}; font-size: 0.95em; margin-top: 4px;">
                วางแผนการเรียนอย่างมีความสุข & สบายตา ✨
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # แสดงสถานะผู้ใช้
    if is_logged_in:
        st.markdown(
            f"""
            <div class="user-profile-badge">
                <span style="font-size: 1.8em;">👨‍🎓</span>
                <div style="line-height: 1.3;">
                    <div style="font-weight: 600; color: {text_main}; font-size: 1.05em;">{current_user['full_name']}</div>
                    <div style="color: {theme_accent}; font-size: 0.85em;">@{current_user['username']} • สมาชิก</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="user-profile-badge" style="border-style: dashed; border-color: {border_color};">
                <span style="font-size: 1.8em;">👀</span>
                <div style="line-height: 1.3;">
                    <div style="font-weight: 600; color: {text_main}; font-size: 1.05em;">โหมดดูตัวอย่าง (Guest)</div>
                    <div style="color: {text_muted}; font-size: 0.85em;">เข้าสู่ระบบเพื่อบันทึกงานของคุณ</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🔑 เข้าสู่ระบบ / สมัครสมาชิก", use_container_width=True, type="primary"):
            open_auth_modal()

    st.markdown(f"<hr style='margin: 10px 0 18px 0; border: none; border-top: 1.5px solid {border_color};'>", unsafe_allow_html=True)

    # เมนูนำทางหลัก
    st.markdown(f"<div style='color: {text_muted}; font-size: 0.9em; font-weight: 600; text-transform: uppercase; margin-bottom: 10px;'>เมนูหลัก (Navigation)</div>", unsafe_allow_html=True)
    menu_selection = st.radio(
        label="เมนูหลัก",
        options=[
            "📊 แดชบอร์ด & วิเคราะห์งาน",
            "➕ เพิ่มการบ้านใหม่",
            "📋 รายการการบ้านทั้งหมด",
            "⏱️ โหมดจับเวลาโฟกัส (Pomodoro)"
        ],
        label_visibility="collapsed"
    )

    st.markdown(f"<hr style='margin: 24px 0 18px 0; border: none; border-top: 1.5px solid {border_color};'>", unsafe_allow_html=True)

    # ปุ่มฟันเฟือง ⚙️ ตั้งค่าระบบ
    st.markdown(f"<div style='color: {text_muted}; font-size: 0.9em; font-weight: 600; text-transform: uppercase; margin-bottom: 10px;'>เครื่องมือ & การตั้งค่า</div>", unsafe_allow_html=True)
    if st.button("⚙️ ปรับแต่งสไตล์ & ธีม (Settings)", use_container_width=True):
        open_settings_modal()

    # ปุ่มออกจากระบบ (ถ้าล็อกอินอยู่)
    if is_logged_in:
        if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True, type="secondary"):
            st.session_state["authenticated"] = False
            st.session_state["current_user"] = None
            st.rerun()

    st.markdown(
        f"""
        <div style="color: {text_muted}; font-size: 0.78em; text-align: center; border-top: 1px solid {border_color}; margin-top: 25px; padding-top: 15px;">
            SmartStudy • Clean Edition<br>
            Python • Streamlit • SQLite • Pandas
        </div>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# แถบแจ้งเตือนด้านบนสำหรับโหมด GUEST (BANNER)
# ==============================================================================
if not is_logged_in:
    b_col1, b_col2 = st.columns([4, 1.2])
    with b_col1:
        st.markdown(
            f"""
            <div style="background-color: {rec_box_bg}; border: 1.5px solid {rec_box_border}; border-radius: 12px; padding: 12px 18px; margin-bottom: 15px;">
                <span style="font-weight: 600; color: {text_main}; font-size: 1.05em;">👋 ยินดีต้อนรับสู่ SmartStudy (โหมดดูตัวอย่าง)</span>
                <span style="color: {text_muted}; font-size: 0.92em; margin-left: 8px;">คุณสามารถทดลองใช้งานและดูแดชบอร์ดได้อิสระ หากต้องการบันทึกการบ้านของคุณเอง กดเข้าสู่ระบบได้เลยครับ</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with b_col2:
        if st.button("🔑 ล็อกอิน / สมาชิก", key="top_login_btn", use_container_width=True, type="primary"):
            open_auth_modal()


# ==============================================================================
# หน้า 1: 📊 แดชบอร์ด & วิเคราะห์งาน
# ==============================================================================
if menu_selection == "📊 แดชบอร์ด & วิเคราะห์งาน":
    today_quote = "🌟 'ทุกหน้าหนังสือที่อ่านในวันนี้ กำลังพาคุณเข้าใกล้มหาวิทยาลัยในฝันมากขึ้นเรื่อยๆ สู้ๆ นะครับ! 💪'"

    st.markdown(
        f"""
        <div style="margin-bottom: 15px;">
            <h2 style="color: {theme_accent}; margin-bottom: 4px; font-weight: 700;">📊 แดชบอร์ดภาพรวม & วิเคราะห์งาน</h2>
            <div class="quote-box">{today_quote}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    df = get_task_data()

    if df.empty:
        st.info("👋 ยังไม่มีการบ้านในระบบ คุณสามารถคลิกเมนู '➕ เพิ่มการบ้านใหม่' หรือกดปุ่มด้านล่างเพื่อโหลดข้อมูลตัวอย่างมาทดลองเล่นได้ทันทีครับ")
        if st.button("🚀 โหลดการบ้านตัวอย่างทันที", type="primary"):
            database.seed_sample_data(user_id=active_user_id)
            st.rerun()
    else:
        # สรุปตัวเลขสถิติ
        total_tasks = len(df)
        completed_tasks = len(df[df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])])
        pending_df = df[~df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
        pending_tasks = len(pending_df)
        overdue_tasks = len(pending_df[pending_df["days_left"] < 0])
        pending_hours = pending_df["estimated_hours"].sum() if not pending_df.empty else 0.0
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

        # แสดงกล่อง Metric Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("งานทั้งหมด", f"{total_tasks} ชิ้น")
        m2.metric("ยังค้างอยู่", f"{pending_tasks} ชิ้น")
        m3.metric("เลยกำหนดส่ง", f"{overdue_tasks} ชิ้น", delta=-overdue_tasks if overdue_tasks > 0 else 0, delta_color="inverse")
        m4.metric("ทำเสร็จแล้ว", f"{completed_tasks} ชิ้น ({completion_rate}%)")
        m5.metric("เวลาที่ต้องใช้รวม", f"{pending_hours:.1f} ชม.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- กล่องแนะนำงานอันดับ 1 (Next Best Action Recommendation) ---
        top_task = planner.get_top_recommendation(df)
        if top_task:
            st.markdown("### 💡 แนะนำให้ทำชิ้นนี้ก่อนเป็นอันดับแรก")
            
            c_box, c_btn = st.columns([3.8, 1.2])
            with c_box:
                st.markdown(
                    f"""
                    <div class="recommendation-box">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.35em; font-weight: 700; color: {theme_accent};">
                                {top_task['urgency_badge']} : {top_task['title']}
                            </span>
                            <span class="subject-pill">{top_task['subject']}</span>
                        </div>
                        <p style="color: {text_main}; margin: 10px 0 8px 0; font-size: 1.05em; line-height: 1.5;">
                            <b>🎯 เหตุผลที่ควรเริ่มชิ้นนี้:</b> {top_task['recommendation_reason']}
                        </p>
                        <div style="color: {text_muted}; font-size: 0.92em; margin-top: 10px;">
                            📅 กำหนดส่ง: <b style="color: {text_main};">{top_task['due_date']}</b> ({top_task['deadline_status']}) &nbsp;|&nbsp; 
                            ⏱️ ใช้เวลา: <b style="color: {text_main};">{top_task['estimated_hours']} ชม.</b> &nbsp;|&nbsp; 
                            ⭐ ความสำคัญ: <b style="color: {text_main};">{top_task['importance']}/5</b> &nbsp;|&nbsp; 
                            📈 คะแนนความเร่งด่วน: <b style="color: {theme_accent};">{top_task['urgency_score']} แต้ม</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_btn:
                st.write("")
                st.write("")
                if st.button("ทำชิ้นนี้เสร็จแล้ว ✅", key=f"rec_done_{top_task['id']}", use_container_width=True, type="primary"):
                    if is_logged_in:
                        database.update_task_status(top_task['id'], "เสร็จสิ้นแล้ว", user_id=active_user_id)
                        st.success("ยินดีด้วย! ทำงานสำคัญเสร็จไปอีกหนึ่งชิ้นแล้ว 🎉")
                        st.rerun()
                    else:
                        st.info("🔒 โหมดดูตัวอย่าง: กรุณาเข้าสู่ระบบเพื่อบันทึกสถานะการบ้านของคุณครับ")
                        open_auth_modal()

        st.markdown("---")
        st.markdown("### 📈 แผนภูมิวิเคราะห์ภาระงาน (Visual Analytics)")

        col_chart1, col_chart2 = st.columns(2)

        # กราฟที่ 1: ชั่วโมงอ่านหนังสือแยกตามรายวิชา (แนวนอน 100% ตัวหนังสือคมชัด 100%)
        with col_chart1:
            st.markdown("##### 📚 ชั่วโมงที่ต้องใช้ตามรายวิชา (งานที่ยังค้างอยู่)")
            if not pending_df.empty:
                subject_data = (
                    pending_df.groupby("subject", as_index=False)["estimated_hours"]
                    .sum()
                    .rename(columns={"estimated_hours": "ชั่วโมง"})
                )
                
                chart_base = (
                    alt.Chart(subject_data)
                    .encode(
                        y=alt.Y(
                            "subject:N",
                            title=None,
                            sort="-x",
                            axis=alt.Axis(
                                labelAngle=0,
                                labelFontSize=13,
                                labelColor=text_main,
                                labelLimit=300
                            )
                        ),
                        x=alt.X(
                            "ชั่วโมง:Q",
                            title="ชั่วโมงที่ต้องใช้ (ชม.)",
                            axis=alt.Axis(
                                labelAngle=0,
                                titleFontSize=12,
                                titleColor=text_muted,
                                labelColor=text_muted
                            )
                        )
                    )
                )

                chart_bar = chart_base.mark_bar(
                    cornerRadiusTopRight=8,
                    cornerRadiusBottomRight=8,
                    color=theme_accent
                )

                chart_text = chart_base.mark_text(
                    align="left",
                    baseline="middle",
                    dx=6,
                    color=text_main,
                    fontSize=12,
                    fontWeight=600
                ).encode(
                    text=alt.Text("ชั่วโมง:Q", format=".1f")
                )

                raw_chart1 = (chart_bar + chart_text).properties(height=260)
                st.altair_chart(format_chart(raw_chart1), theme=None, use_container_width=True)
            else:
                st.success("🎉 เก่งมาก! เคลียร์งานหมดทุกวิชาแล้ว พักผ่อนได้เต็มที่เลยครับ ✨")

        # กราฟที่ 2: สัดส่วนสถานะงาน (โดนัท - แนวนอน ชัดเจน)
        with col_chart2:
            st.markdown("##### 🎯 สัดส่วนสถานะการบ้านทั้งหมด")
            status_list = []
            for _, r in df.iterrows():
                if r["status"] in ["Completed", "เสร็จสิ้นแล้ว"]:
                    status_list.append("เสร็จสิ้นแล้ว")
                elif r["days_left"] < 0:
                    status_list.append("เลยกำหนดส่ง")
                else:
                    status_list.append("รอดำเนินการ (ยังไม่ถึงกำหนด)")
            
            status_df = pd.DataFrame({"สถานะ": status_list})
            status_counts = status_df["สถานะ"].value_counts().reset_index()
            status_counts.columns = ["สถานะ", "จำนวน"]

            raw_chart2 = (
                alt.Chart(status_counts)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta("จำนวน:Q"),
                    color=alt.Color(
                        "สถานะ:N",
                        scale=alt.Scale(
                            domain=["เสร็จสิ้นแล้ว", "รอดำเนินการ (ยังไม่ถึงกำหนด)", "เลยกำหนดส่ง"],
                            range=["#10b981", "#3b82f6", "#ef4444"]
                        ),
                        legend=alt.Legend(
                            orient="bottom",
                            direction="horizontal",
                            title=None,
                            labelFontSize=12,
                            labelColor=text_main
                        )
                    ),
                    tooltip=["สถานะ", "จำนวน"]
                )
                .properties(height=260)
            )
            st.altair_chart(format_chart(raw_chart2), theme=None, use_container_width=True)

        # กราฟที่ 3: ระดับความเร่งด่วนของงานที่ยังค้าง (แนวนอน 100% ตัวหนังสือคมชัด)
        st.markdown("##### ⚡ ระดับความเร่งด่วนของงานที่ยังค้างส่ง")
        if not pending_df.empty:
            tier_df = (
                pending_df["urgency_tier_th"]
                .value_counts()
                .reindex(["วิกฤต / ด่วนที่สุด", "เร่งด่วนสูง", "ปานกลาง", "ทยอยทำได้"], fill_value=0)
                .reset_index()
            )
            tier_df.columns = ["ระดับความเร่งด่วน", "จำนวนงาน"]

            tier_base = (
                alt.Chart(tier_df)
                .encode(
                    y=alt.Y(
                        "ระดับความเร่งด่วน:N",
                        title=None,
                        sort=["วิกฤต / ด่วนที่สุด", "เร่งด่วนสูง", "ปานกลาง", "ทยอยทำได้"],
                        axis=alt.Axis(
                            labelAngle=0,
                            labelFontSize=13,
                            labelColor=text_main,
                            labelLimit=300
                        )
                    ),
                    x=alt.X(
                        "จำนวนงาน:Q",
                        title="จำนวนงาน (ชิ้น)",
                        axis=alt.Axis(
                            labelAngle=0,
                            tickMinStep=1,
                            titleFontSize=12,
                            titleColor=text_muted,
                            labelColor=text_muted
                        )
                    ),
                    color=alt.Color(
                        "ระดับความเร่งด่วน:N",
                        scale=alt.Scale(
                            domain=["วิกฤต / ด่วนที่สุด", "เร่งด่วนสูง", "ปานกลาง", "ทยอยทำได้"],
                            range=["#ef4444", "#f97316", "#eab308", "#10b981"]
                        ),
                        legend=None
                    )
                )
            )

            tier_bar = tier_base.mark_bar(
                cornerRadiusTopRight=8,
                cornerRadiusBottomRight=8
            )

            tier_text = tier_base.mark_text(
                align="left",
                baseline="middle",
                dx=6,
                color=text_main,
                fontSize=12,
                fontWeight=600
            ).encode(
                text=alt.Text("จำนวนงาน:Q")
            )

            raw_chart3 = (tier_bar + tier_text).properties(height=200)
            st.altair_chart(format_chart(raw_chart3), theme=None, use_container_width=True)


# ==============================================================================
# หน้า 2: ➕ เพิ่มการบ้านใหม่
# ==============================================================================
elif menu_selection == "➕ เพิ่มการบ้านใหม่":
    st.markdown(
        f"""
        <div style="margin-bottom: 15px;">
            <h2 style="color: {theme_accent}; margin-bottom: 2px; font-weight: 700;">➕ เพิ่มการบ้านหรือรายงานใหม่</h2>
            <p style="color: {text_muted}; margin-top: 0px;">กรอกรายละเอียดการบ้าน ระบบจะวิเคราะห์คำนวณความเร่งด่วนและจัดลำดับให้อัตโนมัติ</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not is_logged_in:
        st.info("💡 **คุณกำลังอยู่ในโหมดดูตัวอย่าง:** คุณสามารถทดลองกรอกฟอร์มได้ หากต้องการบันทึกเก็บเป็นบัญชีของตัวเอง กดเข้าสู่ระบบได้เลยครับ")
        if st.button("🔑 เข้าสู่ระบบเพื่อเริ่มบันทึกงานของฉัน", type="primary"):
            open_auth_modal()

    subject_options = [
        "คณิตศาสตร์", "ฟิสิกส์", "เคมี", "ชีววิทยา",
        "คอมพิวเตอร์ / เขียนโค้ด", "ภาษาอังกฤษ", "ภาษาไทย",
        "สังคม / ประวัติศาสตร์", "ศิลปะ / ดนตรี", "วิชาอื่นๆ (ระบุเอง)"
    ]

    with st.form("form_add_homework", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)

        with f_col1:
            title_input = st.text_input("ชื่องาน / รายละเอียดการบ้าน *", placeholder="เช่น การบ้านฟิสิกส์ บทที่ 2 เรื่องการเคลื่อนที่", max_chars=120)
            subject_selected = st.selectbox("เลือกรายวิชา *", subject_options)
            custom_subject_input = ""
            if subject_selected == "วิชาอื่นๆ (ระบุเอง)":
                custom_subject_input = st.text_input("ระบุชื่อวิชาเพิ่มเติม *", placeholder="เช่น ดาราศาสตร์ หรือ เศรษฐศาสตร์")

        with f_col2:
            min_allow_date = date.today() - timedelta(days=60)
            due_date_input = st.date_input("วันกำหนดส่ง *", value=date.today() + timedelta(days=2), min_value=min_allow_date)
            estimated_hours_input = st.number_input("เวลาที่คาดว่าจะใช้ทำ (ชั่วโมง) *", min_value=0.25, max_value=60.0, value=2.0, step=0.25)
            importance_input = st.select_slider(
                "ระดับความสำคัญ / คะแนนเก็บ *",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: {
                    1: "1 - เล็กน้อย (แบบฝึกหัดทบทวน ไม่เก็บคะแนน)",
                    2: "2 - ทั่วไป (การบ้านรายวันปกติ)",
                    3: "3 - ปานกลาง (งานกลุ่ม / ใบงานเก็บคะแนน)",
                    4: "4 - สำคัญมาก (รายงานใหญ่ / เตรียมสอบย่อย)",
                    5: "5 - วิกฤต/สำคัญที่สุด (โครงงานปลายภาค / สอบใหญ่)"
                }[x]
            )

        submit_btn = st.form_submit_button("💾 บันทึกการบ้าน", use_container_width=True, type="primary")

        if submit_btn:
            if not is_logged_in:
                st.warning("🔒 กรุณาเข้าสู่ระบบก่อนทำการบันทึกการบ้านของคุณครับ")
                open_auth_modal()
            else:
                actual_subject = custom_subject_input.strip() if subject_selected == "วิชาอื่นๆ (ระบุเอง)" else subject_selected
                
                validation_errors = []
                if not title_input or len(title_input.strip()) < 2:
                    validation_errors.append("กรุณาระบุชื่องานอย่างน้อย 2 ตัวอักษร")
                if subject_selected == "วิชาอื่นๆ (ระบุเอง)" and not actual_subject:
                    validation_errors.append("กรุณากรอกชื่อวิชาที่ต้องการระบุเอง")
                if estimated_hours_input <= 0:
                    validation_errors.append("เวลาที่ใช้ทำต้องมากกว่า 0 ชั่วโมง")

                if validation_errors:
                    for err in validation_errors:
                        st.error(f"⚠️ {err}")
                else:
                    try:
                        formatted_date = due_date_input.strftime("%Y-%m-%d")
                        database.add_task(
                            title=title_input.strip(),
                            subject=actual_subject,
                            due_date=formatted_date,
                            estimated_hours=float(estimated_hours_input),
                            importance=int(importance_input),
                            user_id=active_user_id
                        )
                        st.success(f"✅ บันทึกงาน '{title_input.strip()}' วิชา {actual_subject} สำเร็จแล้ว!")
                        st.info("💡 เลือกเมนู '📊 แดชบอร์ด' หรือ '📋 รายการการบ้าน' เพื่อดูข้อมูลที่อัปเดตได้เลยครับ")
                    except Exception as ex:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {ex}")


# ==============================================================================
# หน้า 3: 📋 รายการการบ้านทั้งหมด
# ==============================================================================
elif menu_selection == "📋 รายการการบ้านทั้งหมด":
    st.markdown(
        f"""
        <div style="margin-bottom: 15px;">
            <h2 style="color: {theme_accent}; margin-bottom: 2px; font-weight: 700;">📋 รายการการบ้านและการจัดการ</h2>
            <p style="color: {text_muted}; margin-top: 0px;">ค้นหา กรองข้อมูลรายวิชา และอัปเดตสถานะงานได้อย่างรวดเร็ว</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    df = get_task_data()

    if df.empty:
        st.info("ยังไม่มีข้อมูลการบ้านในระบบ สามารถเพิ่มการบ้านได้ที่เมนู '➕ เพิ่มการบ้านใหม่'")
    else:
        filter_col1, filter_col2, filter_col3 = st.columns([1.5, 1.5, 2])
        with filter_col1:
            status_filter = st.selectbox("กรองตามสถานะ", ["ทั้งหมด", "รอดำเนินการ", "เสร็จสิ้นแล้ว", "เลยกำหนดส่ง"])
        with filter_col2:
            all_subjects = ["ทั้งหมด"] + sorted(df["subject"].unique().tolist())
            subject_filter = st.selectbox("กรองตามวิชา", all_subjects)
        with filter_col3:
            search_text = st.text_input("🔍 ค้นหาตามชื่องาน...", placeholder="พิมพ์คำค้นหา...")

        filtered_df = df.copy()
        if status_filter == "รอดำเนินการ":
            filtered_df = filtered_df[~filtered_df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
        elif status_filter == "เสร็จสิ้นแล้ว":
            filtered_df = filtered_df[filtered_df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
        elif status_filter == "เลยกำหนดส่ง":
            filtered_df = filtered_df[(~filtered_df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])) & (filtered_df["days_left"] < 0)]

        if subject_filter != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df["subject"] == subject_filter]

        if search_text.strip():
            filtered_df = filtered_df[filtered_df["title"].str.contains(search_text.strip(), case=False, na=False)]

        st.caption(f"แสดงผล **{len(filtered_df)}** จากทั้งหมด {len(df)} รายการ")

        if filtered_df.empty:
            st.warning("ไม่พบการบ้านที่ตรงกับเงื่อนไขการค้นหา")
        else:
            for _, task in filtered_df.iterrows():
                task_id = int(task["id"])
                is_done = task["status"] in ["Completed", "เสร็จสิ้นแล้ว"]

                with st.container():
                    col_info, col_act1, col_act2 = st.columns([4, 1.1, 1])

                    with col_info:
                        title_style = f"<s style='color: {text_muted};'>{task['title']}</s>" if is_done else f"<span style='font-size: 1.12em; font-weight: 600; color: {text_main};'>{task['title']}</span>"
                        badge_text = "<span style='color: #10b981; font-weight: 600;'>✅ เสร็จสิ้นแล้ว</span>" if is_done else task["urgency_badge"]

                        st.markdown(
                            f"""
                            <div class="tech-card">
                                <div>
                                    {title_style} 
                                    <span class="subject-pill" style="margin-left: 8px;">{task['subject']}</span> 
                                    &nbsp; {badge_text}
                                </div>
                                <div style="color: {text_muted}; font-size: 0.9em; margin-top: 8px;">
                                    📅 ส่ง: <b>{task['due_date']}</b> ({task['deadline_status']}) &nbsp;&bull;&nbsp; 
                                    ⏱️ เวลา: <b>{task['estimated_hours']} ชม.</b> &nbsp;&bull;&nbsp; 
                                    ⭐ สำคัญ: <b>{task['importance']}/5</b> &nbsp;&bull;&nbsp; 
                                    📈 ความเร่งด่วน: <b style="color: {theme_accent};">{task['urgency_score']}</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with col_act1:
                        st.write("")
                        if is_done:
                            if st.button("↩️ ทำใหม่", key=f"reopen_{task_id}", use_container_width=True):
                                if is_logged_in:
                                    database.update_task_status(task_id, "รอดำเนินการ", user_id=active_user_id)
                                    st.rerun()
                                else:
                                    st.info("🔒 เข้าสู่ระบบเพื่อจัดการงาน")
                                    open_auth_modal()
                        else:
                            if st.button("✅ เสร็จแล้ว", key=f"done_{task_id}", use_container_width=True):
                                if is_logged_in:
                                    database.update_task_status(task_id, "เสร็จสิ้นแล้ว", user_id=active_user_id)
                                    st.rerun()
                                else:
                                    st.info("🔒 เข้าสู่ระบบเพื่อจัดการงาน")
                                    open_auth_modal()

                    with col_act2:
                        st.write("")
                        if st.button("🗑️ ลบ", key=f"del_{task_id}", use_container_width=True):
                            if is_logged_in:
                                database.delete_task(task_id, user_id=active_user_id)
                                st.rerun()
                            else:
                                st.info("🔒 เข้าสู่ระบบเพื่อจัดการงาน")
                                open_auth_modal()


# ==============================================================================
# หน้า 5: ⏱️ โหมดจับเวลาโฟกัส (Pomodoro)
# ==============================================================================
elif menu_selection == "⏱️ โหมดจับเวลาโฟกัส (Pomodoro)":
    st.markdown(
        f"""
        <div style="margin-bottom: 15px;">
            <h2 style="color: {theme_accent}; margin-bottom: 2px; font-weight: 700;">⏱️ นาฬิกาจับเวลาโฟกัส (Pomodoro Focus Timer)</h2>
            <p style="color: {text_muted}; margin-top: 0px;">ใช้เทคนิค Pomodoro โฟกัสอ่านหนังสือทีละเซสชันอย่างมีความสุขและไม่เหนื่อยล้า</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_timer, col_guide = st.columns([2, 1])

    with col_timer:
        timer_mode = st.radio(
            "เลือกระยะเวลาเซสชัน",
            ["โฟกัส 25 นาที (แนะนำ)", "ทำงานลึก 50 นาที (Deep Work)", "พักสั้น 5 นาที", "พักยาว 15 นาที"],
            horizontal=True
        )

        mode_minutes = {
            "โฟกัส 25 นาที (แนะนำ)": 25,
            "ทำงานลึก 50 นาที (Deep Work)": 50,
            "พักสั้น 5 นาที": 5,
            "พักยาว 15 นาที": 15
        }[timer_mode]

        st.markdown(
            f"""
            <div style="text-align: center; background-color: {bg_card}; border: 1.5px solid {border_color}; padding: 45px; border-radius: 20px; margin: 25px 0; box-shadow: 0 4px 14px rgba(0,0,0,0.04);">
                <h1 style="font-size: 4.5em; color: {theme_accent}; margin: 0; font-family: monospace; letter-spacing: 3px;">
                    {mode_minutes:02d}:00
                </h1>
                <p style="color: {text_muted}; margin-top: 12px; font-size: 1.15em;">
                    โหมด: {timer_mode}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info("💡 **คำแนะนำเพื่อการมีสมาธิ:** วางโทรศัพท์มือถือไว้ให้ห่างสายตา หยิบน้ำมาจิบ 1 แก้ว และทุ่มเทให้กับการบ้านชิ้นนี้เพียงชิ้นเดียว คุณทำได้แน่นอนครับ! 🌟")

    with col_guide:
        st.markdown("#### 🧠 3 เคล็ดลับเรียนดีแบบไม่เครียด")
        st.markdown(
            """
            1. **โฟกัสทีละเรื่อง (Single-tasking):** สมองมนุษย์ทำงานได้ดีที่สุดเมื่อทำทีละอย่าง อย่าเปิดโทรศัพท์สลับไปมา
            2. **ซอยเป้าหมายให้เล็กลง:** แทนที่จะคิดว่าจะอ่าน 5 ชั่วโมง ให้ตั้งเป้าแค่ "อ่านจบใน 25 นาทีนี้" จะเริ่มต้นได้ง่ายกว่ามาก
            3. **พักผ่อนอย่างมีคุณภาพ:** เมื่อหมดเวลาโฟกัส ให้ลุกขึ้นยืดเส้นยืดสาย ดื่มน้ำ หรือมองออกไปนอกหน้าต่างเพื่อพักสายตา
            """
        )
