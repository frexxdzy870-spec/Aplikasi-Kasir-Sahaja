import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import requests

# --- MASUKKAN URL /exec YANG BARU SETELAH RE-DEPLOY ---
URL_API = "https://script.google.com/macros/s/AKfycbxouRTgn9MBSZjdYS04fbIYApLwX5p3uJ49BaoMVEI3nwDleKAGwrQPSDzr_o-JOhZXag/exec"
NAMA_FILE_LOGO = "logo_kedai.png"

st.set_page_config(page_title="POS Sahaja v3.5.1", layout="wide")

# CSS Tetap Sama
st.markdown("""<style>html, body, [class*="st-"], div, p, h1, h2, h3, span, label { color: #ffffff !important; }.stApp { background-color: #121212 !important; }div.stButton > button { background-color: #800000 !important; color: white !important; border-radius: 12px !important; height: 3.5rem !important; width: 100%; border: none; }[data-testid="stSidebar"] { background-color: #4a0404 !important; }</style>""", unsafe_allow_html=True)

def get_cloud_data():
    try:
        r = requests.get(URL_API, timeout=10)
        return r.json()
    except:
        return {"produk": [], "penjualan": []}

def send_to_cloud(data):
    try:
        # Menambahkan header agar lebih stabil
        r = requests.post(URL_API, json=data, timeout=15)
        return r.status_code == 200
    except:
        return False

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

# --- LOGIN ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        if os.path.exists(NAMA_FILE_LOGO): st.image(NAMA_FILE_LOGO, use_container_width=True)
        user = st.selectbox("Pilih Kasir", ["Pilih Nama...", "Ferdi", "Obi", "Tiara"])
        if st.button("Masuk"):
            if user != "Pilih Nama...":
                st.session_state.logged_in = True
                st.session_state.employee_name = user
                now = datetime.now()
                send_to_cloud({"target": "absensi", "nama": user, "status": "MASUK", "jam": now.strftime("%H:%M"), "shift": "Pagi" if now.hour < 15 else "Malam", "tanggal": now.strftime("%d-%m-%Y")})
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"Kasir: **{st.session_state.employee_name}**")
    menu = st.radio("Menu", ["🛒 Kasir", "📦 Stok", "📊 Laporan"])
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

data_cloud = get_cloud_data()

# --- KASIR ---
if menu == "🛒 Kasir":
    st.title("🛒 Kasir Utama")
    df_p = pd.DataFrame(data_cloud['produk'])
    
    if not df_p.empty:
        c1, c2 = st.columns([2, 1])
        with c1: p_pilih = st.selectbox("Pilih Menu", df_p['name'].tolist())
        with c2: qty = st.number_input("Qty", min_value=1, value=1)
        if st.button("➕ Tambah"):
            info = df_p[df_p['name'] == p_pilih].iloc[0]
            st.session_state.cart.append({"Item": p_pilih, "Harga": info['price'], "Qty": qty, "Subtotal": info['price']*qty})
            st.rerun()

    if st.session_state.cart:
        for idx, item in enumerate(st.session_state.cart):
            cols = st.columns([3, 1, 1])
            cols[0].write(f"{item['Item']} x{item['Qty']}")
            cols[1].write(f"Rp{item['Subtotal']:,.0f}")
            if cols[2].button("❌", key=f"del_{idx}"):
                st.session_state.cart.pop(idx)
                st.rerun()
        
        total = sum(i['Subtotal'] for i in st.session_state.cart)
        st.header(f"Total: Rp {total:,.0f}")
        pay = st.radio("Metode", ["Cash", "QRIS"], horizontal=True)
        
        if st.button("✅ SELESAIKAN PEMBAYARAN"):
            with st.spinner('Menyimpan data...'):
                items_txt = ", ".join([f"{i['Item']}x{i['Qty']}" for i in st.session_state.cart])
                success = send_to_cloud({
                    "target": "penjualan", 
                    "tanggal": datetime.now().strftime("%d-%m %H:%M"),
                    "kasir": st.session_state.employee_name, 
                    "items": items_txt,
                    "metode": pay, 
                    "total": total
                })
                if success:
                    st.session_state.cart = []
                    st.success("DATA BERHASIL MASUK KE GOOGLE SHEETS!")
                    st.balloons()
                    # Pakai st.button untuk refresh manual jika perlu
                else:
                    st.error("GAGAL SIMPAN! Cek Izin Google Apps Script kamu (Who has access: Anyone)")

# --- STOK ---
elif menu == "📦 Stok":
    st.title("📦 Stok")
    with st.form("add"):
        n, p = st.text_input("Nama"), st.number_input("Harga", min_value=0)
        k = st.selectbox("Kategori", ["MINUMAN", "MAKANAN", "JAJANAN"])
        if st.form_submit_button("Simpan"):
            send_to_cloud({"target": "produk", "nama_produk": n, "harga": p, "kategori": k})
            st.rerun()
    st.dataframe(pd.DataFrame(data_cloud['produk']), use_container_width=True)

# --- LAPORAN ---
elif menu == "📊 Laporan":
    st.title("📊 Laporan")
    st.dataframe(pd.DataFrame(data_cloud['penjualan']), use_container_width=True)
