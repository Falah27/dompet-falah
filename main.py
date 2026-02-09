import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Dompet Falah", page_icon="💸", layout="wide")

# --- 2. KONEKSI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    """Ambil data dari Google Sheets"""
    try:
        # ttl=0 biar gak nyimpen cache lama
        df = conn.read(worksheet="Sheet1", usecols=list(range(6)), ttl=0).dropna(how="all")
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['Tanggal', 'Akun', 'Kategori', 'Jenis', 'Total', 'Ket'])

def submit_data():
    """Fungsi Simpan Data (Action)"""
    try:
        # 1. Bungkus data inputan jadi DataFrame
        new_entry = pd.DataFrame([{
            'Tanggal': st.session_state.widget_date.strftime("%Y-%m-%d"),
            'Akun': st.session_state.widget_wallet,
            'Kategori': st.session_state.widget_tipe,
            'Jenis': st.session_state.widget_jenis,
            'Total': st.session_state.widget_nominal,
            'Ket': st.session_state.widget_ket
        }])

        # 2. Kirim ke Google Sheets (Background Process)
        df_old = get_data()
        df_updated = pd.concat([df_old, new_entry], ignore_index=True)
        conn.update(worksheet="Sheet1", data=df_updated)
        
        # 3. Simpan data barusan ke "Memori Sementara"
        st.session_state.data_barusan = new_entry
        st.session_state.sukses = True
        
        # 4. Hapus Cache
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. LOGIC NOTIFIKASI ---
if 'sukses' in st.session_state and st.session_state.sukses:
    st.toast("✅ Data Masuk! Grafik sudah update.", icon='🚀')

# --- 4. UI APLIKASI ---
st.title("💸 Dompet Falah")

tab_input, tab_dash = st.tabs(["➕ Input Data", "📊 Dashboard"])

# === TAB 1: INPUT ===
with tab_input:
    # Logic Sticky Date
    if 'date_default' not in st.session_state:
        st.session_state.date_default = date.today()

    def update_date_session():
        st.session_state.date_default = st.session_state.widget_date

    col_tgl, col_dummy = st.columns([1, 2])
    with col_tgl:
        st.date_input("Tanggal", value=st.session_state.date_default, key='widget_date', on_change=update_date_session)

    with st.form("form_utama", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            # --- UPDATE DISINI: LIST PEMBAYARAN BARU ---
            st.selectbox("Wallet", ["OCTO", "Mandiri", "Shopeepay", "Dana", "Cash"], key='widget_wallet')
        with c2:
            st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key='widget_tipe')
        
        # Opsi Kategori
        tipe = st.session_state.get('widget_tipe', "Pengeluaran")
        if tipe == "Pemasukan":
             opts = ["Gaji", "Bonus", "Freelance", "Refund"]
        else:
             opts = ["Makan", "Transport", "Kebutuhan Kos", "Belanja", "Tagihan", "Hiburan", "Sedekah", "Lainnya"]
        
        st.selectbox("Kategori Detail", opts, key='widget_jenis')
        st.number_input("Nominal (Rp)", min_value=0, step=5000, key='widget_nominal')
        st.text_input("Keterangan", key='widget_ket')

        # Tombol Submit
        st.form_submit_button("Simpan Data 💾", on_click=submit_data)

# === TAB 2: DASHBOARD ===
with tab_dash:
    # 1. Ambil Data dari Google Sheets
    df = get_data()
    
    # 2. LOGIC "OPTIMISTIC UI"
    if st.session_state.get('sukses') and 'data_barusan' in st.session_state:
        if not df.empty:
             df = pd.concat([df, st.session_state.data_barusan], ignore_index=True)
        else:
             df = st.session_state.data_barusan
        
        st.session_state.sukses = False 
    
    if not df.empty:
        # Konversi Ulang (Penting!)
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
        
        df['Bulan'] = df['Tanggal'].dt.month_name()
        df['Tahun'] = df['Tanggal'].dt.year
        
        # Filter Default
        last_row = df.iloc[-1]
        try:
            idx_bln = list(df['Bulan'].unique()).index(last_row['Bulan'])
            idx_thn = list(df['Tahun'].unique()).index(last_row['Tahun'])
        except:
            idx_bln = 0; idx_thn = 0

        c_fil1, c_fil2 = st.columns(2)
        with c_fil1:
            pilih_bulan = st.selectbox("Bulan", df['Bulan'].unique(), index=idx_bln)
        with c_fil2:
            pilih_tahun = st.selectbox("Tahun", df['Tahun'].unique(), index=idx_thn)

        # Filter View
        view = df[(df['Bulan'] == pilih_bulan) & (df['Tahun'] == pilih_tahun)]
        
        if not view.empty:
            # Scorecard
            inc = view[view['Kategori'] == 'Pemasukan']['Total'].sum()
            out = view[view['Kategori'] == 'Pengeluaran']['Total'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Masuk", f"{inc:,.0f}")
            m2.metric("Keluar", f"{out:,.0f}")
            m3.metric("Sisa", f"{inc-out:,.0f}")
            
            st.divider()
            
            # Grafik
            st.subheader(f"Pengeluaran {pilih_bulan}")
            view_out = view[view['Kategori'] == 'Pengeluaran']
            
            if not view_out.empty:
                chart_data = view_out.groupby('Jenis')['Total'].sum().reset_index()
                fig = px.pie(chart_data, values='Total', names='Jenis', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
                
                st.caption("Rincian Transaksi:")
                st.dataframe(view[['Tanggal', 'Jenis', 'Total', 'Ket']].sort_values('Tanggal', ascending=False), 
                             use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada pengeluaran.")
        else:
            st.warning("Data tidak ditemukan.")
    else:
        st.info("Database kosong.")
