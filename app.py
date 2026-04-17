import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import requests

# --- KONFIGURASI ---
# GANTI DENGAN URL /exec MILIKMU
URL_API = "https://script.google.com/macros/s/AKfycbzBWC2LRAY-vmxLa6Ag1q2yeHKZS0uQzHX_LbPPIPlcv3chWGVbqsiMWMIJFYxv_55OEA/exec"
NAMA_FILE_LOGO = "logo_kedai.png"

st.set_page_config(page_title="POS Sahaja v3.5", layout="wide")

# --- CSS CUSTOM (MAROON & ANTI-DARK MODE ANDROID) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], div, p, h1, h2, h3, span, label { color: #ffffff !important; }
    .stApp { background-color: #121212 !important; }
    div.stButton > button { background-color: #800000 !important; color: white !important; border-radius: 12px !important; height: 3.5rem !important; border: none !important; width: 100%; }
    [data-testid="stSidebar"] { background-color: #4a0404 !important; }
    .stSelectbox div, .stTextInput input, .stNumberInput input { background-color: #1e1e1e !important; color: white !important; }
    .cart-box { border: 1px solid #4a0404; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI CLOUD ---
@st.cache_data(ttl=2) # Refresh data tiap 2 detik
def get_cloud_data():
    try:
        r = requests.get(URL_API)
        return r.json()
    except:
        return {"produk": [], "penjualan": []}

def send_to_cloud(data):
    try:
        requests.post(URL_API, json=data)
        return True
    except:
        return False

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.employee_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- LOGIN & ABSENSI ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        if os.path.exists(NAMA_FILE_LOGO): st.image(NAMA_FILE_LOGO, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>🔐 Login & Absen</h2>", unsafe_allow_html=True)
        user = st.selectbox("Pilih Nama Kasir", ["Pilih Nama...", "Ferdi", "Obi", "Tiara"])
        if st.button("Masuk"):
            if user != "Pilih Nama...":
                st.session_state.logged_in = True
                st.session_state.employee_name = user
                now = datetime.now()
                send_to_cloud({
                    "target": "absensi", "nama": user, "status": "MASUK",
                    "jam": now.strftime("%H:%M"), "shift": "Pagi" if now.hour < 15 else "Malam",
                    "tanggal": now.strftime("%d-%m-%Y")
                })
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### ☕ POS SAHAJA\nKasir: **{st.session_state.employee_name}**")
    menu = st.radio("Menu:", ["🛒 Kasir Utama", "📦 Stok & Produk", "📊 Laporan"])
    if st.button("🚪 Logout & Selesai Shift"):
        now = datetime.now()
        send_to_cloud({
            "target": "absensi", "nama": st.session_state.employee_name, "status": "PULANG",
            "jam": now.strftime("%H:%M"), "shift": "Pagi" if now.hour < 15 else "Malam",
            "tanggal": now.strftime("%d-%m-%Y")
        })
        st.session_state.logged_in = False
        st.rerun()

data_cloud = get_cloud_data()

# --- MENU KASIR (FITUR EDIT KERANJANG) ---
if menu == "🛒 Kasir Utama":
    st.title("🛒 Kasir Utama")
    df_p = pd.DataFrame(data_cloud['produk'])
    
    if not df_p.empty:
        c1, c2 = st.columns([2, 1])
        with c1: p_pilih = st.selectbox("Pilih Menu", df_p['name'].tolist())
        with c2: qty = st.number_input("Qty", min_value=1, value=1)
        
        if st.button("➕ Tambah"):
            info = df_p[df_p['name'] == p_pilih].iloc[0]
            st.session_state.cart.append({
                "id": len(st.session_state.cart), 
                "Item": p_pilih, "Harga": info['price'], 
                "Qty": qty, "Subtotal": info['price'] * qty
            })
            st.rerun()

    if st.session_state.cart:
        st.markdown("---")
        st.subheader("📝 Daftar Pesanan (Bisa Edit/Hapus)")
        
        # Loop Keranjang untuk Fitur Hapus/Edit
        for idx, item in enumerate(st.session_state.cart):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{item['Item']}** ({item['Qty']} x Rp{item['Harga']:,.0f})")
            col_b.write(f"Rp{item['Subtotal']:,.0f}")
            if col_c.button("❌", key=f"del_{idx}"):
                st.session_state.cart.pop(idx)
                st.rerun()
        
        st.markdown("---")
        total = sum(i['Subtotal'] for i in st.session_state.cart)
        st.header(f"Total: Rp {total:,.0f}")
        
        pay = st.radio("Metode Pembayaran:", ["Cash", "QRIS"], horizontal=True)
        if pay == "Cash":
            terima = st.number_input("Uang Diterima", min_value=0)
            if terima >= total:
                st.success(f"Kembalian: Rp {terima - total:,.0f}")

        if st.button("✅ Proses & Simpan Transaksi"):
            items_txt = ", ".join([f"{i['Item']}x{i['Qty']}" for i in st.session_state.cart])
            success = send_to_cloud({
                "target": "penjualan", "tanggal": datetime.now().strftime("%d-%m %H:%M"),
                "kasir": st.session_state.employee_name, "items": items_txt,
                "metode": pay, "total": total
            })
            if success:
                st.session_state.cart = []
                st.success("Tersimpan!")
                st.rerun()

# --- MENU STOK ---
elif menu == "📦 Stok & Produk":
    st.title("📦 Pengaturan Menu")
    with st.form("add_form"):
        n = st.text_input("Nama Produk")
        p = st.number_input("Harga", min_value=0)
        k = st.selectbox("Kategori", ["MINUMAN", "MAKANAN", "JAJANAN"])
        if st.form_submit_button("Simpan ke Cloud"):
            send_to_cloud({"target": "produk", "nama_produk": n, "harga": p, "kategori": k})
            st.success("Tersimpan!")
            st.rerun()
    
    st.write("### Daftar Produk di Cloud")
    st.dataframe(pd.DataFrame(data_cloud['produk']), use_container_width=True)

# --- MENU LAPORAN ---
elif menu == "📊 Laporan":
    st.title("📊 Laporan Penjualan")
    df_s = pd.DataFrame(data_cloud['penjualan'])
    if not df_s.empty:
        st.metric("Total Omzet", f"Rp {df_s['total'].astype(float).sum():,.0f}")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.info("Belum ada data.")
