import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Budget Bento Pro", page_icon="🍱", layout="wide")

# 2. CUSTOM CSS (MODERN BENTO & M-BANKING UI)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
        background-color: #0e0e0e;
    }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }

    /* --- KARTU BENTO STYLE --- */
    .bento-card-green {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white; padding: 25px; border-radius: 28px;
        height: 200px; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
        display: flex; flex-direction: column; justify-content: space-between;
        transition: transform 0.3s ease;
    }
    .bento-card-dark {
        background-color: #1a1a1a; color: white; padding: 22px;
        border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.05);
        height: 100%; display: flex; flex-direction: column; justify-content: center;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
    }
    .bento-card-green:hover, .bento-card-dark:hover { transform: translateY(-5px); }

    .card-label { font-size: 14px; opacity: 0.8; font-weight: 400; text-transform: uppercase; letter-spacing: 1px; }
    .card-value { font-size: 36px; font-weight: 700; margin: 10px 0; }
    .card-value-small { font-size: 24px; font-weight: 600; }

    /* --- FORM & BUTTONS --- */
    div.stButton > button {
        background: #10B981; color: white; border: none; border-radius: 15px;
        padding: 14px; font-weight: 600; width: 100%; transition: 0.3s;
        text-transform: uppercase; letter-spacing: 1px;
    }
    div.stButton > button:hover { background: #059669; box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
    [data-testid="stForm"] { background-color: #161b22; border-radius: 28px; border: 1px solid #30363d; padding: 30px; }
    
    @media (max-width: 768px) {
        .bento-card-green { height: auto; padding: 20px; margin-bottom: 15px; }
        .card-value { font-size: 28px; }
        .bento-card-dark { margin-bottom: 15px; }
    }
</style>
""", unsafe_allow_html=True)

# 3. KONEKSI GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="Transaksi", ttl=5)

try:
    df = load_data()
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()

# 4. INISIALISASI SESSION STATE
if 'input_deskripsi' not in st.session_state: st.session_state['input_deskripsi'] = ""
if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = None
if 'input_ket' not in st.session_state: st.session_state['input_ket'] = ""
if 'message' not in st.session_state: st.session_state['message'] = None

# Default Values Logic Interaktif
if 'input_tipe' not in st.session_state: st.session_state['input_tipe'] = "Pengeluaran"
if 'input_status' not in st.session_state: st.session_state['input_status'] = "Lunas"

# 5. FUNGSI CALLBACK SIMPAN DATA
def add_transaction():
    desk = st.session_state.input_deskripsi
    amt = st.session_state.input_nominal
    date = st.session_state.input_tanggal
    cat = st.session_state.input_kategori
    tip = st.session_state.input_tipe
    sta = st.session_state.input_status
    ket = st.session_state.input_ket
    
    if sta == "Belum Lunas":
        met = "-"
    else:
        met = st.session_state.get("input_metode", "-")

    if not desk or amt is None:
        st.session_state['message'] = {"type": "error", "text": "Isi Deskripsi dan Nominal ya!"}
        return

    try:
        current_df = conn.read(worksheet="Transaksi", ttl=0)
        new_row = pd.DataFrame([{
            "Tanggal": date.strftime("%Y-%m-%d"),
            "Item": desk, "Kategori": cat, "Nominal": amt,
            "Tipe": tip, "Status": sta, "Keterangan": ket, "Metode Pembayaran": met
        }])
        updated_df = pd.concat([current_df, new_row], ignore_index=True)
        conn.update(worksheet="Transaksi", data=updated_df)
        
        st.session_state.input_deskripsi = ""
        st.session_state.input_nominal = None
        st.session_state.input_ket = ""
        st.session_state['message'] = {"type": "success", "text": "Transaksi Berhasil Dicatat!"}
        st.cache_data.clear()
    except Exception as e:
        st.session_state['message'] = {"type": "error", "text": f"Gagal simpan: {e}"}

# 6. HEADER & METRICS
st.markdown("<h2 style='margin-bottom:20px;'>🍱 Budget Bento Pro</h2>", unsafe_allow_html=True)

if not df.empty:
    df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce').fillna(0)
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df = df.dropna(subset=['Tanggal'])
    
    total_in = df[df['Tipe'] == 'Pemasukan']['Nominal'].sum()
    total_out = df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()
    balance = total_in - total_out
    
    col_m, col_s = st.columns([1.8, 1.2])
    
    with col_m:
        st.markdown(f"""
        <div class="bento-card-green">
            <div>
                <div class="card-label">Total Saldo Tersedia</div>
                <div class="card-value">Rp {balance:,.0f}</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="background:rgba(255,255,255,0.15); padding: 5px 15px; border-radius: 12px; font-size: 13px;">
                   📅 {datetime.now().strftime('%B %Y')}
                </span>
                <span style="font-size: 24px;">💰</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_s:
        st.markdown(f"""
        <div class="bento-card-dark" style="margin-bottom: 15px;">
            <div class="card-label">📈 Pemasukan</div>
            <div class="card-value-small" style="color: #4ade80;">+ Rp {total_in:,.0f}</div>
        </div>
        <div class="bento-card-dark">
            <div class="card-label">📉 Pengeluaran</div>
            <div class="card-value-small" style="color: #f87171;">- Rp {total_out:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("") 

# 7. FORM INPUT (LAYOUT UPDATE SESUAI REFERENSI)
with st.expander("➕ Tambah Transaksi Baru", expanded=True):
    # Layout 3 Kolom
    c1, c2, c3 = st.columns(3)
    
    # --- KOLOM 1: Tanggal, Kategori, Tipe ---
    with c1:
        st.date_input("Tanggal", datetime.today(), key="input_tanggal")
        
        # Logic Kategori (diambil dari Tipe session state agar update realtime)
        # Kita panggil session_state karena widget Radio ada di bawah, 
        # tapi logic harus jalan duluan.
        current_tipe = st.session_state.get("input_tipe", "Pengeluaran")
        
        if current_tipe == "Pemasukan":
            kategori_list = ["Gaji", "Bonus", "Hadiah", "Investasi", "Penjualan", "Lainnya"]
        else:
            kategori_list = ["Makan", "Transport", "Hiburan", "Tagihan", "Belanja", "Kesehatan", "Pendidikan", "Lainnya"]
        
        st.selectbox("Kategori", kategori_list, key="input_kategori")
        
        # Radio Tipe ditaruh di bawah Kategori (sesuai gambar referensi)
        st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key="input_tipe")

    # --- KOLOM 2: Metode, Nominal, Deskripsi ---
    with c2:
        # Logic Status menentukan Metode Pembayaran
        current_status = st.session_state.get("input_status", "Lunas")
        
        if current_status == "Belum Lunas":
            st.text_input("Metode Pembayaran", value="-", disabled=True, key="input_metode_disabled")
        else:
            metode_list = ["Cash", "Livin (Mandiri)", "Octo (CIMB)", "DANA", "Shopeepay"]
            st.selectbox("Metode Pembayaran", metode_list, key="input_metode")
            
        st.number_input("Nominal (Rp)", min_value=0, step=1000, value=None, key="input_nominal")
        st.text_input("Deskripsi", key="input_deskripsi", placeholder="Cth: Beli Kopi")

    # --- KOLOM 3: Status, Keterangan ---
    with c3:
        st.radio("Status", ["Lunas", "Belum Lunas"], horizontal=True, key="input_status")
        st.text_area("Keterangan", key="input_ket", height=138, placeholder="Catatan tambahan")

    st.write("")
    # Tombol Simpan Full Width (Sesuai Request)
    st.button("SIMPAN DATA", type="primary", use_container_width=True, on_click=add_transaction)

# Notifikasi
if st.session_state['message']:
    msg = st.session_state['message']
    st.toast(msg['text'], icon="✅" if msg['type'] == 'success' else "⚠️")
    st.session_state['message'] = None

st.divider()

# 8. GRAFIK & ANALISIS
if not df.empty:
    tab1, tab2 = st.tabs(["📊 Analisis Visual", "📋 Riwayat Transaksi"])
    
    with tab1:
        cg1, cg2 = st.columns([2, 1])
        df_exp = df[df['Tipe'] == 'Pengeluaran'].copy()
        
        with cg1:
            st.subheader("Tren Pengeluaran Harian")
            
            now = datetime.today()
            start_date = now.replace(day=1)
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_date = now.replace(day=last_day)
            
            all_days = pd.DataFrame({'Tgl': pd.date_range(start=start_date, end=end_date)})
            all_days['Tgl'] = all_days['Tgl'].dt.normalize()
            
            if not df_exp.empty:
                df_exp['Tanggal'] = df_exp['Tanggal'].dt.normalize()
                daily_grouped = df_exp.groupby('Tanggal')['Nominal'].sum().reset_index()
                daily = pd.merge(all_days, daily_grouped, left_on='Tgl', right_on='Tanggal', how='left').fillna(0)
                daily['Label'] = daily['Tgl'].dt.strftime('%d')
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=daily['Label'], y=daily['Nominal'], name='Expense',
                    marker_color='rgba(255, 255, 255, 0.4)', showlegend=False
                ))
                
                fig.update_layout(
                    margin=dict(t=10, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat="Rp"),
                    xaxis=dict(showgrid=False, type='category', title="Tanggal")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Belum ada pengeluaran bulan ini.")

        with cg2:
            st.subheader("Kategori")
            if not df_exp.empty:
                cat = df_exp.groupby('Kategori')['Nominal'].sum().reset_index()
                fig_pie = px.pie(cat, values='Nominal', names='Kategori',
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(
                    showlegend=True, margin=dict(t=0, b=0, l=0, r=0),
                    paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.1)
                )
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("Riwayat Transaksi")
        view_df = df.sort_values(by='Tanggal', ascending=False).copy()
        view_df = view_df.fillna("None")
        view_df['Tanggal_Str'] = view_df['Tanggal'].apply(lambda x: x.strftime('%d-%b-%Y') if isinstance(x, datetime) else str(x))
        
        def style_rows(row):
            styles = [''] * len(row)
            try:
                idx_tipe = list(row.index).index('Tipe')
                if row.Tipe == 'Pemasukan': styles[idx_tipe] = 'color: #10B981; font-weight: bold;'
                elif row.Tipe == 'Pengeluaran': styles[idx_tipe] = 'color: #f87171;'
                
                idx_status = list(row.index).index('Status')
                if row.Status == 'Belum Lunas': 
                    styles[idx_status] = 'background-color: #FBBF24; color: black; font-weight: bold; border-radius: 5px;'
                elif row.Status == 'Lunas':
                    styles[idx_status] = 'background-color: #10B981; color: white; font-weight: bold; border-radius: 5px;'
            except: pass
            return styles

        st.dataframe(
            view_df.style.apply(style_rows, axis=1),
            column_order=("Tanggal_Str", "Item", "Nominal", "Kategori", "Tipe", "Status", "Metode Pembayaran"),
            hide_index=True, use_container_width=True,
            column_config={
                "Tanggal_Str": "Tanggal",
                "Nominal": st.column_config.NumberColumn(format="Rp %d")
            }
        )
else:
    st.info("👋 Halo! Data kamu masih kosong.")