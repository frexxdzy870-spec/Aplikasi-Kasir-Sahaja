import streamlit as st
import pandas as pd
from datetime import datetime
import os
from supabase import create_client, Client

# --- KONFIGURASI SUPABASE ---
# Isi dengan data dari Project Settings > API Supabase kamu
SUPABASE_URL = "https://obrbnenfojqdepqzxain.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9icmJuZW5mb2pxZGVwcXp4YWluIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2NDU2MDAsImV4cCI6MjA5MjIyMTYwMH0.Ef0uELb-CwYxlKpK_DggIrfX0NZDHiyEHTIcZmseyzk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

NAMA_FILE_LOGO = "logo_kedai.png"

st.set_page_config(page_title="POS Sahaja v4.0", layout="wide")

# --- CSS CUSTOM ---
st.markdown("""
    <style>
    html, body, [class*="st-"], div, p, h1, h2, h3, span, label { color: #ffffff !important; }
    .stApp { background-color: #121212 !important; }
    div.stButton > button { background-color: #800000 !important; color: white !important; border-radius: 12px !important; height: 3.5rem !important; width: 100%; border: none; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #4a0404 !important; }
    .stSelectbox div, .stTextInput input, .stNumberInput input { background-color: #1e1e1e !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

# --- HALAMAN LOGIN ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        if os.path.exists(NAMA_FILE_LOGO): st.image(NAMA_FILE_LOGO, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>🔐 Login Kasir</h2>", unsafe_allow_html=True)
        user = st.selectbox("Siapa yang bertugas?", ["Pilih Nama...", "Ferdi", "Obi", "Tiara"])
        if st.button("MASUK & ABSEN"):
            if user != "Pilih Nama...":
                st.session_state.logged_in = True
                st.session_state.employee_name = user
                # Absen ke Supabase
                now = datetime.now()
                supabase.table("attendance").insert({
                    "nama": user, "status": "MASUK", "jam": now.strftime("%H:%M"),
                    "shift": "Pagi" if now.hour < 15 else "Malam", "tanggal": now.strftime("%Y-%m-%d")
                }).execute()
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"### ☕ POS Sahaja\nUser: **{st.session_state.employee_name}**")
    menu = st.radio("Navigasi", ["🛒 Kasir", "📦 Manajemen Stok", "📊 Laporan Harian"])
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.cart = []
        st.rerun()

# --- MENU KASIR ---
if menu == "🛒 Kasir":
    st.title("🛒 Kasir Utama")
    
    # Ambil data produk dari Supabase
    res = supabase.table("products").select("*").execute()
    df_p = pd.DataFrame(res.data)
    
    if not df_p.empty:
        c1, c2 = st.columns([2, 1])
        with c1: p_pilih = st.selectbox("Pilih Menu", df_p['name'].tolist())
        with c2: qty = st.number_input("Jumlah", min_value=1, value=1)
        
        if st.button("➕ Tambah Ke Pesanan"):
            info = df_p[df_p['name'] == p_pilih].iloc[0]
            st.session_state.cart.append({
                "Item": p_pilih, "Harga": float(info['price']), 
                "Qty": qty, "Subtotal": float(info['price']) * qty
            })
            st.rerun()

    if st.session_state.cart:
        st.markdown("---")
        for idx, item in enumerate(st.session_state.cart):
            col_a, col_b, col_c = st.columns([3, 1, 0.5])
            col_a.write(f"**{item['Item']}** ({item['Qty']}x)")
            col_b.write(f"Rp{item['Subtotal']:,.0f}")
            if col_c.button("❌", key=f"del_{idx}"):
                st.session_state.cart.pop(idx)
                st.rerun()
        
        total = sum(i['Subtotal'] for i in st.session_state.cart)
        st.header(f"Total Bayar: Rp {total:,.0f}")
        
        metode = st.radio("Metode Pembayaran", ["Cash", "QRIS"], horizontal=True)
        if st.button("✅ SELESAIKAN PEMBAYARAN"):
            items_txt = ", ".join([f"{i['Item']}x{i['Qty']}" for i in st.session_state.cart])
            # Simpan ke Supabase
            try:
                supabase.table("sales").insert({
                    "kasir": st.session_state.employee_name,
                    "items": items_txt,
                    "metode": metode,
                    "total": total
                }).execute()
                
                st.success("TRANSAKSI BERHASIL DISIMPAN!")
                st.balloons()
                st.session_state.cart = []
                # Tunggu sebentar lalu refresh
            except Exception as e:
                st.error(f"Gagal simpan: {e}")

# --- MENU STOK ---
elif menu == "📦 Manajemen Stok":
    st.title("📦 Manajemen Stok")
    with st.form("tambah_produk", clear_on_submit=True):
        n = st.text_input("Nama Produk")
        p = st.number_input("Harga", min_value=0)
        k = st.selectbox("Kategori", ["MINUMAN", "MAKANAN", "JAJANAN"])
        if st.form_submit_button("Simpan Produk"):
            supabase.table("products").insert({"name": n, "price": p, "category": k}).execute()
            st.success("Produk berhasil ditambahkan!")
            st.rerun()

    # Tampilkan & Hapus Produk
    res = supabase.table("products").select("*").execute()
    df_list = pd.DataFrame(res.data)
    if not df_list.empty:
        st.dataframe(df_list[['name', 'price', 'category']], use_container_width=True)
        p_hapus = st.selectbox("Hapus Produk", df_list['name'].tolist())
        if st.button("🗑️ Hapus Permanen"):
            supabase.table("products").delete().eq("name", p_hapus).execute()
            st.rerun()

# --- MENU LAPORAN ---
elif menu == "📊 Laporan Harian":
    st.title("📊 Laporan Penjualan")
    res = supabase.table("sales").select("*").order('created_at', desc=True).execute()
    df_s = pd.DataFrame(res.data)
    if not df_s.empty:
        st.metric("Total Omzet", f"Rp {df_s['total'].sum():,.0f}")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.info("Belum ada transaksi hari ini.")
