import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import calendar

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Budget Bento Pro v5 (Final)", page_icon="🍱", layout="wide")

# --- KONFIGURASI KATEGORI ---
KATEGORI_PEMASUKAN = ["Gaji", "Bonus", "Hadiah", "Investasi", "Penjualan", "Lainnya"]
KATEGORI_PENGELUARAN = ["Makan", "Transport", "Hiburan", "Tagihan", "Belanja", "Kesehatan", "Pendidikan", "Amal", "Lainnya"]
METODE_PEMBAYARAN = ["Cash", "Livin (Mandiri)", "Octo (CIMB)", "DANA", "Shopeepay", "Kartu Kredit"]

# 2. CUSTOM CSS (DARK BENTO THEME)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
        background-color: #0e0e0e;
    }
    
    /* --- STYLE KARTU BENTO --- */
    .bento-card-green, .bento-card-red, .bento-card-dark, .bento-card-warning {
        height: 180px; 
        display: flex; 
        flex-direction: column; 
        justify-content: center;
        padding: 25px;
        border-radius: 24px;
        margin-bottom: 10px;
    }

    /* 1. KARTU SALDO (HIJAU) */
    .bento-card-green {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
    }

    /* 2. KARTU PENGELUARAN (MERAH) */
    .bento-card-red {
        background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
        color: white;
        box-shadow: 0 10px 30px rgba(239, 68, 68, 0.2);
    }
    
    /* 3. KARTU PEMASUKAN (HITAM) */
    .bento-card-dark {
        background-color: #1a1a1a; 
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
    }

    /* 4. KARTU TANGGUNGAN (ORANGE) */
    .bento-card-warning {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
        box-shadow: 0 10px 30px rgba(245, 158, 11, 0.2);
    }

    /* TYPOGRAPHY */
    .card-label { font-size: 13px; opacity: 0.9; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .card-value { font-size: 32px; font-weight: 700; margin-bottom: 0px;}
    .card-detail { font-size: 12px; opacity: 0.8; margin-top: 5px; }
    
    /* BUTTONS & FORM */
    div.stButton > button { border-radius: 12px; height: 50px; font-weight: 600; text-transform: uppercase; }
    [data-testid="stForm"] { background-color: #161b22; border-radius: 24px; border: 1px solid #30363d; padding: 25px; }
    
    /* MODIFIKASI POPOVER BUTTON */
    [data-testid="stPopover"] > button {
        background-color: transparent;
        border: 1px solid rgba(255,255,255,0.2);
        color: rgba(255,255,255,0.7);
        height: 40px;
        font-size: 12px;
        width: 100%;
    }
    [data-testid="stPopover"] > button:hover {
        border-color: #EF4444;
        color: #EF4444;
    }

</style>
""", unsafe_allow_html=True)

# 3. KONEKSI DATA
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="Transaksi", ttl=0)
        if not data.empty:
            data['Tanggal'] = pd.to_datetime(data['Tanggal'], errors='coerce')
            data['Nominal'] = pd.to_numeric(data['Nominal'], errors='coerce').fillna(0)
            if 'ID' not in data.columns: data['ID'] = range(1, len(data) + 1)
        return data
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# 4. SIDEBAR FILTER
with st.sidebar:
    st.title("🎛️ Filter Data")
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

# 5. DASHBOARD LAYOUT (GRID 2x2)
st.markdown(f"<h2 style='margin-bottom:20px;'>🍱 Budget Bento Pro <span style='font-size:16px; opacity:0.5; margin-left:10px'>{selected_month} {selected_year}</span></h2>", unsafe_allow_html=True)

if not df.empty:
    mask = (df['Month'] == selected_month) & (df['Year'] == selected_year)
    df_filtered = df.loc[mask]

    # Kalkulasi
    total_in = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
    total_out = df_filtered[df_filtered['Tipe'] == 'Pengeluaran']['Nominal'].sum()
    balance = total_in - total_out
    
    df_utang = df[df['Status'] == 'Belum Lunas']
    total_utang = df_utang['Nominal'].sum()

    # --- ROW 1 ---
    r1c1, r1c2 = st.columns(2)
    
    with r1c1:
        # KARTU SALDO (HIJAU)
        st.markdown(f"""
        <div class="bento-card-green">
            <div>
                <div class="card-label">💰 Sisa Saldo</div>
                <div class="card-value">Rp {balance:,.0f}</div>
            </div>
            <div class="card-detail">Aman untuk {selected_month}</div>
        </div>
        """, unsafe_allow_html=True)

    with r1c2:
        # KARTU PEMASUKAN (HITAM)
        st.markdown(f"""
        <div class="bento-card-dark">
            <div>
                <div class="card-label" style="color:#4ade80;">📈 Total Pemasukan</div>
                <div class="card-value">Rp {total_in:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- ROW 2 ---
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        # KARTU PENGELUARAN (MERAH SOLID)
        st.markdown(f"""
        <div class="bento-card-red">
            <div>
                <div class="card-label">📉 Pengeluaran</div>
                <div class="card-value">Rp {total_out:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # DROPDOWN (POPOVER) UNTUK RINCIAN
        with st.popover("Lihat Rincian Dompet 💳", use_container_width=True):
            st.markdown("### Sumber Dana Terpakai")
            if total_out > 0:
                df_methods = df_filtered[df_filtered['Tipe'] == 'Pengeluaran'].groupby('Metode Pembayaran')['Nominal'].sum().reset_index()
                for _, row in df_methods.iterrows():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid #444; padding:8px 0;">
                        <span>{row['Metode Pembayaran']}</span>
                        <span style="font-weight:bold;">Rp {row['Nominal']:,.0f}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Belum ada pengeluaran.")

    with r2c2:
        # KARTU TANGGUNGAN (ORANGE)
        st.markdown(f"""
        <div class="bento-card-warning">
            <div>
                <div class="card-label">⚠️ Total Tanggungan</div>
                <div class="card-value">Rp {total_utang:,.0f}</div>
            </div>
            <div class="card-detail">{len(df_utang)} Transaksi Belum Lunas</div>
        </div>
        """, unsafe_allow_html=True)

# 6. FORM INPUT (EXPANDER)
st.write("")
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

with st.expander("➕ TAMBAH TRANSAKSI BARU", expanded=False):
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

# 7. TABS ANALISIS & UTANG
tab1, tab2, tab3 = st.tabs(["📊 Analisis", "💸 Manajemen Utang", "📋 Data Lengkap"])

with tab1:
    if not df.empty:
        c1, c2 = st.columns([2,1])
        with c1:
            st.caption("Tren Pengeluaran")
            daily = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Tanggal')['Nominal'].sum().reset_index()
            fig = px.bar(daily, x='Tanggal', y='Nominal', color_discrete_sequence=['#EF4444'])
            fig.update_layout(height=300, xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.caption("Kategori")
            cat = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Kategori')['Nominal'].sum().reset_index()
            fig2 = px.pie(cat, values='Nominal', names='Kategori', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.info("💡 Klik status 'Belum Lunas' -> ubah ke 'Lunas' -> Klik Update.")
    df_unpaid = df[df['Status'] == 'Belum Lunas'].copy()
    if not df_unpaid.empty:
        editor = st.data_editor(df_unpaid, column_config={"Status": st.column_config.SelectboxColumn(options=["Belum Lunas", "Lunas"], required=True), "Nominal": st.column_config.NumberColumn(format="Rp %d")}, disabled=["Tanggal", "Item", "Nominal"], hide_index=True, use_container_width=True, key="utang_editor")
        if st.button("🔄 Update Pelunasan", type="primary"):
            orig = conn.read(worksheet="Transaksi", ttl=0)
            orig['Tanggal'] = pd.to_datetime(orig['Tanggal'])
            changes = False
            for i, row in editor.iterrows():
                if row['Status'] == 'Lunas':
                    mask = (orig['Item'] == row['Item']) & (orig['Nominal'] == row['Nominal']) & (orig['Status'] == 'Belum Lunas')
                    if mask.any():
                        orig.loc[mask, 'Status'] = 'Lunas'
                        changes = True
            if changes:
                orig['Tanggal'] = orig['Tanggal'].dt.strftime('%Y-%m-%d')
                conn.update(worksheet="Transaksi", data=orig)
                st.toast("Lunas!", icon="✅")
                st.rerun()
    else:
        st.success("Bebas Utang!")

with tab3:
    st.dataframe(df_filtered.sort_values('Tanggal', ascending=False), use_container_width=True, hide_index=True)
