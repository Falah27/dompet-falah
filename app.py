import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import calendar

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Budget Bento Pro v13", page_icon="🍱", layout="wide")

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

    /* --- WALLET CARD STYLE --- */
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
        transaksi = conn.read(worksheet="Transaksi", ttl=600)
        dompet = conn.read(worksheet="Dompet", ttl=600)
        
        # --- PERBAIKAN LOGIKA LOAD TARGET IMPIAN ---
        try:
            target = conn.read(worksheet="Target", ttl=600)
            
            # Jika tabel terbaca tapi kosong, bentuk ulang agar formatnya tidak rusak
            if target.empty:
                target = pd.DataFrame(columns=['Nama Impian', 'Target Harga', 'Dana Terkumpul'])
            else:
                # Paksa kolom 'Nama Impian' menjadi string (teks) agar tidak dianggap Float
                target['Nama Impian'] = target['Nama Impian'].fillna("").astype(str)
                target['Target Harga'] = pd.to_numeric(target['Target Harga'], errors='coerce').fillna(0)
                target['Dana Terkumpul'] = pd.to_numeric(target['Dana Terkumpul'], errors='coerce').fillna(0)
        except:
            # Jika Sheet 'Target' belum ada sama sekali
            target = pd.DataFrame(columns=['Nama Impian', 'Target Harga', 'Dana Terkumpul'])
            target['Nama Impian'] = target['Nama Impian'].astype(str)
        # -------------------------------------------
        
        if not transaksi.empty:
            transaksi['Tanggal'] = pd.to_datetime(transaksi['Tanggal'], errors='coerce')
            transaksi['Nominal'] = pd.to_numeric(transaksi['Nominal'], errors='coerce').fillna(0)
        
        if not dompet.empty:
            dompet['Saldo Awal'] = pd.to_numeric(dompet['Saldo Awal'], errors='coerce').fillna(0)
            
        return transaksi, dompet, target
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df, df_wallet_initial, df_target = load_data()

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.title("🍱 Bento Pro")
    
    # MENU UTAMA (TAMBAH TARGET IMPIAN)
    selected_menu = st.radio(
        "Menu Aplikasi", 
        ["🏠 Dashboard", "👛 Dompet Saya", "💰 Budget Planner", "🎯 Target Impian", "📁 Data Lengkap"],
        index=0
    )
    
    st.divider()
    
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
        mask = (df['Month'] == selected_month) & (df['Year'] == selected_year)
        df_filtered = df.loc[mask]

        global_in = df[df['Tipe'] == 'Pemasukan']['Nominal'].sum()
        global_out = df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        current_balance = global_in - global_out 

        monthly_in = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
        monthly_out = df_filtered[df_filtered['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        
        df_utang = df[df['Status'] == 'Belum Lunas']
        total_utang = df_utang['Nominal'].sum()

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
        df_filtered = pd.DataFrame()
    
    st.write("")
    
    # TOAST NOTIFICATION HANDLER
    if 'sukses_simpan' in st.session_state:
        st.toast(f"✅ Tersimpan: {st.session_state['sukses_simpan']}", icon="🍱")
        del st.session_state['sukses_simpan']

    # --- INISIALISASI STATE KOSONG ---
    # Memastikan form benar-benar kosong saat pertama kali dibuka
    if 'in_nom' not in st.session_state: st.session_state['in_nom'] = None
    if 'in_desk' not in st.session_state: st.session_state['in_desk'] = ""
    if 'in_ket' not in st.session_state: st.session_state['in_ket'] = ""

    # INPUT TRANSAKSI (DINAMIS & CEPAT)
    with st.expander("📝 Input Transaksi Baru", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            input_tanggal = st.date_input("Tanggal", datetime.today(), key="in_tgl")
            input_tipe = st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key="in_tipe")
            cats = KATEGORI_PEMASUKAN if input_tipe == "Pemasukan" else KATEGORI_PENGELUARAN
            input_kategori = st.selectbox("Kategori", cats, key="in_kat")
            
        with c2:
            input_status = st.radio("Status", ["Lunas", "Belum Lunas"], horizontal=True, key="in_stat")
            is_disabled = (input_status == "Belum Lunas")
            input_metode = st.selectbox("Metode", METODE_PEMBAYARAN, disabled=is_disabled, key="in_met")
            
            # --- PERBAIKAN 1: value=None agar kotak nominal kosong ---
            input_nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000, value=None, key="in_nom")
            
        with c3:
            input_deskripsi = st.text_input("Item", placeholder="Cth: Kopi / Gaji", key="in_desk")
            input_ket = st.text_area("Ket", height=100, key="in_ket")
            
        if st.button("💾 SIMPAN DATA", type="primary", use_container_width=True):
            # Cek juga kalau nominal masih None (kosong)
            if not input_deskripsi or input_nominal is None or input_nominal <= 0:
                st.error("⚠️ Gagal: Nama Item harus diisi dan Nominal harus diisi lebih dari 0!")
            else:
                try:
                    current_df = conn.read(worksheet="Transaksi", ttl=0) 
                    new_row = pd.DataFrame([{
                        "Tanggal": input_tanggal.strftime("%Y-%m-%d"),
                        "Item": input_deskripsi, "Kategori": input_kategori, 
                        "Nominal": input_nominal, "Tipe": input_tipe, 
                        "Status": input_status, "Keterangan": input_ket, 
                        "Metode Pembayaran": "-" if is_disabled else input_metode
                    }])
                    updated_df = pd.concat([current_df, new_row], ignore_index=True)
                    conn.update(worksheet="Transaksi", data=updated_df)
                    
                    st.session_state['sukses_simpan'] = input_deskripsi
                    
                    # --- PERBAIKAN 2: Timpa data dengan kosong agar langsung bersih ---
                    st.session_state['in_nom'] = None
                    st.session_state['in_desk'] = ""
                    st.session_state['in_ket'] = ""
                    
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.divider()
    
    # GRAFIK ANALISIS CEPAT
    st.subheader("📊 Analisis Cepat")
    if not df.empty and not df_filtered.empty:
        c_graph1, c_graph2 = st.columns([2,1])
        with c_graph1:
            daily_stats = df_filtered.groupby(['Tanggal', 'Tipe'])['Nominal'].sum().reset_index()
            fig = px.bar(daily_stats, x='Tanggal', y='Nominal', color='Tipe', barmode='group',
                         color_discrete_map={'Pemasukan': '#10B981', 'Pengeluaran': '#EF4444'})
            fig.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                              height=300, showlegend=False, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
        with c_graph2:
            cat = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Kategori')['Nominal'].sum().reset_index()
            if not cat.empty:
                fig2 = px.pie(cat, values='Nominal', names='Kategori', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
                fig2.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=350, showlegend=True,
                                   legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.caption("Belum ada data pengeluaran untuk chart ini.")

# ---------------- SCREEN 2: DOMPET SAYA ----------------
elif selected_menu == "👛 Dompet Saya":
    st.title("👛 Monitoring Dompet")
    st.info(f"Sistem mulai menghitung transaksi otomatis sejak: **{START_DATE_MONITORING}**")
    
    if not df_wallet_initial.empty:
        df_new_trans = df[df['Tanggal'] >= START_DATE_MONITORING]
        wallet_in = df_new_trans[df_new_trans['Tipe'] == 'Pemasukan'].groupby('Metode Pembayaran')['Nominal'].sum()
        wallet_out = df_new_trans[df_new_trans['Tipe'] == 'Pengeluaran'].groupby('Metode Pembayaran')['Nominal'].sum()
        
        live_wallets = df_wallet_initial.copy()
        live_wallets['Total Masuk'] = live_wallets['Wallet'].map(wallet_in).fillna(0)
        live_wallets['Total Keluar'] = live_wallets['Wallet'].map(wallet_out).fillna(0)
        live_wallets['Saldo Sekarang'] = live_wallets['Saldo Awal'] + live_wallets['Total Masuk'] - live_wallets['Total Keluar']
        
        total_aset_real = live_wallets['Saldo Sekarang'].sum()
        st.markdown(f"""
        <div class="bento-card-blue" style="height: 120px; margin-bottom: 25px;">
            <div class="card-label">💎 TOTAL KEKAYAAN SAAT INI</div>
            <div class="card-value" style="font-size: 36px;">Rp {total_aset_real:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        for i, row in live_wallets.iterrows():
            with cols[i % 3]:
                st.markdown(f"""
                <div class="wallet-card">
                    <div class="wallet-chip"></div>
                    <div class="wallet-name">{row['Wallet']}</div>
                    <div class="wallet-balance">Rp {row['Saldo Sekarang']:,.0f}</div>
                    <div style="font-size:10px; opacity:0.5; margin-top:5px;">Input Awal: Rp {row['Saldo Awal']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    with st.expander("⚙️ Atur Saldo Awal (Gunakan saat sinkron ulang)"):
        edited_wallets = st.data_editor(
            df_wallet_initial, 
            column_config={
                "Wallet": st.column_config.TextColumn(disabled=True),
                "Saldo Awal": st.column_config.NumberColumn("Saldo Saat Ini", format="Rp %d", required=True)
            }, hide_index=True, use_container_width=True
        )
        if st.button("💾 Simpan & Reset Perhitungan", type="primary"):
            try:
                conn.update(worksheet="Dompet", data=edited_wallets)
                st.toast("Saldo awal berhasil diupdate!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gagal update: {e}")

# ---------------- SCREEN 3: BUDGET PLANNER ----------------
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
                    st.cache_data.clear()
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

# ---------------- SCREEN 4: TARGET IMPIAN (FITUR BARU 🌟) ----------------
elif selected_menu == "🎯 Target Impian":
    st.title("🎯 Target & Wishlist")
    st.markdown("Pantau progress tabunganmu untuk mencapai impian besar (Gadget, Liburan, Kendaraan, dll).")
    
    if not df_target.empty:
        for i, row in df_target.iterrows():
            nama = row['Nama Impian']
            harga = row['Target Harga']
            kumpul = row['Dana Terkumpul']
            
            # Kalkulasi persentase
            if harga > 0:
                pct = min(kumpul / harga, 1.0)
            else:
                pct = 0
            pct_display = int(pct * 100)
            
            st.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 16px; margin-bottom: 5px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 600; font-size: 18px;">{nama}</span>
                    <span style="color: #10B981; font-weight: bold;">{pct_display}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; opacity: 0.7; margin-bottom: 15px;">
                    <span>Terkumpul: Rp {kumpul:,.0f}</span>
                    <span>Target: Rp {harga:,.0f}</span>
                </div>
            """, unsafe_allow_html=True)
            st.progress(pct) # Progress Bar bawaan Streamlit
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Kamu belum memiliki target impian. Yuk buat satu di bawah!")

    st.divider()
    
    with st.expander("⚙️ Kelola Target Impian", expanded=True):
        st.info("💡 **Cara Edit:** Tambahkan impian baru di baris kosong paling bawah. Update jumlah tabunganmu di kolom 'Dana Terkumpul'.")
        edited_target = st.data_editor(
            df_target,
            column_config={
                "Nama Impian": st.column_config.TextColumn("Nama Impian", required=True),
                "Target Harga": st.column_config.NumberColumn("Target Harga (Rp)", format="Rp %d", required=True),
                "Dana Terkumpul": st.column_config.NumberColumn("Dana Terkumpul (Rp)", format="Rp %d", required=True)
            },
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key="target_editor"
        )
        if st.button("💾 Simpan Target", type="primary"):
            try:
                conn.update(worksheet="Target", data=edited_target)
                st.toast("Target impian berhasil diperbarui!", icon="🎯")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan target: {e}")

# ---------------- SCREEN 5: DATA LENGKAP & EXPORT ----------------
elif selected_menu == "📁 Data Lengkap":
    st.title("📁 Data Lengkap & Laporan")
    
    if not df.empty:
        mask = (df['Month'] == selected_month) & (df['Year'] == selected_year)
        df_filtered_view = df.loc[mask].sort_values('Tanggal', ascending=False)
    else:
        df_filtered_view = pd.DataFrame()

    tab_tabel, tab_utang = st.tabs(["📋 Tabel Transaksi (Edit & Hapus)", "💸 Kelola Utang"])

    # --- TABEL TRANSAKSI (EDIT & HAPUS DATA) ---
    with tab_tabel:
        st.info("💡 **Cara Edit:** Klik sel untuk mengubah teks. **Cara Hapus:** Geser tabel ke kanan, centang kotak paling kiri, lalu klik ikon 🗑️ di atas tabel. Jangan lupa klik Simpan.")
        
        if not df_filtered_view.empty:
            cols_to_show = ["Tanggal", "Item", "Kategori", "Nominal", "Tipe", "Status", "Keterangan", "Metode Pembayaran"]
            df_to_edit = df_filtered_view[cols_to_show].copy()
            semua_kategori = list(dict.fromkeys(KATEGORI_PEMASUKAN + KATEGORI_PENGELUARAN))
            
            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Tanggal": st.column_config.DateColumn("Tanggal", format="DD MMM YYYY", required=True),
                    "Nominal": st.column_config.NumberColumn("Nominal", format="Rp %d", required=True),
                    "Tipe": st.column_config.SelectboxColumn("Tipe", options=["Pemasukan", "Pengeluaran"], required=True),
                    "Kategori": st.column_config.SelectboxColumn("Kategori", options=semua_kategori, required=True),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Lunas", "Belum Lunas"], required=True),
                    "Metode Pembayaran": st.column_config.SelectboxColumn("Metode", options=["-"] + METODE_PEMBAYARAN, required=True)
                },
                num_rows="dynamic",
                hide_index=False,
                use_container_width=True,
                key="editor_transaksi_lengkap"
            )
            
            if st.button("💾 Simpan Perubahan Data", type="primary"):
                try:
                    orig = conn.read(worksheet="Transaksi", ttl=0)
                    orig['Tanggal_Parsed'] = pd.to_datetime(orig['Tanggal'], errors='coerce')
                    
                    mask_orig = (orig['Tanggal_Parsed'].dt.month_name() == selected_month) & (orig['Tanggal_Parsed'].dt.year == selected_year)
                    orig_kept = orig[~mask_orig].copy().drop(columns=['Tanggal_Parsed'])
                    
                    edited_clean = edited_df.copy()
                    edited_clean['Tanggal'] = pd.to_datetime(edited_clean['Tanggal']).dt.strftime('%Y-%m-%d')
                    
                    final_df = pd.concat([orig_kept, edited_clean], ignore_index=True)
                    conn.update(worksheet="Transaksi", data=final_df)
                    st.toast("✅ Perubahan tabel berhasil disimpan!", icon="🍱")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
                    
            st.divider()
            
            # --- FITUR E-STATEMENT PDF (ALA M-BANKING) ---
    if not df_filtered_view.empty:
        st.markdown("### 📥 Download E-Statement (PDF)")
        st.caption(f"Cetak laporan resmi keuanganmu ala Bank untuk bulan {selected_month} {selected_year}.")
        
        def create_pdf(df_laporan, month, year):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # --- HEADER (Mirip Kop Surat Bank) ---
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(37, 99, 235) # Biru Bento
            pdf.cell(0, 8, "BENTO PRO BY STREAMLIT", ln=True, align='R')
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "PERSONAL FINANCE STATEMENT", ln=True, align='R')
            pdf.ln(5)
            
            # --- JUDUL & PERIODE ---
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, "Laporan Rekening / Statement of Account", ln=True, align='L')
            
            # Cari tanggal terakhir di bulan tsb
            month_idx = list(calendar.month_name).index(month)
            last_day = calendar.monthrange(int(year), month_idx)[1]
            
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 6, f"Periode: 01 {month} {year} - {last_day} {month} {year}", ln=True, align='L')
            pdf.ln(5)
            
            # --- INFO AKUN ---
            pdf.set_font("Arial", '', 10)
            pdf.cell(30, 6, "Jenis Produk", border=0)
            pdf.cell(0, 6, ": Bento Finance Tracker", border=0, ln=True)
            pdf.cell(30, 6, "Nama", border=0)
            pdf.cell(0, 6, ": Pengguna Utama", border=0, ln=True)
            pdf.cell(30, 6, "Mata Uang", border=0)
            pdf.cell(0, 6, ": IDR", border=0, ln=True)
            pdf.ln(5)
            
            # --- TABLE HEADER ---
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(37, 99, 235)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 8, "Tanggal", border=1, fill=True, align='C')
            pdf.cell(75, 8, "Deskripsi", border=1, fill=True, align='C')
            pdf.cell(30, 8, "Pengeluaran", border=1, fill=True, align='C')
            pdf.cell(30, 8, "Pemasukan", border=1, fill=True, align='C')
            pdf.cell(35, 8, "Saldo", border=1, fill=True, align='C')
            pdf.ln()
            
            # --- SORT DATA: Dari tanggal terlama ke terbaru (Chronological) ---
            df_sorted = df_laporan.sort_values('Tanggal', ascending=True).copy()
            
            # --- ISI TABEL ---
            pdf.set_font("Arial", '', 8)
            pdf.set_text_color(0, 0, 0)
            
            running_balance = 0
            total_kredit = 0
            total_debit = 0
            
            for i, row in df_sorted.iterrows():
                tgl = pd.to_datetime(row['Tanggal']).strftime('%d/%m/%Y')
                
                # Format Deskripsi: Item + Metode
                desc_raw = f"{row['Item']} ({row['Metode Pembayaran']})"
                desc = desc_raw[:45] # Potong teks kepanjangan agar tidak keluar kotak
                
                debit_str = ""
                kredit_str = ""
                
                if row['Tipe'] == 'Pengeluaran':
                    nom = row['Nominal']
                    debit_str = f"{nom:,.2f}"
                    total_debit += nom
                    running_balance -= nom
                else:
                    nom = row['Nominal']
                    kredit_str = f"{nom:,.2f}"
                    total_kredit += nom
                    running_balance += nom
                    
                saldo_str = f"{running_balance:,.2f}"
                
                # Print Row
                pdf.cell(20, 7, tgl, border=1, align='C')
                pdf.cell(75, 7, desc, border=1, align='L')
                pdf.cell(30, 7, debit_str, border=1, align='R')
                pdf.cell(30, 7, kredit_str, border=1, align='R')
                pdf.cell(35, 7, saldo_str, border=1, align='R')
                pdf.ln()

            pdf.ln(5)
            
            # --- SUMMARY KOTAK ---
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(40, 6, "Total Pengeluaran", border=0)
            pdf.cell(50, 6, f"IDR {total_debit:,.2f}", border=0, ln=True)
            pdf.cell(40, 6, "Total Pemasukan", border=0)
            pdf.cell(50, 6, f"IDR {total_kredit:,.2f}", border=0, ln=True)
            pdf.cell(40, 6, "Net Saldo Bulan Ini", border=0)
            pdf.cell(50, 6, f"IDR {running_balance:,.2f}", border=0, ln=True)
            
            pdf.ln(10)
            
            # --- FOOTER ---
            pdf.set_font("Arial", 'I', 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, "IMPORTANT!", ln=True)
            pdf.cell(0, 5, "Dokumen e-statement ini di-generate secara otomatis oleh sistem aplikasi Bento Pro.", ln=True)
            pdf.cell(0, 5, "Data keuangan Anda bersifat rahasia. Jangan membagikannya dengan alasan apa pun.", ln=True)
            
            # Output ke bytes
            return pdf.output(dest='S').encode('latin-1')

        # Generate Button
        pdf_bytes = create_pdf(df_filtered_view, selected_month, selected_year)
        
        st.download_button(
            label="📄 Download E-Statement (.pdf)",
            data=pdf_bytes,
            file_name=f"E-Statement_BentoPro_{selected_month}_{selected_year}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.divider()

    # --- TABEL UTANG ---
    with tab_utang:
        st.info("💡 Ubah Status ke **'Lunas'** DAN pilih **Metode Pembayaran** (sumber dana). Lalu klik Update.")
        df_unpaid = df[df['Status'] == 'Belum Lunas'].copy()
        
        if not df_unpaid.empty:
            editor = st.data_editor(
                df_unpaid,
                column_config={
                    "Status": st.column_config.SelectboxColumn(options=["Belum Lunas", "Lunas"], required=True),
                    "Metode Pembayaran": st.column_config.SelectboxColumn(options=METODE_PEMBAYARAN, required=True),
                    "Nominal": st.column_config.NumberColumn(format="Rp %d"),
                    "Tanggal": st.column_config.DateColumn(format="DD MMM YYYY")
                },
                disabled=["Tanggal", "Item", "Nominal", "Kategori", "Tipe", "ID"], 
                column_order=["Tanggal", "Item", "Nominal", "Status", "Metode Pembayaran"],
                hide_index=True, use_container_width=True, key="utang_editor"
            )
            
            if st.button("🔄 Update Pelunasan", type="primary"):
                try:
                    orig = conn.read(worksheet="Transaksi", ttl=0)
                    orig['Tanggal_Match'] = pd.to_datetime(orig['Tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
                    changes_count = 0
                    
                    for i, row in editor.iterrows():
                        if row['Status'] == 'Lunas':
                            if row['Metode Pembayaran'] == "-" or row['Metode Pembayaran'] is None:
                                st.warning(f"⚠️ Harap pilih Metode Pembayaran untuk item: {row['Item']}")
                                continue
                            
                            target_date = pd.to_datetime(row['Tanggal']).strftime('%Y-%m-%d')
                            mask = ((orig['Tanggal_Match'] == target_date) & (orig['Item'] == row['Item']) & 
                                    (orig['Nominal'] == row['Nominal']) & (orig['Status'] == 'Belum Lunas'))
                            
                            if mask.any():
                                orig.loc[mask, 'Status'] = 'Lunas'
                                orig.loc[mask, 'Metode Pembayaran'] = row['Metode Pembayaran']
                                changes_count += 1
                    
                    if changes_count > 0:
                        orig = orig.drop(columns=['Tanggal_Match'])
                        orig['Tanggal'] = pd.to_datetime(orig['Tanggal']).dt.strftime('%Y-%m-%d')
                        conn.update(worksheet="Transaksi", data=orig)
                        st.toast(f"Berhasil melunasi {changes_count} transaksi!", icon="✅")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error Update: {e}")
        else:
            st.success("🎉 Tidak ada tanggungan utang saat ini!")
