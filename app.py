import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import calendar

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Budget Bento Pro v12", page_icon="🍱", layout="wide")

# --- KONFIGURASI KATEGORI ---
KATEGORI_PEMASUKAN = ["Gaji", "Bonus", "Hadiah", "Investasi", "Penjualan", "Lainnya"]
KATEGORI_PENGELUARAN = ["Makan", "Jajan", "Belanja", "Hiburan", "Transport", "Kesehatan", "Tagihan", "Amal", "Lainnya"]
METODE_PEMBAYARAN = ["Cash", "Livin (Mandiri)", "Octo (CIMB)", "DANA", "Shopeepay", "Kartu Kredit"]
START_DATE_MONITORING = "2026-02-18"

# 2. CUSTOM CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
        background-color: #0e0e0e;
    }
    
    /* --- BENTO CARDS --- */
    .bento-card-green, .bento-card-red, .bento-card-dark, .bento-card-warning, .bento-card-blue {
        height: 160px; display: flex; flex-direction: column; justify-content: center;
        padding: 25px; border-radius: 24px; margin-bottom: 15px;
    }
    .bento-card-green { background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2); }
    .bento-card-red { background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%); color: white; box-shadow: 0 10px 30px rgba(239, 68, 68, 0.2); }
    .bento-card-dark { background-color: #1a1a1a; color: white; border: 1px solid rgba(255, 255, 255, 0.05); box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); }
    .bento-card-warning { background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: white; box-shadow: 0 10px 30px rgba(245, 158, 11, 0.2); }
    .bento-card-blue { background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); color: white; box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2); }

    /* --- WALLET CARD STYLE (NEW) --- */
    .wallet-card {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        position: relative;
        overflow: hidden;
    }
    .wallet-card::before {
        content: ""; position: absolute; top: -50px; right: -50px;
        width: 100px; height: 100px; background: rgba(255,255,255,0.05);
        border-radius: 50%;
    }
    .wallet-name { font-size: 14px; opacity: 0.7; letter-spacing: 1px; text-transform: uppercase; }
    .wallet-balance { font-size: 24px; font-weight: 700; margin-top: 5px; color: #fff; }
    .wallet-chip { 
        width: 40px; height: 25px; 
        background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%); 
        border-radius: 6px; margin-bottom: 15px; opacity: 0.8;
    }

    /* TYPOGRAPHY & BUTTONS */
    .card-label { font-size: 13px; opacity: 0.9; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .card-value { font-size: 28px; font-weight: 700; margin-bottom: 0px;}
    .card-detail { font-size: 12px; opacity: 0.8; margin-top: 5px; }
    
    div.stButton > button { 
        border-radius: 12px; height: 50px; font-weight: 600; text-transform: uppercase;
        background-color: #2563EB !important; color: white !important; border: none !important;
    }
    div.stButton > button:hover { background-color: #1d4ed8 !important; box-shadow: 0 5px 15px rgba(37, 99, 235, 0.4); }
    
    /* SIDEBAR & FORM */
    section[data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #222; }
    [data-testid="stForm"] { background-color: #161b22; border-radius: 24px; border: 1px solid #30363d; padding: 30px; }
    .streamlit-expanderHeader { background-color: #1a1a1a !important; border-radius: 12px !important; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 3. KONEKSI DATA
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        transaksi = conn.read(worksheet="Transaksi", ttl=0)
        dompet = conn.read(worksheet="Dompet", ttl=0)
        
        if not transaksi.empty:
            transaksi['Tanggal'] = pd.to_datetime(transaksi['Tanggal'], errors='coerce')
            transaksi['Nominal'] = pd.to_numeric(transaksi['Nominal'], errors='coerce').fillna(0)
        
        if not dompet.empty:
            dompet['Saldo Awal'] = pd.to_numeric(dompet['Saldo Awal'], errors='coerce').fillna(0)
            
        return transaksi, dompet
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

df, df_wallet_initial = load_data()

# ==========================================
# 4. SIDEBAR NAVIGATION & WALLET MONITORING
# ==========================================
with st.sidebar:
    st.title("🍱 Bento Pro")
    
    # MENU UTAMA
    selected_menu = st.radio(
        "Menu Aplikasi", 
        ["🏠 Dashboard", "👛 Dompet Saya", "💰 Budget Planner", "📁 Data Lengkap"],
        index=0
    )
    
    st.divider()
    
    # --- MINI MONITORING DI SIDEBAR ---
    # st.subheader("💳 Info Saldo Cepat")
    # if not df_wallet_initial.empty:
    #     # Hitung Saldo Realtime (Saldo Awal + Masuk - Keluar)
    #     # Grouping transaksi berdasarkan Metode Pembayaran
    #     wallet_in = df[df['Tipe'] == 'Pemasukan'].groupby('Metode Pembayaran')['Nominal'].sum()
    #     wallet_out = df[df['Tipe'] == 'Pengeluaran'].groupby('Metode Pembayaran')['Nominal'].sum()
        
    #     # Merge dengan Saldo Awal
    #     realtime_wallets = df_wallet_initial.copy()
    #     realtime_wallets['Masuk'] = realtime_wallets['Wallet'].map(wallet_in).fillna(0)
    #     realtime_wallets['Keluar'] = realtime_wallets['Wallet'].map(wallet_out).fillna(0)
    #     realtime_wallets['Saldo Akhir'] = realtime_wallets['Saldo Awal'] + realtime_wallets['Masuk'] - realtime_wallets['Keluar']
        
    #     # Tampilkan list kecil
    #     if not df_wallet_initial.empty:
    #     # Menghitung Total Kekayaan dari Saldo Manual
    #         total_aset_real = df_wallet_initial['Saldo Awal'].sum()
            
    #         for index, row in df_wallet_initial.iterrows():
    #             if row['Saldo Awal'] != 0:
    #                 st.caption(f"{row['Wallet']}: **Rp {row['Saldo Awal']:,.0f}**")
            
    #         st.write("---")
    #         st.markdown(f"<p style='font-size:14px; font-weight:bold; color:#54A0FF;'>Total Kekayaan: <br>Rp {total_aset_real:,.0f}</p>", unsafe_allow_html=True)
    
    # st.divider()
    
    # FILTER GLOBAL
    st.subheader("📅 Filter Periode")
    now = datetime.now()
    current_year = now.year
    current_month_name = now.strftime('%B')
    
    if not df.empty:
        df['Month'] = df['Tanggal'].dt.month_name()
        df['Year'] = df['Tanggal'].dt.year
        unique_years = sorted(df['Year'].unique(), reverse=True)
        idx_year = list(unique_years).index(current_year) if current_year in unique_years else 0
        selected_year = st.selectbox("Tahun", unique_years, index=idx_year)
        
        available_months = df[df['Year'] == selected_year]['Month'].unique()
        month_order = list(calendar.month_name)[1:]
        available_months = sorted(available_months, key=lambda x: month_order.index(x))
        if current_month_name in available_months:
            idx_month = list(available_months).index(current_month_name)
        else:
            idx_month = len(available_months) - 1 if len(available_months) > 0 else 0
        selected_month = st.selectbox("Bulan", available_months, index=idx_month)
    else:
        selected_year = current_year
        selected_month = current_month_name

# ==========================================
# LOGIC SCREEN
# ==========================================

# ---------------- SCREEN 1: DASHBOARD ----------------
if selected_menu == "🏠 Dashboard":
    st.title("🏠 Dashboard Utama")
    st.markdown(f"<span style='font-size:16px; opacity:0.5; margin-left:10px'>{selected_month} {selected_year}</span>", unsafe_allow_html=True)
    if not df.empty:
        # LOGIKA SALDO UTAMA: MURNI DARI DATA TRANSAKSI (GAJI - PENGELUARAN)
        global_in = df[df['Tipe'] == 'Pemasukan']['Nominal'].sum()
        global_out = df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        current_balance = global_in - global_out # Saldo murni dari cashflow gaji
        
        # Filter Bulanan
        mask = (df['Month'] == selected_month) & (df['Year'] == selected_year)
        df_filtered = df.loc[mask]

        monthly_in = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
        monthly_out = df_filtered[df_filtered['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        
        df_utang = df[df['Status'] == 'Belum Lunas']
        total_utang = df_utang['Nominal'].sum()

        # BENTO CARDS
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""<div class="bento-card-blue"><div><div class="card-label">💰 Sisa Saldo (Real)</div><div class="card-value">Rp {current_balance:,.0f}</div></div><div class="card-detail">Total Aset di Semua Dompet</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="bento-card-green"><div><div class="card-label">📈 Pemasukan ({selected_month})</div><div class="card-value">+ Rp {monthly_in:,.0f}</div></div></div>""", unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"""<div class="bento-card-red"><div><div class="card-label">📉 Pengeluaran ({selected_month})</div><div class="card-value">- Rp {monthly_out:,.0f}</div></div></div>""", unsafe_allow_html=True)
            with st.popover("Lihat Rincian Dompet 💳", use_container_width=True):
                if monthly_out > 0:
                    df_methods = df_filtered[df_filtered['Tipe'] == 'Pengeluaran'].groupby('Metode Pembayaran')['Nominal'].sum().reset_index()
                    for _, row in df_methods.iterrows():
                        st.markdown(f"<div style='display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #333;'><span>{row['Metode Pembayaran']}</span><b>Rp {row['Nominal']:,.0f}</b></div>", unsafe_allow_html=True)
                else:
                    st.info("Belum ada pengeluaran.")
        with c4:
            st.markdown(f"""<div class="bento-card-warning"><div><div class="card-label">⚠️ Total Tanggungan</div><div class="card-value">! Rp {total_utang:,.0f}</div></div><div class="card-detail">{len(df_utang)} Transaksi Belum Lunas</div></div>""", unsafe_allow_html=True)
    else:
        st.info("Belum ada data transaksi.")
    
    st.write("")
    
    # INPUT TRANSAKSI (Expander)
    if 'input_deskripsi' not in st.session_state: st.session_state['input_deskripsi'] = ""
    if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = None
    if 'input_ket' not in st.session_state: st.session_state['input_ket'] = ""

    def add_transaction():
        desk = st.session_state.input_deskripsi
        amt = st.session_state.input_nominal
        if not desk or amt is None or amt <= 0:
            st.toast("⚠️ Data tidak valid!", icon="⚠️")
            return
        try:
            current_df = conn.read(worksheet="Transaksi", ttl=0)
            new_row = pd.DataFrame([{
                "Tanggal": st.session_state.input_tanggal.strftime("%Y-%m-%d"),
                "Item": desk, "Kategori": st.session_state.input_kategori, 
                "Nominal": amt, "Tipe": st.session_state.input_tipe, 
                "Status": st.session_state.input_status, 
                "Keterangan": st.session_state.input_ket, 
                "Metode Pembayaran": "-" if st.session_state.input_status == "Belum Lunas" else st.session_state.get("input_metode", "Cash")
            }])
            updated_df = pd.concat([current_df, new_row], ignore_index=True)
            conn.update(worksheet="Transaksi", data=updated_df)
            st.session_state.input_deskripsi = ""
            st.session_state.input_nominal = None
            st.toast("✅ Tersimpan!", icon="🍱")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error: {e}")

    with st.expander("📝 Input Transaksi Baru", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.date_input("Tanggal", datetime.today(), key="input_tanggal")
            tipe = st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key="input_tipe")
            cats = KATEGORI_PEMASUKAN if tipe == "Pemasukan" else KATEGORI_PENGELUARAN
            st.selectbox("Kategori", cats, key="input_kategori")
        with c2:
            status = st.radio("Status", ["Lunas", "Belum Lunas"], horizontal=True, key="input_status")
            if status == "Lunas": st.selectbox("Metode", METODE_PEMBAYARAN, key="input_metode")
            else: st.text_input("Metode", value="-", disabled=True)
            st.number_input("Nominal (Rp)", min_value=0, step=1000, value=None, key="input_nominal")
        with c3:
            st.text_input("Item", key="input_deskripsi", placeholder="Cth: Kopi")
            st.text_area("Ket", key="input_ket", height=100)
        st.button("💾 SIMPAN DATA", type="primary", use_container_width=True, on_click=add_transaction)
    
    st.divider()
    
    # 3. ANALISIS CEPAT (DENGAN LEGENDA)
    st.subheader("📊 Analisis Cepat")
    if not df.empty and not df_filtered.empty:
        c1, c2 = st.columns([2,1])
        with c1:
            daily = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Tanggal')['Nominal'].sum().reset_index()
            fig = px.bar(daily, x='Tanggal', y='Nominal', color_discrete_sequence=['#EF4444'])
            fig.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            cat = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Kategori')['Nominal'].sum().reset_index()
            fig2 = px.pie(cat, values='Nominal', names='Kategori', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
            
            # MENGAKTIFKAN LEGENDA & MENGATUR POSISI
            fig2.update_layout(
                margin=dict(t=20, b=20, l=0, r=0), 
                height=350, # Sedikit ditambah agar legenda tidak terpotong
                showlegend=True,
                legend=dict(
                    orientation="h",   # Horizontal
                    yanchor="bottom", 
                    y=-0.3,           # Posisi di bawah chart
                    xanchor="center", 
                    x=0.5
                )
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Belum ada data untuk dianalisis bulan ini.")

# ---------------- SCREEN 2: DOMPET SAYA (LIVE WALLET START NEW) ----------------
elif selected_menu == "👛 Dompet Saya":
    st.title("👛 Monitoring Dompet")
    st.info(f"Sistem mulai menghitung transaksi otomatis sejak: **{START_DATE_MONITORING}**")
    
    if not df_wallet_initial.empty:
        # 1. FILTER TRANSAKSI HANYA YANG BARU (Mulai dari Start Date)
        df_new_trans = df[df['Tanggal'] >= START_DATE_MONITORING]
        
        wallet_in = df_new_trans[df_new_trans['Tipe'] == 'Pemasukan'].groupby('Metode Pembayaran')['Nominal'].sum()
        wallet_out = df_new_trans[df_new_trans['Tipe'] == 'Pengeluaran'].groupby('Metode Pembayaran')['Nominal'].sum()
        
        # 2. GABUNGKAN DENGAN SALDO AWAL
        live_wallets = df_wallet_initial.copy()
        live_wallets['Total Masuk'] = live_wallets['Wallet'].map(wallet_in).fillna(0)
        live_wallets['Total Keluar'] = live_wallets['Wallet'].map(wallet_out).fillna(0)
        
        # RUMUS: Saldo Sekarang = Saldo Input Hari Ini + Transaksi Baru
        live_wallets['Saldo Sekarang'] = (
            live_wallets['Saldo Awal'] + 
            live_wallets['Total Masuk'] - 
            live_wallets['Total Keluar']
        )
        
        # 3. TOTAL KEKAYAAN
        total_aset_real = live_wallets['Saldo Sekarang'].sum()
        st.markdown(f"""
        <div class="bento-card-blue" style="height: 120px; margin-bottom: 25px;">
            <div class="card-label">💎 TOTAL KEKAYAAN SAAT INI</div>
            <div class="card-value" style="font-size: 36px;">Rp {total_aset_real:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. KARTU DOMPET
        cols = st.columns(3)
        for i, row in live_wallets.iterrows():
            with cols[i % 3]:
                st.markdown(f"""
                <div class="wallet-card">
                    <div class="wallet-chip"></div>
                    <div class="wallet-name">{row['Wallet']}</div>
                    <div class="wallet-balance">Rp {row['Saldo Sekarang']:,.0f}</div>
                    <div style="font-size:10px; opacity:0.5; margin-top:5px;">
                        Initial Reset: {START_DATE_MONITORING}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    
    # 5. PENGATURAN SALDO AWAL (HANYA UNTUK SETTING PERTAMA KALI)
    with st.expander("⚙️ Atur Saldo Awal (Gunakan saat baru pakai app / sinkron ulang)"):
        st.info("Input saldo yang kamu pegang saat ini. Selanjutnya biarkan aplikasi yang menghitung otomatis.")
        
        edited_wallets = st.data_editor(
            df_wallet_initial, 
            column_config={
                "Wallet": st.column_config.TextColumn(disabled=True),
                "Saldo Awal": st.column_config.NumberColumn("Saldo Saat Ini", format="Rp %d", required=True)
            },
            hide_index=True,
            use_container_width=True,
            key="wallet_editor_live"
        )
        
        if st.button("💾 Simpan & Reset Perhitungan", type="primary"):
            try:
                conn.update(worksheet="Dompet", data=edited_wallets)
                st.toast("Saldo awal berhasil diupdate!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gagal update: {e}")

# ---------------- HALAMAN 2: BUDGET PLANNER ----------------
elif selected_menu == "💰 Budget Planner":
    st.title("💰 Perencanaan Budget")
    
    with st.container(border=True):
        col_gaji, col_simpan = st.columns([3, 1])
        with col_gaji:
            total_income = st.number_input("💵 Masukkan Total Gaji (Rp)", min_value=0, step=100000, value=5000000)
        with col_simpan:
            st.write("")
            st.write("")
            if st.button("📥 Catat Pemasukan", use_container_width=True):
                try:
                    curr = conn.read(worksheet="Transaksi", ttl=0)
                    new_row = pd.DataFrame([{
                        "Tanggal": datetime.today().strftime("%Y-%m-%d"),
                        "Item": "Gaji Bulanan", "Kategori": "Gaji",
                        "Nominal": total_income, "Tipe": "Pemasukan",
                        "Status": "Lunas", "Keterangan": "Budget Planner", "Metode Pembayaran": "Livin (Mandiri)"
                    }])
                    upd = pd.concat([curr, new_row], ignore_index=True)
                    conn.update(worksheet="Transaksi", data=upd)
                    st.toast("Gaji berhasil dicatat!", icon="✅")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    allocation_mode = st.radio("Metode Alokasi:", ["🔢 Atur Nominal (Rupiah)", "📊 Atur Persentase (%)"], horizontal=True)
    allocations = {}
    total_allocated = 0
    
    with st.container(border=True):
        cols = st.columns(2)
        if allocation_mode == "🔢 Atur Nominal (Rupiah)":
            for i, cat in enumerate(KATEGORI_PENGELUARAN):
                with cols[i % 2]:
                    val = st.number_input(f"Budget {cat} (Rp)", min_value=0, step=50000, key=f"nom_{cat}")
                    allocations[cat] = val
                    total_allocated += val
        else:
            for i, cat in enumerate(KATEGORI_PENGELUARAN):
                with cols[i % 2]:
                    pct = st.slider(f"Alokasi {cat} (%)", 0, 100, 0, key=f"pct_{cat}")
                    val = total_income * (pct / 100)
                    allocations[cat] = val
                    total_allocated += val
                    st.caption(f"Rp {val:,.0f}")

    st.divider()
    remaining = total_income - total_allocated
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="bento-card-blue" style="height:120px;"><div class="card-label">Total Gaji</div><div class="card-value">Rp {total_income:,.0f}</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="bento-card-dark" style="height:120px;"><div class="card-label">Dialokasikan</div><div class="card-value">Rp {total_allocated:,.0f}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#10B981" if remaining >= 0 else "#EF4444"
        st.markdown(f"""<div style="background:{color}; padding:20px; border-radius:24px; height:120px; color:white; display:flex; flex-direction:column; justify-content:center;"><div class="card-label">Sisa Budget</div><div class="card-value">Rp {remaining:,.0f}</div></div>""", unsafe_allow_html=True)

# ---------------- HALAMAN 3: DATA LENGKAP (Termasuk Manajemen Utang) ----------------
elif selected_menu == "📁 Data Lengkap":
    st.title("📁 Data Lengkap & Utang")
    
    # FILTER DATA
    if not df.empty:
        mask = (df['Month'] == selected_month) & (df['Year'] == selected_year)
        df_filtered_view = df.loc[mask].sort_values('Tanggal', ascending=False)
    else:
        df_filtered_view = pd.DataFrame()

    tab_tabel, tab_utang = st.tabs(["📋 Tabel Transaksi", "💸 Kelola Utang"])

    # --- TAB 1: TABEL TRANSAKSI (TANPA ID & TANPA JAM) ---
    with tab_tabel:
        if not df_filtered_view.empty:
            # Trik Menghilangkan ID & Format Tanggal
            # Column Config 'Tanggal' = DateColumn (akan otomatis hilang jam)
            # Hide Index = True
            # Column Order = exclude 'ID'
            
            # Definisikan kolom yang mau ditampilkan (Tanpa ID)
            cols_to_show = ["Tanggal", "Item", "Kategori", "Nominal", "Tipe", "Status", "Keterangan", "Metode Pembayaran"]
            
            st.dataframe(
                df_filtered_view,
                column_order=cols_to_show,
                column_config={
                    "Tanggal": st.column_config.DateColumn("Tanggal", format="DD MMM YYYY"),
                    "Nominal": st.column_config.NumberColumn("Nominal", format="Rp %d")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Data kosong untuk periode ini.")

    # --- TAB 2: MANAJEMEN UTANG (UPDATE METODE BAYAR) ---
    with tab_utang:
        st.info("💡 Cara Lunasin: Ubah Status ke **'Lunas'** DAN pilih **Metode Pembayaran** (sumber dana). Lalu klik Update.")
        
        # Filter Global Utang
        df_unpaid = df[df['Status'] == 'Belum Lunas'].copy()
        
        if not df_unpaid.empty:
            # Tampilkan Data Editor dengan 2 Kolom yang bisa diedit: Status & Metode
            editor = st.data_editor(
                df_unpaid,
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        label="Status Pelunasan",
                        options=["Belum Lunas", "Lunas"],
                        required=True
                    ),
                    "Metode Pembayaran": st.column_config.SelectboxColumn(
                        label="Bayar Pakai Apa?",
                        options=METODE_PEMBAYARAN, # List metode dari config
                        required=True
                    ),
                    "Nominal": st.column_config.NumberColumn(format="Rp %d"),
                    "Tanggal": st.column_config.DateColumn(format="DD MMM YYYY")
                },
                # HAPUS 'Metode Pembayaran' dari disabled agar bisa diedit
                disabled=["Tanggal", "Item", "Nominal", "Kategori", "Tipe", "ID"], 
                column_order=["Tanggal", "Item", "Nominal", "Status", "Metode Pembayaran"],
                hide_index=True,
                use_container_width=True,
                key="utang_editor"
            )
            
            if st.button("🔄 Update Pelunasan", type="primary"):
                try:
                    # 1. Baca Data Asli
                    orig = conn.read(worksheet="Transaksi", ttl=0)
                    
                    # 2. Normalisasi Tanggal
                    orig['Tanggal_Match'] = pd.to_datetime(orig['Tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
                    
                    changes_count = 0
                    for i, row in editor.iterrows():
                        # Cek jika Status Lunas
                        if row['Status'] == 'Lunas':
                            # Validasi: Pastikan user memilih metode bayar (bukan strip "-")
                            if row['Metode Pembayaran'] == "-" or row['Metode Pembayaran'] is None:
                                st.warning(f"⚠️ Harap pilih Metode Pembayaran untuk item: {row['Item']}")
                                continue # Skip item ini, jangan simpan dulu
                            
                            target_date = pd.to_datetime(row['Tanggal']).strftime('%Y-%m-%d')
                            
                            # Matching Logic
                            mask = (
                                (orig['Tanggal_Match'] == target_date) & 
                                (orig['Item'] == row['Item']) & 
                                (orig['Nominal'] == row['Nominal']) & 
                                (orig['Status'] == 'Belum Lunas')
                            )
                            
                            if mask.any():
                                orig.loc[mask, 'Status'] = 'Lunas'
                                # UPDATE JUGA METODE PEMBAYARANNYA
                                orig.loc[mask, 'Metode Pembayaran'] = row['Metode Pembayaran']
                                changes_count += 1
                    
                    if changes_count > 0:
                        orig = orig.drop(columns=['Tanggal_Match'])
                        orig['Tanggal'] = pd.to_datetime(orig['Tanggal']).dt.strftime('%Y-%m-%d')
                        
                        conn.update(worksheet="Transaksi", data=orig)
                        st.toast(f"Berhasil melunasi {changes_count} transaksi! Saldo terupdate.", icon="✅")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("Tidak ada perubahan valid yang disimpan.")
                        
                except Exception as e:
                    st.error(f"Error Update: {e}")
        else:
            st.success("🎉 Tidak ada tanggungan utang saat ini!")
