import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import requests

# --- KONFIGURASI UTAMA ---
# GANTI URL DI BAWAH INI DENGAN URL DARI GOOGLE APPS SCRIPT KAMU
URL_ABSENSI = "https://script.google.com/macros/s/AKfycbwo9x5DLYIt83msjqG3BboOLO33LQA_xmvTcr8CtQdRlyzSgzFp8xWVpI02gadmKr0J_w/exec" 
NAMA_FILE_LOGO = "logo_kedai.png"

st.set_page_config(page_title="POS Sahaja v3.4", layout="wide")

# --- CSS CUSTOM: TEMA MAROON & FIX ANDROID ---
st.markdown("""
    <style>
    html, body, [class*="st-"], div, p, h1, h2, h3, span, label { color: #ffffff !important; }
    .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem; max-width: 95%; }
    .stApp { background-color: #121212 !important; }
    
    div.stButton > button {
        background-color: #800000 !important; color: white !important;
        border-radius: 12px !important; height: 3.5rem !important;
        width: 100% !important; font-size: 18px !important; border: none !important;
    }
    
    .logout-btn button { background-color: #333333 !important; height: 2.5rem !important; }
    .delete-btn button { background-color: #ff4d4d !important; height: 3rem !important; }
    .reset-btn button { background-color: #ff1a1a !important; height: 3rem !important; }

    [data-testid="stSidebar"] { background-color: #4a0404 !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    h1, h2, h3 { color: #ff4d4d !important; }
    
    .stSelectbox div, .stTextInput input, .stNumberInput input {
        background-color: #1e1e1e !important; color: white !important; border: 1px solid #4a0404 !important;
    }

    .kembalian-box {
        padding: 20px; background-color: #1e1e1e; border-left: 10px solid #800000;
        border-radius: 10px; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI ABSENSI (KE SPREADSHEET) ---
def kirim_absensi(nama, status):
    now = datetime.now()
    jam = now.strftime("%H:%M:%S")
    tgl = now.strftime("%d-%m-%Y")
    hour = now.hour
    shift = "Pagi" if 6 <= hour < 15 else "Malam"
    
    data = {"nama": nama, "status": status, "jam": jam, "shift": shift, "tanggal": tgl}
    try:
        requests.post(URL_ABSENSI, json=data)
    except:
        pass # Tetap jalan meski internet absen bermasalah

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('pos_maroon.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, category TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, employee TEXT, total REAL, items TEXT, payment_method TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

def get_data(query):
    conn = sqlite3.connect('pos_maroon.db')
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

init_db()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.employee_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- HALAMAN LOGIN & ABSEN MASUK ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists(NAMA_FILE_LOGO):
            st.image(NAMA_FILE_LOGO, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>🔐 Login & Absen</h2>", unsafe_allow_html=True)
        user = st.selectbox("Siapa yang bertugas?", ["Pilih Nama...", "Ferdi", "Obi", "Tiara"])
        if st.button("Masuk & Mulai Shift"):
            if user != "Pilih Nama...":
                st.session_state.logged_in = True
                st.session_state.employee_name = user
                kirim_absensi(user, "MASUK")
                st.success(f"Berhasil Login! Selamat bekerja {user}.")
                st.rerun()
            else:
                st.error("Pilih nama dulu!")
    st.stop()

# --- SIDEBAR & ABSEN PULANG ---
with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO): st.image(NAMA_FILE_LOGO, width=100)
    st.markdown(f"### ☕ POS SAHAJA\nUser: **{st.session_state.employee_name}**")
    st.markdown("---")
    menu = st.radio("Menu Utama:", ["🛒 Kasir Utama", "📦 Stok & Produk", "📊 Laporan & Reset"])
    st.markdown("---")
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Log Out & Selesai Shift"):
        kirim_absensi(st.session_state.employee_name, "PULANG")
        st.session_state.logged_in = False
        st.session_state.cart = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- MENU: KASIR ---
if menu == "🛒 Kasir Utama":
    st.title("🛒 Kasir Utama")
    df_p = get_data("SELECT * FROM products")
    if not df_p.empty:
        c1, c2 = st.columns([2, 1])
        with c1: p_pilih = st.selectbox("Pilih Produk", df_p['name'].tolist())
        with c2: qty = st.number_input("Qty", min_value=1, value=1)
        if st.button("➕ Tambah"):
            info = df_p[df_p['name'] == p_pilih].iloc[0]
            st.session_state.cart.append({"Item": p_pilih, "Harga": info['price'], "Qty": qty, "Subtotal": info['price'] * qty})
            st.toast("Ditambahkan!")

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart)[['Item', 'Qty', 'Subtotal']])
        total = sum(i['Subtotal'] for i in st.session_state.cart)
        st.markdown(f"## Total: Rp {total:,.0f}")
        pay = st.radio("Bayar via:", ["Cash", "QRIS"], horizontal=True)
        if pay == "Cash":
            terima = st.number_input("Uang Diterima", min_value=0)
            if terima > 0:
                kembali = terima - total
                color = "#00ff00" if kembali >= 0 else "#ff4d4d"
                st.markdown(f'<div class="kembalian-box"><h3>Kembalian:</h3><h1 style="color:{color};">Rp {abs(kembali):,.0f}</h1></div>', unsafe_allow_html=True)
        
        if st.button("✅ Selesaikan Transaksi"):
            conn = sqlite3.connect('pos_maroon.db')
            items_str = ", ".join([f"{i['Item']}x{i['Qty']}" for i in st.session_state.cart])
            conn.execute("INSERT INTO sales (employee, total, items, payment_method, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (st.session_state.employee_name, total, items_str, pay, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit(); conn.close()
            st.session_state.cart = []
            st.success("Tersimpan!"); st.balloons(); st.rerun()

# --- MENU: STOK ---
elif menu == "📦 Stok & Produk":
    st.title("📦 Inventaris")
    with st.expander("➕ Tambah Produk"):
        with st.form("add_f", clear_on_submit=True):
            n, p = st.text_input("Nama"), st.number_input("Harga", min_value=0)
            c = st.selectbox("Kategori", ["MINUMAN", "MAKANAN", "JAJANAN"])
            if st.form_submit_button("Simpan"):
                conn = sqlite3.connect('pos_maroon.db')
                conn.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", (n, p, c))
                conn.commit(); conn.close(); st.rerun()
    df_list = get_data("SELECT name as Nama, price as Harga, category as Kategori FROM products")
    st.dataframe(df_list, use_container_width=True, hide_index=True)
    if not df_list.empty:
        h = st.selectbox("Hapus Produk:", df_list['Nama'].tolist())
        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
        if st.button("Hapus Permanen"):
            conn = sqlite3.connect('pos_maroon.db')
            conn.execute("DELETE FROM products WHERE name = ?", (h,))
            conn.commit(); conn.close(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- MENU: LAPORAN ---
elif menu == "📊 Laporan & Reset":
    st.title("📊 Laporan")
    df_s = get_data("SELECT * FROM sales")
    df_p = get_data("SELECT name, category FROM products")
    if not df_s.empty:
        total_omzet = df_s['total'].sum()
        st.metric("Omzet Hari Ini", f"Rp {total_omzet:,.0f}")
        pengeluaran = st.number_input("Pengeluaran (Rp):", min_value=0)
        
        counts = {}
        for row in df_s['items']:
            for p in row.split(", "):
                try: name, qty = p.rsplit("x", 1); counts[name] = counts.get(name, 0) + int(qty)
                except: continue

        msg = f"*Laporan Keuangan Shift Pagi*\nTanggal: {datetime.now().strftime('%d %B %Y')}\n\n"
        for cat in ["MINUMAN", "MAKANAN", "JAJANAN"]:
            msg += f"*{cat}*\n"
            for it in df_p[df_p['category'] == cat]['name'].tolist():
                msg += f"- {it} : {counts.get(it, 0)}\n"
            msg += "\n"
        msg += f"*Total Omzet: Rp {total_omzet:,.0f}*\n*Pengeluaran: Rp {pengeluaran:,.0f}*\n*Total Bersih: Rp {total_omzet-pengeluaran:,.0f}*"
        
        st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold;">🚀 KIRIM WA</button></a>', unsafe_allow_html=True)
        st.dataframe(df_s[['timestamp', 'employee', 'payment_method', 'items', 'total']], use_container_width=True)
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("⚠️ RESET DATA"):
            conn = sqlite3.connect('pos_maroon.db'); conn.execute("DELETE FROM sales"); conn.commit(); conn.close(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
