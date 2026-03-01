import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from fpdf import FPDF
import calendar
from functools import lru_cache
import hashlib
import time
from io import BytesIO

# ============================================================
# 🚀 RETRY LOGIC UNTUK GOOGLE SHEETS CONNECTION
# ============================================================
def retry_gsheet_operation(func, max_retries=3, delay=2):
    """Retry operation jika ada connection error"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            # Check jika error adalah connection issue
            if any(keyword in error_msg for keyword in ['connection', 'timeout', 'remote', 'aborted']):
                if attempt < max_retries - 1:
                    wait_time = delay * (attempt + 1)  # Exponential backoff
                    st.warning(f"⚠️ Koneksi terputus, mencoba lagi dalam {wait_time} detik... (Percobaan {attempt + 2}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    st.error(f"❌ Gagal setelah {max_retries} percobaan. Silakan refresh halaman dan coba lagi.")
                    raise
            else:
                # Error lain, langsung raise
                raise
    return None

# ============================================================
# 🚀 OPTIMASI #1: SESSION STATE CACHING UNTUK DATA
# ============================================================
# Dengan caching ini, data hanya di-load 1x per session
# CRUD selanjutnya menggunakan cache lokal, hanya sync ke GSheets saat perlu

def init_session_state():
    """Initialize session state untuk cache data"""
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {
            'transaksi': None,
            'dompet': None,
            'target': None,
            'recurring': None,
            'last_update': None,
            'needs_refresh': True
        }
    if 'reset_key' not in st.session_state:
        st.session_state.reset_key = 0
    if 'filter_mode' not in st.session_state:
        st.session_state.filter_mode = 'monthly'  # 'monthly' or 'custom'

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Budget Bento Pro v15 Professional", page_icon="🍱", layout="wide")

# --- KONFIGURASI KATEGORI ---
KATEGORI_PEMASUKAN = ["Gaji", "Bonus", "Hadiah", "Pembayaran", "Penjualan", "Lainnya"]
KATEGORI_PENGELUARAN = ["Makan", "Jajan", "Belanja", "Hiburan", "Transport", "Kesehatan", "Tagihan", "Amal", "Lainnya"]
METODE_PEMBAYARAN = ["Cash", "Livin (Mandiri)", "Octo (CIMB)", "DANA", "Shopeepay", "Kartu Kredit"]
# START_DATE_MONITORING sudah tidak dipakai lagi, diganti dengan Tanggal Reset per Wallet

# 2. CUSTOM CSS (unchanged)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
        background-color: #0e0e0e;
    }
    
    .bento-card-green, .bento-card-red, .bento-card-dark, .bento-card-warning, .bento-card-blue {
        height: 160px; display: flex; flex-direction: column; justify-content: center;
        padding: 25px; border-radius: 24px; margin-bottom: 15px;
    }
    .bento-card-green { background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2); }
    .bento-card-red { background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%); color: white; box-shadow: 0 10px 30px rgba(239, 68, 68, 0.2); }
    .bento-card-dark { background-color: #1a1a1a; color: white; border: 1px solid rgba(255, 255, 255, 0.05); box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); }
    .bento-card-warning { background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: white; box-shadow: 0 10px 30px rgba(245, 158, 11, 0.2); }
    .bento-card-blue { background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); color: white; box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2); }

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

    .card-label { font-size: 13px; opacity: 0.9; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .card-value { font-size: 28px; font-weight: 700; margin-bottom: 0px;}
    .card-detail { font-size: 12px; opacity: 0.8; margin-top: 5px; }
    
    div.stButton > button { 
        border-radius: 12px; height: 50px; font-weight: 600; text-transform: uppercase;
        background-color: #2563EB !important; color: white !important; border: none !important;
    }
    div.stButton > button:hover { background-color: #1d4ed8 !important; box-shadow: 0 5px 15px rgba(37, 99, 235, 0.4); }
    
    section[data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #222; }
    [data-testid="stForm"] { background-color: #161b22; border-radius: 24px; border: 1px solid #30363d; padding: 30px; }
    .streamlit-expanderHeader { background-color: #1a1a1a !important; border-radius: 12px !important; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🚀 OPTIMASI #2: SMART DATA LOADING WITH CACHE
# ============================================================

# 3. KONEKSI DATA
conn = st.connection("gsheets", type=GSheetsConnection)

init_session_state()

def load_data_from_sheets():
    """Load data dari Google Sheets - cache dikelola di session state"""
    try:
        transaksi = conn.read(worksheet="Transaksi", ttl=0)
        dompet = conn.read(worksheet="Dompet", ttl=0)
        
        try:
            target = conn.read(worksheet="Target", ttl=0)
            if target.empty:
                target = pd.DataFrame(columns=['Nama Impian', 'Target Harga', 'Dana Terkumpul'])
            else:
                target['Nama Impian'] = target['Nama Impian'].fillna("").astype(str)
                target['Target Harga'] = pd.to_numeric(target['Target Harga'], errors='coerce').fillna(0)
                target['Dana Terkumpul'] = pd.to_numeric(target['Dana Terkumpul'], errors='coerce').fillna(0)
        except:
            target = pd.DataFrame(columns=['Nama Impian', 'Target Harga', 'Dana Terkumpul'])
            target['Nama Impian'] = target['Nama Impian'].astype(str)
        
        # 🚀 NEW: Load Recurring Transactions
        try:
            recurring = conn.read(worksheet="Recurring", ttl=0)
            if recurring.empty:
                recurring = pd.DataFrame(columns=['Nama Item', 'Kategori', 'Nominal', 'Tipe', 'Metode Pembayaran', 'Frekuensi', 'Tanggal Mulai', 'Status'])
            else:
                recurring['Nominal'] = pd.to_numeric(recurring['Nominal'], errors='coerce').fillna(0)
                recurring['Tanggal Mulai'] = pd.to_datetime(recurring['Tanggal Mulai'], errors='coerce')
        except:
            recurring = pd.DataFrame(columns=['Nama Item', 'Kategori', 'Nominal', 'Tipe', 'Metode Pembayaran', 'Frekuensi', 'Tanggal Mulai', 'Status'])
        
        # 🚀 OPTIMASI: Prepare data types sekali saja
        if not transaksi.empty:
            transaksi['Tanggal'] = pd.to_datetime(transaksi['Tanggal'], errors='coerce')
            transaksi['Nominal'] = pd.to_numeric(transaksi['Nominal'], errors='coerce').fillna(0)
            # 🚀 OPTIMASI: Pre-compute month dan year untuk filtering cepat
            transaksi['Month'] = transaksi['Tanggal'].dt.month_name()
            transaksi['Year'] = transaksi['Tanggal'].dt.year
        
        if not dompet.empty:
            dompet['Saldo Awal'] = pd.to_numeric(dompet['Saldo Awal'], errors='coerce').fillna(0)
            # 🚀 PERBAIKAN: Tambah kolom Tanggal Reset jika belum ada
            if 'Tanggal Reset' not in dompet.columns:
                dompet['Tanggal Reset'] = datetime.today().strftime('%Y-%m-%d')
            # Parse Tanggal Reset
            dompet['Tanggal Reset'] = pd.to_datetime(dompet['Tanggal Reset'], errors='coerce')
            # Jika ada yang NaT, set ke hari ini
            dompet['Tanggal Reset'] = dompet['Tanggal Reset'].fillna(pd.Timestamp.today())
            
        return transaksi, dompet, target, recurring
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def get_cached_data(force_refresh=False):
    """Get data dari cache atau load baru jika perlu"""
    if force_refresh or st.session_state.data_cache['needs_refresh']:
        df, df_wallet, df_target, df_recurring = load_data_from_sheets()
        st.session_state.data_cache['transaksi'] = df
        st.session_state.data_cache['dompet'] = df_wallet
        st.session_state.data_cache['target'] = df_target
        st.session_state.data_cache['recurring'] = df_recurring
        st.session_state.data_cache['last_update'] = datetime.now()
        st.session_state.data_cache['needs_refresh'] = False
    
    return (
        st.session_state.data_cache['transaksi'],
        st.session_state.data_cache['dompet'],
        st.session_state.data_cache['target'],
        st.session_state.data_cache['recurring']
    )

# ============================================================
# 🚀 OPTIMASI #3: EFFICIENT CRUD OPERATIONS
# ============================================================

def add_transaction_optimized(new_data_dict):
    """Add transaction dengan operasi yang dioptimasi"""
    try:
        # Gunakan cache lokal, jangan fetch dari sheets lagi
        df = st.session_state.data_cache['transaksi'].copy()
        
        # 🚀 OPTIMASI: Gunakan DataFrame.loc untuk append, lebih cepat dari concat
        new_row = pd.DataFrame([new_data_dict])
        
        # Prepare new row data types
        new_row['Tanggal'] = pd.to_datetime(new_row['Tanggal'])
        new_row['Nominal'] = pd.to_numeric(new_row['Nominal'])
        new_row['Month'] = new_row['Tanggal'].dt.month_name()
        new_row['Year'] = new_row['Tanggal'].dt.year
        
        # Efficient append
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Update cache lokal dulu
        st.session_state.data_cache['transaksi'] = df
        
        # Prepare untuk sync ke Google Sheets (hapus computed columns)
        df_to_save = df.drop(columns=['Month', 'Year'], errors='ignore').copy()
        df_to_save['Tanggal'] = pd.to_datetime(df_to_save['Tanggal']).dt.strftime('%Y-%m-%d')
        
        # Sync ke Google Sheets dengan retry logic
        def update_operation():
            return conn.update(worksheet="Transaksi", data=df_to_save)
        
        retry_gsheet_operation(update_operation, max_retries=3, delay=1)
        
        return True, "Data berhasil disimpan!"
    except Exception as e:
        return False, f"Error: {e}"

def update_transactions_batch(updated_df, month_filter, year_filter):
    """Update multiple transactions sekaligus (batch operation)"""
    try:
        # Get full data dari cache
        orig = st.session_state.data_cache['transaksi'].copy()
        
        # Filter rows yang tidak diubah
        mask = (orig['Month'] == month_filter) & (orig['Year'] == year_filter)
        orig_kept = orig[~mask].copy()
        
        # Prepare updated data
        updated_clean = updated_df.copy()
        updated_clean['Tanggal'] = pd.to_datetime(updated_clean['Tanggal'])
        updated_clean['Month'] = updated_clean['Tanggal'].dt.month_name()
        updated_clean['Year'] = updated_clean['Tanggal'].dt.year
        
        # Combine
        final_df = pd.concat([orig_kept, updated_clean], ignore_index=True)
        
        # Update cache
        st.session_state.data_cache['transaksi'] = final_df
        
        # Sync ke Google Sheets dengan retry logic
        df_to_save = final_df.drop(columns=['Month', 'Year'], errors='ignore').copy()
        df_to_save['Tanggal'] = pd.to_datetime(df_to_save['Tanggal']).dt.strftime('%Y-%m-%d')
        
        def update_operation():
            return conn.update(worksheet="Transaksi", data=df_to_save)
        
        retry_gsheet_operation(update_operation, max_retries=3, delay=1)
        
        return True, "Batch update berhasil!"
    except Exception as e:
        return False, f"Error: {e}"

# ============================================================
# 🚀 OPTIMASI #4: EFFICIENT FILTERING WITH INDEXING
# ============================================================

@lru_cache(maxsize=128)
def get_month_year_filter(month_name, year_val):
    """Cache filter results untuk kombinasi month+year yang sama"""
    return (month_name, year_val)

def filter_data_efficient(df, month, year):
    """Filter data dengan operasi yang lebih cepat"""
    if df.empty:
        return df
    
    # 🚀 OPTIMASI: Gunakan boolean indexing langsung, sudah pre-computed
    mask = (df['Month'] == month) & (df['Year'] == year)
    return df.loc[mask].copy()

def search_transactions_optimized(df, keyword="", tipe_filter=None, kategori_filter=None):
    """Search dengan optimasi untuk performa lebih baik"""
    if df.empty:
        return df
    
    result = df.copy()
    
    # 🚀 OPTIMASI: Apply filters secara berurutan, bukan create multiple masks
    if keyword:
        # Gunakan vectorized string operations
        mask = result['Item'].str.contains(keyword, case=False, na=False) | \
               result['Keterangan'].str.contains(keyword, case=False, na=False)
        result = result[mask]
    
    if tipe_filter:
        result = result[result['Tipe'].isin(tipe_filter)]
    
    if kategori_filter:
        result = result[result['Kategori'].isin(kategori_filter)]
    
    return result

# ============================================================
# 🚀 PHASE 1: PROFESSIONAL FEATURES
# ============================================================

def filter_by_date_range(df, start_date, end_date):
    """Filter data berdasarkan custom date range"""
    if df.empty:
        return df
    mask = (df['Tanggal'] >= pd.Timestamp(start_date)) & (df['Tanggal'] <= pd.Timestamp(end_date))
    return df.loc[mask].copy()

def create_sankey_diagram(df_filtered):
    """Buat Sankey diagram untuk Cash Flow visualization"""
    if df_filtered.empty:
        return None
    
    # Prepare data untuk Sankey
    # Source: Kategori Pemasukan -> Target: Kategori Pengeluaran
    income_data = df_filtered[df_filtered['Tipe'] == 'Pemasukan'].groupby('Kategori')['Nominal'].sum()
    expense_data = df_filtered[df_filtered['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Nominal'].sum()
    
    if income_data.empty or expense_data.empty:
        return None
    
    # Build nodes
    source_nodes = list(income_data.index)
    target_nodes = list(expense_data.index)
    all_nodes = source_nodes + ["💰 Total Pemasukan"] + target_nodes
    
    # Build links
    sources = []
    targets = []
    values = []
    colors = []
    
    # Pemasukan -> Total
    for i, cat in enumerate(source_nodes):
        sources.append(i)
        targets.append(len(source_nodes))
        values.append(income_data[cat])
        colors.append('rgba(16, 185, 129, 0.4)')
    
    # Total -> Pengeluaran
    total_income = income_data.sum()
    total_expense = expense_data.sum()
    proportion = total_expense / total_income if total_income > 0 else 0
    
    for i, cat in enumerate(target_nodes):
        sources.append(len(source_nodes))
        targets.append(len(source_nodes) + 1 + i)
        values.append(expense_data[cat])
        colors.append('rgba(239, 68, 68, 0.4)')
    
    # Create Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color=['#10B981'] * len(source_nodes) + ['#3B82F6'] + ['#EF4444'] * len(target_nodes)
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors
        )
    )])
    
    fig.update_layout(
        title="💸 Cash Flow: Dari Mana & Ke Mana Uang Mengalir",
        font=dict(size=10, color='white'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    
    return fig

def create_budget_vs_actual_chart(df_filtered, budget_dict):
    """Buat chart Budget vs Actual spending per kategori"""
    if df_filtered.empty:
        return None
    
    actual = df_filtered[df_filtered['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Nominal'].sum()
    
    categories = list(budget_dict.keys())
    budget_values = [budget_dict[cat] for cat in categories]
    actual_values = [actual.get(cat, 0) for cat in categories]
    variance = [actual_values[i] - budget_values[i] for i in range(len(categories))]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Budget',
        x=categories,
        y=budget_values,
        marker_color='rgba(59, 130, 246, 0.6)',
        text=[f'Rp {v:,.0f}' for v in budget_values],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Aktual',
        x=categories,
        y=actual_values,
        marker_color=['rgba(239, 68, 68, 0.6)' if v > budget_values[i] else 'rgba(16, 185, 129, 0.6)' 
                      for i, v in enumerate(actual_values)],
        text=[f'Rp {v:,.0f}' for v in actual_values],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='📊 Budget vs Actual Spending',
        xaxis_title=None,
        yaxis_title='Rupiah',
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def export_to_excel(df, df_wallet, df_target, start_date, end_date):
    """Export data ke Excel dengan format profesional"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = {
            'Periode': [f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"],
            'Total Pemasukan': [df[df['Tipe'] == 'Pemasukan']['Nominal'].sum()],
            'Total Pengeluaran': [df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()],
            'Net Cash Flow': [df[df['Tipe'] == 'Pemasukan']['Nominal'].sum() - df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()],
            'Jumlah Transaksi': [len(df)],
            'Tanggal Export': [datetime.now().strftime('%d %b %Y %H:%M')]
        }
        pd.DataFrame(summary_data).T.to_excel(writer, sheet_name='Summary', header=False)
        
        # Sheet 2: All Transactions
        df_export = df.drop(columns=['Month', 'Year'], errors='ignore').copy()
        df_export['Tanggal'] = pd.to_datetime(df_export['Tanggal']).dt.strftime('%Y-%m-%d')
        df_export.to_excel(writer, sheet_name='Transaksi', index=False)
        
        # Sheet 3: Pemasukan
        df_income = df[df['Tipe'] == 'Pemasukan'].drop(columns=['Month', 'Year'], errors='ignore').copy()
        if not df_income.empty:
            df_income['Tanggal'] = pd.to_datetime(df_income['Tanggal']).dt.strftime('%Y-%m-%d')
            df_income.to_excel(writer, sheet_name='Pemasukan', index=False)
        
        # Sheet 4: Pengeluaran
        df_expense = df[df['Tipe'] == 'Pengeluaran'].drop(columns=['Month', 'Year'], errors='ignore').copy()
        if not df_expense.empty:
            df_expense['Tanggal'] = pd.to_datetime(df_expense['Tanggal']).dt.strftime('%Y-%m-%d')
            df_expense.to_excel(writer, sheet_name='Pengeluaran', index=False)
        
        # Sheet 5: Per Kategori
        category_summary = df.groupby(['Kategori', 'Tipe'])['Nominal'].sum().reset_index()
        category_summary.to_excel(writer, sheet_name='Per Kategori', index=False)
        
        # Sheet 6: Wallet Balance
        df_wallet.to_excel(writer, sheet_name='Saldo Dompet', index=False)
        
        # Sheet 7: Targets
        if not df_target.empty:
            df_target.to_excel(writer, sheet_name='Target Impian', index=False)
    
    output.seek(0)
    return output

# Load data awal
df, df_wallet_initial, df_target, df_recurring_initial = get_cached_data()

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.title("🍱 Bento Pro v15")
    st.caption("🚀 PROFESSIONAL EDITION")
    st.markdown("<small style='opacity:0.6'>✨ Phase 1 Features Active</small>", unsafe_allow_html=True)
    
    # Check if there's a navigation request
    default_index = 0
    menu_options = ["🏠 Dashboard", "👛 Dompet Saya", "💰 Budget Planner", "🔄 Transaksi Rutin", "🎯 Target Impian", "📁 Data Lengkap"]
    
    if 'goto_menu' in st.session_state:
        target_menu = st.session_state['goto_menu']
        if target_menu in menu_options:
            default_index = menu_options.index(target_menu)
        del st.session_state['goto_menu']
    
    selected_menu = st.radio(
        "Menu Aplikasi", 
        menu_options,
        index=default_index
    )
    
    st.divider()
    
    # FILTER GLOBAL - ENHANCED WITH CUSTOM DATE RANGE
    st.subheader("📅 Filter Periode")
    
    # Toggle between Monthly and Custom Range
    filter_mode = st.radio(
        "Mode Filter:",
        ["📆 Per Bulan", "📅 Custom Range"],
        horizontal=True,
        key="filter_mode_radio"
    )
    
    now = datetime.now()
    current_year = now.year
    current_month_name = now.strftime('%B')
    
    if filter_mode == "📆 Per Bulan":
        st.session_state.filter_mode = 'monthly'
        
        if not df.empty:
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
        
        # Set default date range untuk monthly mode
        month_idx = list(calendar.month_name).index(selected_month)
        start_date = datetime(selected_year, month_idx, 1)
        last_day = calendar.monthrange(selected_year, month_idx)[1]
        end_date = datetime(selected_year, month_idx, last_day)
    
    else:  # Custom Range
        st.session_state.filter_mode = 'custom'
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Dari Tanggal",
                value=datetime(now.year, now.month, 1),
                key="custom_start"
            )
        with col2:
            end_date = st.date_input(
                "Sampai Tanggal",
                value=now,
                key="custom_end"
            )
        
        # Convert to datetime for consistency
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())
        
        # Set dummy values for monthly variables (not used in custom mode)
        selected_year = start_date.year
        selected_month = start_date.strftime('%B')
    
    # Show cache status
    st.divider()
    if st.session_state.data_cache['last_update']:
        last_update_str = st.session_state.data_cache['last_update'].strftime('%H:%M:%S')
        st.caption(f"🔄 Cache: {last_update_str}")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        df, df_wallet_initial, df_target, df_recurring_initial = get_cached_data(force_refresh=True)
        st.rerun()

# ==========================================
# LOGIC SCREEN
# ==========================================

# ---------------- SCREEN 1: DASHBOARD ----------------
if selected_menu == "🏠 Dashboard":
    st.title("🏠 Dashboard Utama")
    
    # Display period info
    if st.session_state.filter_mode == 'custom':
        period_text = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
    else:
        period_text = f"{selected_month} {selected_year}"
    
    st.markdown(f"<span style='font-size:16px; opacity:0.5; margin-left:10px'>{period_text}</span>", unsafe_allow_html=True)
    
    if not df.empty:
        # 🚀 NEW: Use flexible filtering based on mode
        if st.session_state.filter_mode == 'custom':
            df_filtered = filter_by_date_range(df, start_date, end_date)
        else:
            df_filtered = filter_data_efficient(df, selected_month, selected_year)

        # 🚀 OPTIMASI: Compute aggregations sekali saja
        global_in = df[df['Tipe'] == 'Pemasukan']['Nominal'].sum()
        global_out = df[df['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        current_balance = global_in - global_out 

        period_in = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
        period_out = df_filtered[df_filtered['Tipe'] == 'Pengeluaran']['Nominal'].sum()
        
        df_utang = df[df['Status'] == 'Belum Lunas']
        total_utang = df_utang['Nominal'].sum()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""<div class="bento-card-blue"><div><div class="card-label">💰 Sisa Saldo (Real)</div><div class="card-value">Rp {current_balance:,.0f}</div></div><div class="card-detail">Total Aset di Semua Dompet</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="bento-card-green"><div><div class="card-label">📈 Pemasukan (Periode)</div><div class="card-value">+ Rp {period_in:,.0f}</div></div></div>""", unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"""<div class="bento-card-red"><div><div class="card-label">📉 Pengeluaran (Periode)</div><div class="card-value">- Rp {period_out:,.0f}</div></div></div>""", unsafe_allow_html=True)
            with st.popover("Lihat Rincian Dompet 💳", use_container_width=True):
                if period_out > 0:
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
    
    # TOAST NOTIFICATION
    if 'sukses_simpan' in st.session_state:
        st.toast(f"✅ Tersimpan: {st.session_state['sukses_simpan']}", icon="🍱")
        del st.session_state['sukses_simpan']

    # INPUT TRANSAKSI (DENGAN OPTIMASI CRUD)
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
            input_nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000, value=None, key=f"in_nom_{st.session_state.reset_key}")
            
        with c3:
            input_deskripsi = st.text_input("Item", placeholder="Cth: Kopi / Gaji", key=f"in_desk_{st.session_state.reset_key}")
            input_ket = st.text_area("Ket", height=100, key=f"in_ket_{st.session_state.reset_key}")
            
        if st.button("💾 SIMPAN DATA", type="primary", width="stretch"):
            if not input_deskripsi or input_nominal is None or input_nominal <= 0:
                st.error("⚠️ Gagal: Nama Item harus diisi dan Nominal harus lebih dari 0!")
            else:
                # 🚀 OPTIMASI: Gunakan fungsi CRUD yang dioptimasi
                success, message = add_transaction_optimized({
                    "Tanggal": input_tanggal.strftime("%Y-%m-%d"),
                    "Item": input_deskripsi,
                    "Kategori": input_kategori,
                    "Nominal": input_nominal,
                    "Tipe": input_tipe,
                    "Status": input_status,
                    "Keterangan": input_ket,
                    "Metode Pembayaran": "-" if is_disabled else input_metode
                })
                
                if success:
                    st.session_state['sukses_simpan'] = input_deskripsi
                    st.session_state.reset_key += 1
                    # Reload dari cache yang sudah diupdate
                    df, df_wallet_initial, df_target, df_recurring_initial = get_cached_data()
                    st.rerun()
                else:
                    st.error(message)
    
    # 🚀 NEW: Excel Export Button - Positioned after Input Transaction
    if not df_filtered.empty:
        st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        col_left, col_export, col_right = st.columns([1, 2, 1])
        with col_export:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 10px;'>
                <span style='font-size: 14px; opacity: 0.7;'>📊 Export data periode ini ke format Excel</span>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📥 EXPORT KE EXCEL", type="secondary", use_container_width=True, key="export_main"):
                with st.spinner("⏳ Mempersiapkan file Excel..."):
                    excel_file = export_to_excel(df_filtered, df_wallet_initial, df_target, start_date, end_date)
                    st.download_button(
                        label="💾 Download File Excel",
                        data=excel_file,
                        file_name=f"BentoPro_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                    st.success("✅ File siap didownload!")
    
    st.divider()
    
    # 🚀 NEW: Cash Flow Sankey Diagram
    st.subheader("💸 Cash Flow: Dari Mana & Ke Mana Uang Mengalir")
    if not df.empty and not df_filtered.empty:
        sankey_fig = create_sankey_diagram(df_filtered)
        if sankey_fig:
            st.plotly_chart(sankey_fig, use_container_width=True)
        else:
            st.info("Tidak cukup data untuk menampilkan Cash Flow diagram. Pastikan ada data Pemasukan dan Pengeluaran.")
    else:
        st.info("Belum ada data untuk ditampilkan.")
    
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
            st.plotly_chart(fig, use_container_width=True)  # plotly_chart masih pakai use_container_width
            
        with c_graph2:
            cat = df_filtered[df_filtered['Tipe']=='Pengeluaran'].groupby('Kategori')['Nominal'].sum().reset_index()
            if not cat.empty:
                fig2 = px.pie(cat, values='Nominal', names='Kategori', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
                fig2.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=350, showlegend=True,
                                   legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                st.plotly_chart(fig2, use_container_width=True)  # plotly_chart masih pakai use_container_width
            else:
                st.caption("Belum ada data pengeluaran untuk chart ini.")

# ---------------- SCREEN 2: DOMPET SAYA ----------------
elif selected_menu == "👛 Dompet Saya":
    st.title("👛 Monitoring Dompet")
    
    if not df_wallet_initial.empty:
        # 🚀 PERBAIKAN: Hitung per wallet berdasarkan Tanggal Reset masing-masing
        live_wallets = df_wallet_initial.copy()
        
        # Inisialisasi kolom
        live_wallets['Total Masuk'] = 0.0
        live_wallets['Total Keluar'] = 0.0
        live_wallets['Saldo Sekarang'] = 0.0
        
        # Loop per wallet untuk hitung transaksi setelah Tanggal Reset
        for idx, wallet_row in live_wallets.iterrows():
            wallet_name = wallet_row['Wallet']
            reset_date = wallet_row['Tanggal Reset']
            
            # Filter transaksi setelah tanggal reset untuk wallet ini
            df_wallet_trans = df[(df['Tanggal'] >= reset_date) & (df['Metode Pembayaran'] == wallet_name)]
            
            # Hitung total masuk dan keluar
            total_in = df_wallet_trans[df_wallet_trans['Tipe'] == 'Pemasukan']['Nominal'].sum()
            total_out = df_wallet_trans[df_wallet_trans['Tipe'] == 'Pengeluaran']['Nominal'].sum()
            
            # Update dataframe
            live_wallets.at[idx, 'Total Masuk'] = total_in
            live_wallets.at[idx, 'Total Keluar'] = total_out
            live_wallets.at[idx, 'Saldo Sekarang'] = wallet_row['Saldo Awal'] + total_in - total_out
        
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
                reset_date_str = row['Tanggal Reset'].strftime('%d %b %Y')
                st.markdown(f"""
                <div class="wallet-card">
                    <div class="wallet-chip"></div>
                    <div class="wallet-name">{row['Wallet']}</div>
                    <div class="wallet-balance">Rp {row['Saldo Sekarang']:,.0f}</div>
                    <div style="font-size:10px; opacity:0.5; margin-top:5px;">Reset: {reset_date_str} | Awal: Rp {row['Saldo Awal']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    with st.expander("⚙️ Atur Saldo Awal (Gunakan saat sinkron ulang)"):
        st.info("💡 **Cara Reset:** Ubah 'Saldo Saat Ini' sesuai saldo RIIL dompet Anda SEKARANG (cek fisik atau cek app bank). Nilai ini akan menjadi saldo FINAL hari ini. Transaksi baru akan mulai dihitung BESOK.")
        st.warning("⚠️ Transaksi yang sudah tercatat hari ini TIDAK akan dihitung lagi setelah reset! Pastikan nilai yang Anda input sudah termasuk semua transaksi hari ini.")
        
        # Prepare dataframe untuk editor (tanpa Tanggal Reset)
        df_edit = df_wallet_initial[['Wallet', 'Saldo Awal']].copy()
        
        edited_wallets = st.data_editor(
            df_edit, 
            column_config={
                "Wallet": st.column_config.TextColumn(disabled=True),
                "Saldo Awal": st.column_config.NumberColumn("Saldo Saat Ini (Rp)", format="Rp %d", required=True)
            }, hide_index=True, use_container_width=True  # data_editor masih pakai use_container_width
        )
        
        if st.button("💾 Simpan & Reset Perhitungan", type="primary"):
            with st.spinner("⏳ Menyimpan data ke Google Sheets..."):
                try:
                    # 🚀 PERBAIKAN: Set Tanggal Reset ke BESOK agar transaksi hari ini tidak terhitung
                    tomorrow = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
                    edited_wallets['Tanggal Reset'] = tomorrow
                    
                    # Update ke Google Sheets dengan retry logic
                    def update_operation():
                        return conn.update(worksheet="Dompet", data=edited_wallets)
                    
                    retry_gsheet_operation(update_operation, max_retries=3, delay=2)
                    
                    # Update cache dengan parsing Tanggal Reset
                    edited_wallets['Tanggal Reset'] = pd.to_datetime(edited_wallets['Tanggal Reset'])
                    st.session_state.data_cache['dompet'] = edited_wallets
                    st.session_state.data_cache['needs_refresh'] = True
                    
                    st.success("✅ Saldo berhasil direset!")
                    st.info(f"💡 Nilai yang Anda input adalah saldo FINAL hari ini. Perhitungan transaksi baru dimulai besok ({tomorrow}).")
                    time.sleep(1)  # Beri waktu user baca message
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal update: {e}")
                    st.info("💡 **Tips jika gagal:**\n- Pastikan koneksi internet stabil\n- Refresh halaman dan coba lagi\n- Cek apakah Google Sheets masih dapat diakses")

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
            if st.button("📥 Catat Pemasukan", width="stretch"):
                success, message = add_transaction_optimized({
                    "Tanggal": datetime.today().strftime("%Y-%m-%d"),
                    "Item": "Gaji Bulanan",
                    "Kategori": "Gaji",
                    "Nominal": total_income,
                    "Tipe": "Pemasukan",
                    "Status": "Lunas",
                    "Keterangan": "Budget Planner",
                    "Metode Pembayaran": "Livin (Mandiri)"
                })
                if success:
                    st.toast("Gaji berhasil dicatat!", icon="✅")
                    df, df_wallet_initial, df_target, df_recurring_initial = get_cached_data()
                    st.rerun()
                else:
                    st.error(message)

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
    
    # 🚀 NEW: Budget vs Actual Comparison
    st.divider()
    st.subheader("📊 Budget vs Actual Spending")
    
    if not df.empty and allocations:
        # Use current period filter
        if st.session_state.filter_mode == 'custom':
            df_budget_period = filter_by_date_range(df, start_date, end_date)
        else:
            df_budget_period = filter_data_efficient(df, selected_month, selected_year)
        
        if not df_budget_period.empty:
            budget_chart = create_budget_vs_actual_chart(df_budget_period, allocations)
            if budget_chart:
                st.plotly_chart(budget_chart, use_container_width=True)
                
                # Show variance details
                with st.expander("📋 Lihat Detail Variance"):
                    actual = df_budget_period[df_budget_period['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Nominal'].sum()
                    
                    for cat in allocations.keys():
                        budget_val = allocations[cat]
                        actual_val = actual.get(cat, 0)
                        variance = actual_val - budget_val
                        variance_pct = (variance / budget_val * 100) if budget_val > 0 else 0
                        
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        with col1:
                            st.write(f"**{cat}**")
                        with col2:
                            st.write(f"Budget: Rp {budget_val:,.0f}")
                        with col3:
                            st.write(f"Aktual: Rp {actual_val:,.0f}")
                        with col4:
                            if variance > 0:
                                st.error(f"🔴 +{variance_pct:.1f}%")
                            elif variance < 0:
                                st.success(f"🟢 {variance_pct:.1f}%")
                            else:
                                st.info("⚪ 0%")
            else:
                st.info("Belum ada data pengeluaran untuk perbandingan.")
        else:
            st.info("Belum ada transaksi di periode ini.")
    else:
        st.info("Atur budget terlebih dahulu untuk melihat perbandingan.")

# ---------------- SCREEN 4: TRANSAKSI RUTIN (RECURRING) ----------------
elif selected_menu == "🔄 Transaksi Rutin":
    st.title("🔄 Transaksi Rutin (Recurring)")
    st.markdown("Kelola transaksi yang berulang setiap bulan seperti langganan, tagihan, atau gaji tetap.")
    
    # Display existing recurring transactions
    if not df_recurring_initial.empty:
        st.subheader("📋 Daftar Transaksi Rutin")
        
        for i, row in df_recurring_initial.iterrows():
            status_color = "🟢" if row['Status'] == 'Aktif' else "🔴"
            tipe_icon = "📈" if row['Tipe'] == 'Pemasukan' else "📉"
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"### {tipe_icon} {row['Nama Item']}")
                    st.caption(f"Kategori: {row['Kategori']} • {row['Metode Pembayaran']}")
                with col2:
                    st.markdown(f"**Rp {row['Nominal']:,.0f}**")
                    st.caption(f"Frekuensi: {row['Frekuensi']}")
                with col3:
                    st.markdown(f"{status_color} {row['Status']}")
                    if row['Tanggal Mulai']:
                        st.caption(f"Mulai: {row['Tanggal Mulai'].strftime('%d/%m/%Y')}")
    else:
        st.info("Belum ada transaksi rutin yang dicatat.")
    
    st.divider()
    
    # Add new recurring transaction
    with st.expander("➕ Tambah Transaksi Rutin Baru", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rec_nama = st.text_input("Nama Item", placeholder="Cth: Netflix, Listrik, Gaji", key="rec_nama")
            rec_tipe = st.radio("Tipe", ["Pengeluaran", "Pemasukan"], horizontal=True, key="rec_tipe")
            rec_cats = KATEGORI_PEMASUKAN if rec_tipe == "Pemasukan" else KATEGORI_PENGELUARAN
            rec_kategori = st.selectbox("Kategori", rec_cats, key="rec_kat")
        
        with col2:
            rec_nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000, key="rec_nominal")
            rec_metode = st.selectbox("Metode Pembayaran", METODE_PEMBAYARAN, key="rec_metode")
            rec_frekuensi = st.selectbox("Frekuensi", ["Bulanan", "Mingguan", "Tahunan"], key="rec_freq")
        
        with col3:
            rec_start = st.date_input("Tanggal Mulai", datetime.today(), key="rec_start")
            rec_status = st.radio("Status", ["Aktif", "Nonaktif"], horizontal=True, key="rec_status")
        
        if st.button("💾 Simpan Transaksi Rutin", type="primary", use_container_width=True):
            if not rec_nama or rec_nominal <= 0:
                st.error("⚠️ Nama dan Nominal harus diisi!")
            else:
                try:
                    # Add to recurring dataframe
                    new_recurring = pd.DataFrame([{
                        'Nama Item': rec_nama,
                        'Kategori': rec_kategori,
                        'Nominal': rec_nominal,
                        'Tipe': rec_tipe,
                        'Metode Pembayaran': rec_metode,
                        'Frekuensi': rec_frekuensi,
                        'Tanggal Mulai': rec_start.strftime('%Y-%m-%d'),
                        'Status': rec_status
                    }])
                    
                    df_recurring_updated = pd.concat([df_recurring_initial, new_recurring], ignore_index=True)
                    
                    # Update to Google Sheets
                    def update_operation():
                        return conn.update(worksheet="Recurring", data=df_recurring_updated)
                    
                    retry_gsheet_operation(update_operation, max_retries=3, delay=1)
                    
                    # Update cache
                    st.session_state.data_cache['recurring'] = df_recurring_updated
                    
                    st.success(f"✅ Transaksi rutin '{rec_nama}' berhasil ditambahkan!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan: {e}")
    
    # Manage existing recurring transactions
    if not df_recurring_initial.empty:
        st.divider()
        with st.expander("⚙️ Kelola Transaksi Rutin"):
            st.info("💡 Edit transaksi rutin atau nonaktifkan jika sudah tidak berlaku.")
            
            edited_recurring = st.data_editor(
                df_recurring_initial,
                column_config={
                    "Nama Item": st.column_config.TextColumn("Nama Item", required=True),
                    "Nominal": st.column_config.NumberColumn("Nominal (Rp)", format="Rp %d", required=True),
                    "Tipe": st.column_config.SelectboxColumn("Tipe", options=["Pemasukan", "Pengeluaran"]),
                    "Kategori": st.column_config.SelectboxColumn("Kategori", options=KATEGORI_PEMASUKAN + KATEGORI_PENGELUARAN),
                    "Metode Pembayaran": st.column_config.SelectboxColumn("Metode", options=METODE_PEMBAYARAN),
                    "Frekuensi": st.column_config.SelectboxColumn("Frekuensi", options=["Bulanan", "Mingguan", "Tahunan"]),
                    "Tanggal Mulai": st.column_config.DateColumn("Tanggal Mulai", format="DD/MM/YYYY"),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Aktif", "Nonaktif"])
                },
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                key="recurring_editor"
            )
            
            if st.button("💾 Simpan Perubahan", type="primary"):
                try:
                    def update_operation():
                        return conn.update(worksheet="Recurring", data=edited_recurring)
                    
                    retry_gsheet_operation(update_operation, max_retries=3, delay=1)
                    
                    st.session_state.data_cache['recurring'] = edited_recurring
                    st.success("✅ Perubahan berhasil disimpan!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan: {e}")

# ---------------- SCREEN 5: TARGET IMPIAN ----------------
elif selected_menu == "🎯 Target Impian":
    st.title("🎯 Target & Wishlist")
    st.markdown("Pantau progress tabunganmu untuk mencapai impian besar (Gadget, Liburan, Kendaraan, dll).")
    
    if not df_target.empty:
        for i, row in df_target.iterrows():
            nama = row['Nama Impian']
            harga = row['Target Harga']
            kumpul = row['Dana Terkumpul']
            
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
            st.progress(pct)
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
            use_container_width=True,  # data_editor masih pakai use_container_width
            key="target_editor"
        )
        if st.button("💾 Simpan Target", type="primary"):
            with st.spinner("⏳ Menyimpan ke Google Sheets..."):
                try:
                    def update_operation():
                        return conn.update(worksheet="Target", data=edited_target)
                    
                    retry_gsheet_operation(update_operation, max_retries=3, delay=1)
                    
                    st.session_state.data_cache['target'] = edited_target
                    st.success("✅ Target impian berhasil diperbarui!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan target: {e}")
                    st.info("💡 Refresh halaman dan coba lagi jika koneksi bermasalah.")

# ---------------- SCREEN 6: DATA LENGKAP & EXPORT ----------------
elif selected_menu == "📁 Data Lengkap":
    st.title("📁 Data Lengkap & Laporan")
    
    if not df.empty:
        # 🚀 OPTIMASI: Gunakan fungsi filter yang efisien
        df_filtered_view = filter_data_efficient(df, selected_month, selected_year).sort_values('Tanggal', ascending=False)
    else:
        df_filtered_view = pd.DataFrame()

    # E-STATEMENT PDF
    if not df_filtered_view.empty:
        st.markdown("### 📥 Download E-Statement (PDF)")
        st.caption(f"Cetak laporan resmi keuanganmu ala Bank untuk bulan {selected_month} {selected_year}.")
        
        def create_pdf(df_laporan, month, year):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(37, 99, 235)
            pdf.cell(0, 8, "BENTO PRO OPTIMIZED", ln=True, align='R')
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "PERSONAL FINANCE STATEMENT", ln=True, align='R')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, "Laporan Rekening / Statement of Account", ln=True, align='L')
            
            month_idx = list(calendar.month_name).index(month)
            last_day = calendar.monthrange(int(year), month_idx)[1]
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 6, f"Periode: 01 {month} {year} - {last_day} {month} {year}", ln=True, align='L')
            pdf.ln(5)
            
            pdf.set_font("Arial", '', 10)
            pdf.cell(30, 6, "Jenis Produk", border=0)
            pdf.cell(0, 6, ": Bento Finance Tracker", border=0, ln=True)
            pdf.cell(30, 6, "Nama", border=0)
            pdf.cell(0, 6, ": Pengguna Utama", border=0, ln=True)
            pdf.cell(30, 6, "Mata Uang", border=0)
            pdf.cell(0, 6, ": IDR", border=0, ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(37, 99, 235)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 8, "Tanggal", border=1, fill=True, align='C')
            pdf.cell(75, 8, "Deskripsi", border=1, fill=True, align='C')
            pdf.cell(30, 8, "Debit", border=1, fill=True, align='C')
            pdf.cell(30, 8, "Kredit", border=1, fill=True, align='C')
            pdf.cell(35, 8, "Saldo", border=1, fill=True, align='C')
            pdf.ln()
            
            df_sorted = df_laporan.sort_values('Tanggal', ascending=True).copy()
            pdf.set_font("Arial", '', 8)
            pdf.set_text_color(0, 0, 0)
            running_balance = 0
            total_kredit = 0
            total_debit = 0
            
            for i, row in df_sorted.iterrows():
                tgl = pd.to_datetime(row['Tanggal']).strftime('%d/%m/%Y')
                desc_raw = f"{row['Item']} ({row['Metode Pembayaran']})"
                desc = desc_raw[:45]
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
                pdf.cell(20, 7, tgl, border=1, align='C')
                pdf.cell(75, 7, desc, border=1, align='L')
                pdf.cell(30, 7, debit_str, border=1, align='R')
                pdf.cell(30, 7, kredit_str, border=1, align='R')
                pdf.cell(35, 7, saldo_str, border=1, align='R')
                pdf.ln()

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(40, 6, "Total Debit", border=0)
            pdf.cell(50, 6, f"IDR {total_debit:,.2f}", border=0, ln=True)
            pdf.cell(40, 6, "Total Kredit", border=0)
            pdf.cell(50, 6, f"IDR {total_kredit:,.2f}", border=0, ln=True)
            pdf.cell(40, 6, "Net Saldo Bulan Ini", border=0)
            pdf.cell(50, 6, f"IDR {running_balance:,.2f}", border=0, ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'I', 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, "IMPORTANT!", ln=True)
            pdf.cell(0, 5, "Dokumen e-statement ini di-generate secara otomatis oleh sistem aplikasi Bento Pro.", ln=True)
            pdf.cell(0, 5, "Data keuangan Anda bersifat rahasia. Jangan membagikannya dengan alasan apa pun.", ln=True)
            
            return pdf.output(dest='S').encode('latin-1')

        pdf_bytes = create_pdf(df_filtered_view, selected_month, selected_year)
        st.download_button(
            label="📄 Download E-Statement (.pdf)", data=pdf_bytes,
            file_name=f"E-Statement_BentoPro_{selected_month}_{selected_year}.pdf",
            mime="application/pdf", width="stretch"
        )
        st.divider()

    # TIGA TAB UTAMA
    tab_tabel, tab_cari, tab_utang = st.tabs(["📋 Tabel (Edit & Hapus)", "🔍 Cari & Filter", "💸 Kelola Utang"])

    # TAB 1: TABEL TRANSAKSI
    with tab_tabel:
        st.info("💡 **Cara Edit:** Klik sel untuk mengubah teks. **Cara Hapus:** Centang kotak paling kiri, lalu klik ikon 🗑️ di atas tabel. Jangan lupa klik Simpan.")
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
                num_rows="dynamic", hide_index=False, use_container_width=True, key="editor_transaksi_lengkap"  # data_editor masih pakai use_container_width
            )
            
            if st.button("💾 Simpan Perubahan Data", type="primary"):
                # 🚀 OPTIMASI: Gunakan batch update
                success, message = update_transactions_batch(edited_df, selected_month, selected_year)
                if success:
                    st.toast("✅ Perubahan tabel berhasil disimpan!", icon="🍱")
                    df, df_wallet_initial, df_target, df_recurring_initial = get_cached_data()
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.info("Data kosong.")

    # TAB 2: CARI & FILTER (OPTIMIZED)
    with tab_cari:
        st.markdown("### 🔍 Rekap & Pencarian Spesifik")
        
        search_global = st.toggle("🌍 Cari di seluruh riwayat data (semua bulan)", value=False)
        df_source = df.copy() if search_global else df_filtered_view.copy()
        
        if not df_source.empty:
            c1, c2, c3 = st.columns(3)
            with c1:
                cari_teks = st.text_input("Kata Kunci (Item / Ket)", placeholder="Cth: futsal, makan...")
            with c2:
                cari_tipe = st.multiselect("Filter Tipe", ["Pengeluaran", "Pemasukan"])
            with c3:
                semua_kat = list(dict.fromkeys(KATEGORI_PEMASUKAN + KATEGORI_PENGELUARAN))
                cari_kat = st.multiselect("Filter Kategori", semua_kat)
                
            # 🚀 OPTIMASI: Gunakan fungsi search yang dioptimasi
            df_result = search_transactions_optimized(df_source, cari_teks, cari_tipe, cari_kat)
                
            st.divider()
            
            # Hitung Total
            tot_in = df_result[df_result['Tipe'] == 'Pemasukan']['Nominal'].sum()
            tot_out = df_result[df_result['Tipe'] == 'Pengeluaran']['Nominal'].sum()
            jum_trans = len(df_result)
            
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("🟢 Total Pemasukan", f"Rp {tot_in:,.0f}")
            cc2.metric("🔴 Total Pengeluaran", f"Rp {tot_out:,.0f}")
            cc3.metric("📝 Jumlah Transaksi", f"{jum_trans} Transaksi")
            
            st.write("")
            
            cols_show = ["Tanggal", "Item", "Kategori", "Nominal", "Tipe", "Metode Pembayaran", "Keterangan"]
            st.dataframe(
                df_result[cols_show].sort_values('Tanggal', ascending=False),
                column_config={
                    "Tanggal": st.column_config.DateColumn("Tanggal", format="DD MMM YYYY"),
                    "Nominal": st.column_config.NumberColumn("Nominal", format="Rp %d")
                },
                hide_index=True, use_container_width=True  # data_editor masih pakai use_container_width
            )
        else:
            st.info("Belum ada data transaksi yang bisa dicari.")

    # TAB 3: TABEL UTANG
    with tab_utang:
        st.info("💡 Ubah Status ke **'Lunas'** DAN pilih **Metode Pembayaran** (sumber dana). Lalu klik Update.")
        st.caption("⚙️ Cara Kerja: Saat tanggungan dilunasi, saldo dompet yang dipilih akan otomatis berkurang sesuai nominal utang.")
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
                hide_index=True, use_container_width=True, key="utang_editor"  # data_editor masih pakai use_container_width
            )
            
            if st.button("🔄 Update Pelunasan", type="primary"):
                with st.spinner("⏳ Menyimpan perubahan..."):
                    try:
                        # Gunakan cache lokal
                        orig = st.session_state.data_cache['transaksi'].copy()
                        orig_no_compute = orig.drop(columns=['Month', 'Year'], errors='ignore').copy()
                        orig_no_compute['Tanggal_Match'] = pd.to_datetime(orig_no_compute['Tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
                        changes_count = 0
                        
                        payment_summary = {}  # Track total per payment method
                        
                        for i, row in editor.iterrows():
                            if row['Status'] == 'Lunas':
                                if row['Metode Pembayaran'] == "-" or row['Metode Pembayaran'] is None:
                                    st.warning(f"⚠️ Harap pilih Metode Pembayaran untuk item: {row['Item']}")
                                    continue
                                
                                target_date = pd.to_datetime(row['Tanggal']).strftime('%Y-%m-%d')
                                mask = ((orig_no_compute['Tanggal_Match'] == target_date) & (orig_no_compute['Item'] == row['Item']) & 
                                        (orig_no_compute['Nominal'] == row['Nominal']) & (orig_no_compute['Status'] == 'Belum Lunas'))
                                
                                if mask.any():
                                    orig_no_compute.loc[mask, 'Status'] = 'Lunas'
                                    orig_no_compute.loc[mask, 'Metode Pembayaran'] = row['Metode Pembayaran']
                                    changes_count += 1
                                    
                                    # Track payment per wallet
                                    wallet = row['Metode Pembayaran']
                                    if wallet not in payment_summary:
                                        payment_summary[wallet] = 0
                                    payment_summary[wallet] += row['Nominal']
                        
                        if changes_count > 0:
                            orig_no_compute = orig_no_compute.drop(columns=['Tanggal_Match'])
                            orig_no_compute['Tanggal'] = pd.to_datetime(orig_no_compute['Tanggal']).dt.strftime('%Y-%m-%d')
                            
                            # Update dengan retry logic
                            def update_operation():
                                return conn.update(worksheet="Transaksi", data=orig_no_compute)
                            
                            retry_gsheet_operation(update_operation, max_retries=3, delay=1)
                            
                            # Update cache transaksi dengan data yang sudah di-update
                            # Re-parse dan tambahkan computed columns
                            cache_df = orig_no_compute.copy()
                            cache_df['Tanggal'] = pd.to_datetime(cache_df['Tanggal'], errors='coerce')
                            cache_df['Nominal'] = pd.to_numeric(cache_df['Nominal'], errors='coerce').fillna(0)
                            cache_df['Month'] = cache_df['Tanggal'].dt.month_name()
                            cache_df['Year'] = cache_df['Tanggal'].dt.year
                            st.session_state.data_cache['transaksi'] = cache_df
                            st.session_state.data_cache['last_update'] = datetime.now()
                            
                            st.success(f"✅ Berhasil melunasi {changes_count} transaksi!")
                            
                            # Show payment summary
                            if payment_summary:
                                st.info("💳 **Saldo Dompet Berkurang:**")
                                for wallet, amount in payment_summary.items():
                                    st.write(f"  • {wallet}: -Rp {amount:,.0f}")
                            
                            # Button to go to Dompet Saya
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("👛 Lihat Saldo Dompet", type="secondary", use_container_width=True):
                                    st.session_state['goto_menu'] = '👛 Dompet Saya'
                                    st.rerun()
                            with col2:
                                if st.button("🔄 Refresh & Tutup", type="primary", use_container_width=True):
                                    st.rerun()
                        else:
                            st.info("💡 Tidak ada perubahan. Pastikan Anda sudah mengubah Status ke 'Lunas' dan memilih Metode Pembayaran.")
                    except Exception as e:
                        st.error(f"❌ Error Update: {e}")
                        st.info("💡 Refresh halaman dan coba lagi jika koneksi bermasalah.")
        else:
            st.success("🎉 Tidak ada tanggungan utang saat ini!")
