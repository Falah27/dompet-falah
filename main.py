import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- CONFIG ---
st.set_page_config(page_title="Dompet Falah", page_icon="💸", layout="wide")

# Koneksi
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---
def get_data():
    # Baca data, handle error jika kosong
    try:
        df = conn.read(worksheet="Sheet1", usecols=list(range(6)), ttl=0).dropna(how="all")
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except:
        return pd.DataFrame(columns=['Tanggal', 'Akun', 'Kategori', 'Jenis', 'Total', 'Ket'])

# Sticky Date Logic
if 'sticky_date' not in st.session_state:
    st.session_state.sticky_date = date.today()

def update_date():
    st.session_state.sticky_date = st.session_state.date_picker

# --- UI ---
st.title("💸 Dompet Falah")

# Tab Navigasi
tab1, tab2 = st.tabs(["➕ Input", "📊 Dashboard"])

# === TAB 1: INPUT ===
with tab1:
    c_date, c_info = st.columns([1,2])
    with c_date:
        selected_date = st.date_input(
            "Tanggal", 
            value=st.session_state.sticky_date,
            key='date_picker',
            on_change=update_date
        )
    with c_info:
        st.info(f"Input Data: **{selected_date.strftime('%d %B %Y')}**")

    with st.form("input_form", clear_on_submit=True):
        # Baris 1
        col1, col2 = st.columns(2)
        with col1:
            wallet = st.selectbox("Wallet", ["BCA", "Mandiri", "GoPay", "Cash", "Lainnya"])
        with col2:
            tipe = st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True)

        # Baris 2 (Dynamic Dropdown)
        if tipe == "Pengeluaran":
            options = ["Makan", "Transport", "Kebutuhan Kos", "Belanja", "Tagihan", "Hiburan", "Sedekah", "Lainnya"]
        else:
            options = ["Gaji", "Bonus", "Freelance", "Refund"]

        kategori_detail = st.selectbox("Kategori Detail", options)

        # Baris 3
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        ket = st.text_input("Keterangan", placeholder="Contoh: Nasi Padang")

        if st.form_submit_button("Simpan Data 💾"):
            df_lama = get_data()
            data_baru = pd.DataFrame([{
                'Tanggal': selected_date.strftime("%Y-%m-%d"),
                'Akun': wallet,
                'Kategori': tipe,
                'Jenis': kategori_detail,
                'Total': nominal,
                'Ket': ket
            }])

            df_update = pd.concat([df_lama, data_baru], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_update)
            st.success("Data berhasil masuk Cloud! ☁️")

# === TAB 2: DASHBOARD ===
with tab2:
    df = get_data()
    if not df.empty:
        # Filter Bulan & Tahun (Auto-generated)
        df['Bulan'] = df['Tanggal'].dt.month_name()
        df['Tahun'] = df['Tanggal'].dt.year

        c_filter1, c_filter2 = st.columns(2)
        with c_filter1:
            pilih_bulan = st.selectbox("Bulan", df['Bulan'].unique())
        with c_filter2:
            pilih_tahun = st.selectbox("Tahun", df['Tahun'].unique())

        # Filter Data
        view = df[(df['Bulan'] == pilih_bulan) & (df['Tahun'] == pilih_tahun)]

        # Scorecard
        out = view[view['Kategori'] == 'Pengeluaran']['Total'].sum()
        inc = view[view['Kategori'] == 'Pemasukan']['Total'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Pemasukan", f"Rp {inc:,.0f}")
        m2.metric("Pengeluaran", f"Rp {out:,.0f}")
        m3.metric("Sisa", f"Rp {inc-out:,.0f}")

        st.divider()

        # Chart Donut (Plotly)
        st.subheader("Pengeluaran per Kategori")
        view_expense = view[view['Kategori'] == 'Pengeluaran']

        if not view_expense.empty:
            fig = px.pie(view_expense, values='Total', names='Jenis', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

            # Tabel Detail
            st.dataframe(view_expense[['Tanggal', 'Jenis', 'Total', 'Ket']].sort_values('Tanggal', ascending=False), use_container_width=True)
        else:
            st.warning("Belum ada pengeluaran di bulan ini.")
    else:
        st.info("Data masih kosong.")