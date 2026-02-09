import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Dompet Falah", page_icon="💸", layout="wide")

# --- 2. LOGIC NOTIFIKASI (FLASH MESSAGE) ---
# Ini ditaruh paling atas biar dieksekusi pertama kali setelah refresh
if 'sukses' in st.session_state and st.session_state.sukses:
    st.toast("✅ Data Berhasil Masuk! Form sudah bersih.", icon='🚀')
    # Matikan statusnya biar pas refresh berikutnya gak muncul lagi
    st.session_state.sukses = False

# --- 3. KONEKSI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    """Ambil data fresh tanpa cache (ttl=0)"""
    try:
        df = conn.read(worksheet="Sheet1", usecols=list(range(6)), ttl=0).dropna(how="all")
        # Cleaning tipe data biar grafik gak error
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['Tanggal', 'Akun', 'Kategori', 'Jenis', 'Total', 'Ket'])

def submit_data():
    """Fungsi ini jalan di background saat tombol ditekan"""
    try:
        # 1. Ambil data dari Widget (Inputan User)
        new_entry = pd.DataFrame([{
            'Tanggal': st.session_state.widget_date.strftime("%Y-%m-%d"),
            'Akun': st.session_state.widget_wallet,
            'Kategori': st.session_state.widget_tipe,
            'Jenis': st.session_state.widget_jenis,
            'Total': st.session_state.widget_nominal,
            'Ket': st.session_state.widget_ket
        }])

        # 2. Gabung dengan data lama & Update ke Google Sheets
        df_old = get_data()
        df_updated = pd.concat([df_old, new_entry], ignore_index=True)
        conn.update(worksheet="Sheet1", data=df_updated)
        
        # 3. SET SIGNAL SUKSES ("Titip Pesan")
        # Kita kasih tau session state: "Nanti pas reload, tolong munculin toast ya"
        st.session_state.sukses = True
        
    except Exception as e:
        st.error(f"Error: {e}")

# --- 4. UI APLIKASI ---
st.title("💸 Dompet Falah")

tab_input, tab_dash = st.tabs(["➕ Input Data", "📊 Dashboard"])

# === TAB 1: INPUT TRANSAKSI ===
with tab_input:
    # Logic Sticky Date (Biar tanggal gak reset ke hari ini terus)
    if 'date_default' not in st.session_state:
        st.session_state.date_default = date.today()

    def update_date_session():
        st.session_state.date_default = st.session_state.widget_date

    col_tgl, col_dummy = st.columns([1, 2])
    with col_tgl:
        st.date_input(
            "Tanggal Transaksi", 
            value=st.session_state.date_default,
            key='widget_date', 
            on_change=update_date_session
        )

    # FORM INPUT (clear_on_submit=True bikin form jadi bersih otomatis)
    with st.form("form_utama", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Wallet", ["OCTO", "Mandiri", "Shopeepay", "Dana", "Cash"], key='widget_wallet')
        with c2:
            # key='widget_tipe' penting buat logic di bawah
            st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key='widget_tipe')
        
        # Logic Dropdown Berubah sesuai Tipe
        # Kita pakai session_state.get karena saat pertama load, widget belum ada isinya
        tipe_saat_ini = st.session_state.get('widget_tipe', "Pengeluaran")
        
        if tipe_saat_ini == "Pemasukan":
             opts = ["Gaji", "Bonus", "Freelance", "Refund"]
        else:
             opts = ["Makan", "Transport", "Kebutuhan Kos", "Belanja", "Tagihan", "Hiburan", "Sedekah", "Lainnya"]
        
        st.selectbox("Kategori Detail", opts, key='widget_jenis')
        st.number_input("Nominal (Rp)", min_value=0, step=5000, key='widget_nominal')
        st.text_input("Keterangan", key='widget_ket', placeholder="Contoh: Nasi Padang")

        # TOMBOL SAKTI
        # on_click=submit_data artinya: Jalankan fungsi submit dulu, baru reload halaman
        st.form_submit_button("Simpan Data 💾", on_click=submit_data)

# === TAB 2: DASHBOARD ===
with tab_dash:
    df = get_data()
    
    if not df.empty:
        # Tambah kolom bulan/tahun virtual
        df['Bulan'] = df['Tanggal'].dt.month_name()
        df['Tahun'] = df['Tanggal'].dt.year
        
        # Auto-select filter berdasarkan data TERAKHIR yang diinput
        last_row = df.iloc[-1]
        try:
            # Coba cari index bulan terakhir
            idx_bln = list(df['Bulan'].unique()).index(last_row['Bulan'])
            idx_thn = list(df['Tahun'].unique()).index(last_row['Tahun'])
        except:
            idx_bln = 0
            idx_thn = 0

        c_fil1, c_fil2 = st.columns(2)
        with c_fil1:
            pilih_bulan = st.selectbox("Filter Bulan", df['Bulan'].unique(), index=idx_bln)
        with c_fil2:
            pilih_tahun = st.selectbox("Filter Tahun", df['Tahun'].unique(), index=idx_thn)

        # Tampilkan Data sesuai Filter
        view = df[(df['Bulan'] == pilih_bulan) & (df['Tahun'] == pilih_tahun)]
        
        if not view.empty:
            # 1. Ringkasan Angka
            inc = view[view['Kategori'] == 'Pemasukan']['Total'].sum()
            out = view[view['Kategori'] == 'Pengeluaran']['Total'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Pemasukan", f"{inc:,.0f}")
            m2.metric("Pengeluaran", f"{out:,.0f}")
            m3.metric("Sisa", f"{inc-out:,.0f}", delta="Net Cashflow")
            
            st.divider()
            
            # 2. Grafik Donut (Khusus Pengeluaran)
            st.subheader(f"Pengeluaran {pilih_bulan} {pilih_tahun}")
            view_out = view[view['Kategori'] == 'Pengeluaran']
            
            if not view_out.empty:
                # Grouping biar rapi
                chart_data = view_out.groupby('Jenis')['Total'].sum().reset_index()
                
                fig = px.pie(chart_data, values='Total', names='Jenis', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
                
                # 3. Tabel Detail
                st.caption("Rincian Transaksi:")
                st.dataframe(
                    view[['Tanggal', 'Jenis', 'Total', 'Ket']].sort_values('Tanggal', ascending=False), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Bulan ini belum ada pengeluaran. Hemat pangkal kaya! 🤑")
        else:
            st.warning("Data tidak ditemukan untuk periode ini.")
    else:
        st.info("Database masih kosong.")
