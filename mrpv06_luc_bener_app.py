import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import io

# ==========================================
# 1. PAGE CONFIGURATION & CLEAN CSS OVERRIDE
# ==========================================
st.set_page_config(page_title="MRP Lot Sizing Calculator", layout="wide")

# CSS minimalis untuk mengatur tema warna marun, teks sidebar, dan spasi
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #faf8f2;
        color: #111111;
    }
    
    /* Header Utama */
    h1, h2, h3 {
        color: #6a0708 !important;
    }
    
    /* Sidebar Layout (Marun) */
    [data-testid="stSidebar"] {
        background-color: #6a0708 !important;
    }
    
    /* Label teks di luar kolom input (Warna Krem Soft) */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #f4efdc !important;
        font-weight: 600 !important;
    }
    
    /* FIX POIN 2: Mengunci teks angka/isi di dalam kolom input agar TETAP HITAM */
    [data-testid="stSidebar"] input {
        color: #111111 !important;
        font-weight: normal !important;
        background-color: #ffffff !important;
    }
    
    /* Tombol Utama */
    .stButton>button {
        background-color: #6a0708 !important;
        color: #faf8f2 !important;
        border-radius: 4px !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #d90429 !important;
    }
    
    /* Format Teks Justify untuk Penjelasan Rumus di dalam Window Buka-Tutup */
    .text-justify {
        text-align: justify !important;
        line-height: 1.6 !important;
        margin-bottom: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 MRP Lot Sizing Calculator")
st.markdown("---")


# ==========================================
# 2. GLOSSARY SECTION (TOP OF PAGE — NO LATEX)
# ==========================================
st.subheader("📚 Glossary")
g_col1, g_col2, g_col3, g_col4 = st.columns(4)

with g_col1:
    with st.expander("📋 1. Lot-for-Lot (L4L)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Konsep:</b> Memesan jumlah material dalam volume yang sama persis dengan jumlah kebutuhan bersih di setiap periode.<br><br>
        <b>Rumus:</b><br>Lot Size = Kebutuhan Bersih<br><br>
        <b>Fungsi:</b> Meminimalkan biaya penyimpanan hingga mencapai nilai nol.
        </div>""", unsafe_allow_html=True)

with g_col2:
    with st.expander("🎯 2. Economic Order Quantity (EOQ)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Konsep:</b> Menentukan jumlah pesanan yang tetap untuk meminimalkan total biaya pemesanan dan penyimpanan.<br><br>
        <b>Fungsi:</b> Efektif digunakan jika pola permintaan barang bersifat konstan dan stabil.
        </div>""", unsafe_allow_html=True)

with g_col3:
    with st.expander("🔍 3. Least Unit Cost (LUC)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Konsep:</b> Menentukan ukuran lot dengan mengevaluasi beberapa periode ke depan hingga diperoleh biaya per unit yang paling minimum.
        </div>""", unsafe_allow_html=True)

with g_col4:
    with st.expander("⚖️ 4. Part Period Balancing (PPB)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Konsep:</b> Menyeimbangkan antara biaya pemesanan dengan kumulatif biaya penyimpanan untuk periode pesanan yang bervariasi.
        </div>""", unsafe_allow_html=True)

st.markdown("---")


# ==========================================
# 3. SIDEBAR PARAMETER INPUTS
# ==========================================
st.sidebar.header("⚙️ Input Parameter")

st.sidebar.subheader("Biaya")
setup_cost = st.sidebar.number_input("Setup Cost", min_value=0.0, value=100000.0, step=500.0)
holding_cost = st.sidebar.number_input("Holding Cost", min_value=0.0, value=2000.0, step=100.0)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("Persediaan")
initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time", min_value=0, value=1, step=1)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("Kapasitas")
max_capacity = st.sidebar.number_input("Warehouse Capacity", min_value=1, value=100, step=10)


# ==========================================
# UTILITY HELPER & PASTEL THEME MASKING
# ==========================================
def find_matching_column(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

def style_mrp_grid(df_transposed, max_cap):
    def check_capacity(row):
        if row.name == 'Projected On Hand':
            return ['background-color: #ffe0b2; color: #6a0708; font-weight: bold;' if val > max_cap else '' for val in row]
        return [''] * len(row)
    return df_transposed.style.apply(check_capacity, axis=1)

def style_iteration_rows(df_step):
    style_matrix = pd.DataFrame('', index=df_step.index, columns=df_step.columns)
    for idx, row in df_step.iterrows():
        status_str = str(row['Status'])
        if "Stop" in status_str:
            style_matrix.loc[idx] = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
        elif "Selected" in status_str or "Horizon End" in status_str:
            style_matrix.loc[idx] = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    return style_matrix


# ==========================================
# 4. DATA ACQUISITION WORKBENCH
# ==========================================
st.subheader("📊 Data Input")

input_method = st.radio(
    "Pilih Metode Input Data:", 
    ["Upload File", "Manual Entry", "Load Template"]
)

df_workbench = None

if input_method == "Upload File":
    uploaded_file = st.file_uploader("Upload File (.csv, .xlsx)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            col_p = find_matching_column(df_raw.columns, ['periode', 'mingguke', 'p', 'minggu', 'period', 'week'])
            col_gr = find_matching_column(df_raw.columns, ['gr', 'grossrequirement', 'grossrequirements', 'kebutuhankotor'])
            col_sr = find_matching_column(df_raw.columns, ['sr', 'scheduledreceipt', 'scheduledreceipts', 'penerimaanterjadwal'])
            
            df_workbench = pd.DataFrame()
            if col_p and col_p in df_raw.columns:
                df_workbench['Period'] = df_raw[col_p].astype(str)
            else:
                df_workbench['Period'] = [f"P{i+1}" for i in range(len(df_raw))]
                
            if col_gr and col_gr in df_raw.columns:
                df_workbench['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int)
            else:
                st.error("Gagal memetakan kolom Gross Requirements.")
                
            if col_sr and col_sr in df_raw.columns:
                df_workbench['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_workbench['Scheduled Receipts'] = 0
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")
            
elif input_method == "Manual Entry":
    num_periods_input = st.number_input("Jumlah Periode:", min_value=1, max_value=52, value=10, step=1)
    init_data = {
        'Period': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55] if num_periods_input == 10 else [0] * num_periods_input,
        'Scheduled Receipts': [0] * num_periods_input
    }
    df_workbench = st.data_editor(pd.DataFrame(init_data), use_container_width=True, hide_index=True)
else:
    default_data = {
        'Period': [f"P{i}" for i in range(1, 11)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55],
        'Scheduled Receipts': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    }
    df_workbench = pd.DataFrame(default_data)

if df_workbench is not None and not df_workbench.empty:
    gross_req = df_workbench['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec = df_workbench['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_workbench['Period'].astype(str).tolist()
    
    st.markdown("##### Tabel Ringkasan Input:")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()


    # ==========================================
    # CORE PROCESSING MATHEMATICAL ALGORITHMS
    # ==========================================
    def calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)
        
        # Hitung Kebutuhan Bersih
        net_req = []
        prev_inv = init_inv
        for i in range(n):
            available_stock = prev_inv + s_receipts[i]
            net_val = demands[i] + ss - available_stock
            if net_val > 0:
                net_req.append(net_val)
                prev_inv = ss
            else:
                net_req.append(0)
                prev_inv = available_stock - demands[i]

        def generate_poh_and_release(rec_lot):
            poh = []
            r_inv = init_inv
            for i in range(n):
                r_inv += s_receipts[i] + rec_lot[i] - demands[i]
                poh.append(r_inv)
            
            rel_lot = [0] * n
            for i in range(n):
                if rec_lot[i] > 0:
                    target = i - lt
                    rel_lot[max(0, target)] += rec_lot[i]
            return poh, rel_lot

        # 1. LOT-FOR-LOT (L4L)
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = generate_poh_and_release(l4l_rec)
        c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        c_l4l_hold = sum(max(0, x) for x in l4l_poh) * hold

        # 2. LEAST UNIT COST (LUC)
        luc_rec = [0] * n
        luc_trace_logs = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue
            best_k = idx
            min_uc = float('inf')
            acc_d, acc_h = 0, 0
            t_log = []
            
            for k in range(idx, n):
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                t_cost = setup + acc_h
                uc = t_cost / acc_d if acc_d > 0 else float('inf')
                
                covered_periods_str = ", ".join([f"P{m+1}" for m in range(idx, k+1)])
                
                if uc <= min_uc:
                    min_uc, best_k = uc, k
                    t_log.append({
                        'Periods Covered': covered_periods_str, 'Total Units': acc_d, 
                        'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 
                        'Unit Cost': uc, 'Status': 'Feasible'
                    })
                else:
                    t_log.append({
                        'Periods Covered': covered_periods_str, 'Total Units': acc_d, 
                        'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 
                        'Unit Cost': uc, 'Status': 'Stop ⚠️ (Limit Exceeded)'
                    })
                    break
            
            df_step = pd.DataFrame(t_log)
            stop_exists = df_step['Status'].str.contains('Stop').any()
            if stop_exists:
                stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                if stop_idx > 0:
                    df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
            else:
                if not df_step.empty:
                    df_step.at[df_step.index[-1], 'Status'] = 'Horizon End (Optimal)'
                    
            luc_trace_logs.append(df_step)
            luc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
            
        luc_poh, luc_rel = generate_poh_and_release(luc_rec)
        c_luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        c_luc_hold = sum(max(0, x) for x in luc_poh) * hold

        # 3. ECONOMIC ORDER QUANTITY (EOQ)
        avg_demand_gross = np.mean(demands)
        eoq_size = math.ceil(math.sqrt((2 * avg_demand_gross * setup) / hold)) if hold > 0 else 0
        eoq_rec = [0] * n
        rem_stok = 0
        for i in range(n):
            if net_req[i] > 0:
                if rem_stok < net_req[i]:
                    needed = net_req[i] - rem_stok
                    lots_to_order = math.ceil(needed / eoq_size) if eoq_size > 0 else 1
                    eoq_rec[i] = lots_to_order * eoq_size
                    rem_stok = (eoq_rec[i] + rem_stok) - net_req[i]
                else:
                    rem_stok -= net_req[i]
                    
        eoq_poh, eoq_rel = generate_poh_and_release(eoq_rec)
        c_eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        c_eoq_hold = sum(max(0, x) for x in eoq_poh) * hold

        # 4. PART PERIOD BALANCING (PPB)
        ppb_rec = [0] * n
        ppb_trace_logs = []
        epp_limit = setup / hold if hold > 0 else float('inf')
        
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue
            best_k = idx
            cum_part_period = 0
            acc_d = 0
            t_log = []
            
            for k in range(idx, n):
                part_period_k = net_req[k] * (k - idx)
                new_cum_part_period = cum_part_period + part_period_k
                covered_periods_str = ", ".join([f"P{m+1}" for m in range(idx, k+1)])
                
                if new_cum_part_period <= epp_limit:
                    acc_d += net_req[k]
                    cum_part_period = new_cum_part_period
                    best_k = k
                    t_log.append({
                        'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                        'Target EPP': epp_limit, 'Accumulated Part-Period': cum_part_period,
                        'Status': 'Feasible'
                    })
                else:
                    dist_before = abs(cum_part_period - epp_limit)
                    dist_after = abs(new_cum_part_period - epp_limit)
                    
                    if dist_after < dist_before:
                        acc_d += net_req[k]
                        cum_part_period = new_cum_part_period
                        best_k = k
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                            'Target EPP': epp_limit, 'Accumulated Part-Period': cum_part_period,
                            'Status': 'Feasible (Closer Beyond Limit)'
                        })
                    else:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d + net_req[k],
                            'Target EPP': epp_limit, 'Accumulated Part-Period': new_cum_part_period,
                            'Status': 'Stop ⚠️ (Limit Exceeded)'
                        })
                    break
                    
            df_step = pd.DataFrame(t_log)
            stop_exists = df_step['Status'].str.contains('Stop').any()
            if stop_exists:
                stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                if stop_idx > 0:
                    df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
            else:
                if not df_step.empty:
                    df_step.at[df_step.index[-1], 'Status'] = 'Horizon End (Optimal)'
                    
            ppb_trace_logs.append(df_step)
            ppb_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
            
        ppb_poh, ppb_rel = generate_poh_and_release(ppb_rec)
        c_ppb_setup = sum(1 for x in ppb_rec if x > 0) * setup
        c_ppb_hold = sum(max(0, x) for x in ppb_poh) * hold

        return {
            'net_req': net_req,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_trace_logs},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': c_eoq_setup, 'hold': c_eoq_hold, 'total': c_eoq_setup + c_eoq_hold, 'size': eoq_size, 'avg_demand_gross': avg_demand_gross},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': c_ppb_setup, 'hold': c_ppb_hold, 'total': c_ppb_setup + c_ppb_hold, 'iters': ppb_trace_logs, 'epp': epp_limit}
        }

    # Jalankan Mesin Perhitungan
    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    def render_mrp_grid_view(data_dict, max_cap):
        df = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': data_dict['poh'],
            'Net Requirements': res['net_req'],
            'Planned Order Receipts': data_dict['rec'],
            'Planned Order Releases': data_dict['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        st.dataframe(style_mrp_grid(df, max_cap), use_container_width=True)
        if max(data_dict['poh']) > max_cap:
            st.error(f"⚠️ POH melebihi kapasitas gudang ({max_cap} unit).")

    # FIX POIN 5: Mengubah Ringkasan Biaya Menjadi Window Buka-Tutup (Expander) dan ditaruh paling bawah tabel
    def render_cost_audit_window(data_dict, setup_val, hold_val, rec_array, poh_array):
        order_count = sum(1 for x in rec_array if x > 0)
        sum_poh = sum(max(0, x) for x in poh_array)
        
        with st.expander("💰 Detail Biaya Perhitungan", expanded=False):
            st.markdown(f"""<div class='text-justify'>
            <b>1. Setup Cost:</b> {data_dict['setup']:,.2f} (Perhitungan: {order_count} kali order &times; {setup_val:,.2f})<br><br>
            <b>2. Holding Cost:</b> {data_dict['hold']:,.2f} (Perhitungan: {sum_poh} akumulasi unit &times; {hold_val:,.2f})<br><br>
            <b>3. Total Cost:</b> <b>{data_dict['total']:,.2f}</b> (Perhitungan: Setup Cost + Holding Cost)
            </div>""", unsafe_allow_html=True)


    # ==========================================
    # 5. METHODS EXECUTION TABS
    # ==========================================
    st.markdown("---")
    st.subheader("⚙️ Hasil Metode Lot Sizing")
    
    t_l4l, t_eoq, t_luc, t_ppb = st.tabs([
        "📋 Lot-for-Lot (L4L)", 
        "🎯 Economic Order Quantity (EOQ)", 
        "🔍 Least Unit Cost (LUC)", 
        "⚖️ Part Period Balancing (PPB)"
    ])

    # TAB 1: LOT-FOR-LOT
    with t_l4l:
        st.subheader("Metode Lot-for-Lot (L4L)")
        render_mrp_grid_view(res['l4l'], max_capacity)
        render_cost_audit_window(res['l4l'], setup_cost, holding_cost, res['l4l']['rec'], res['l4l']['poh'])

    # TAB 2: EOQ (FIXED POIN 4: MASUK DI WINDOW BUKA-TUTUP, KE BAWAH, JUSTIFY, NO LATEX)
    with t_eoq:
        st.subheader("Metode Economic Order Quantity (EOQ)")
        
        with st.expander("📝 Rumus Perhitungan EOQ", expanded=False):
            avg_d_calc = res['eoq']['avg_demand_gross']
            val_top = 2 * avg_d_calc * setup_cost
            val_div = val_top / holding_cost
            eoq_raw_val = math.sqrt(val_div)
            
            st.markdown(f"""<div class='text-justify'>
            <b>Step 1: Hitung Rata-rata Kebutuhan Kotor (D)</b><br>
            D = Total Kebutuhan Kotor / Jumlah Periode<br>
            D = {sum(gross_req)} / {num_periods}<br>
            D = <b>{avg_d_calc:.4f} unit/periode</b><br><br>
            
            <b>Step 2: Hitung Nilai Nilai Sizing EOQ</b><br>
            EOQ = Akar( (2 * D * Setup Cost) / Holding Cost )<br>
            EOQ = Akar( (2 * {avg_d_calc:.4f} * {setup_cost:,.2f}) / {holding_cost:,.2f} )<br>
            EOQ = Akar( {val_div:,.4f} )<br>
            EOQ = <b>{eoq_raw_val:.4f} unit</b><br><br>
            
            <b>Step 3: Pembulatan ke Atas (Ceiling)</b><br>
            Hasil pembulatan ukuran lot pemesanan EOQ = <b>{res['eoq']['size']} unit</b>.
            </div>""", unsafe_allow_html=True)
            
        render_mrp_grid_view(res['eoq'], max_capacity)
        render_cost_audit_window(res['eoq'], setup_cost, holding_cost, res['eoq']['rec'], res['eoq']['poh'])

    # TAB 3: LUC
    with t_luc:
        st.subheader("Metode Least Unit Cost (LUC)")
        st.markdown("##### Langkah Iterasi:")
        
        fmt_luc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'Unit Cost': '{:.4f}'}
        for step_idx, df_step in enumerate(res['luc']['iters']):
            with st.expander(f"Iterasi {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_luc), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['luc'], max_capacity)
        render_cost_audit_window(res['luc'], setup_cost, holding_cost, res['luc']['rec'], res['luc']['poh'])

    # TAB 4: PPB (FIXED POIN 4: MASUK DI WINDOW BUKA-TUTUP, KE BAWAH, JUSTIFY, NO LATEX)
    with t_ppb:
        st.subheader("Metode Part Period Balancing (PPB)")
        
        with st.expander("⚖️ Rumus Perhitungan Nilai EPP", expanded=False):
            st.markdown(f"""<div class='text-justify'>
            <b>Step 1: Hitung Nilai Target Economic Part Period (EPP)</b><br>
            EPP = Setup Cost / Holding Cost<br>
            EPP = {setup_cost:,.2f} / {holding_cost:,.2f}<br>
            EPP = <b>{res['ppb']['epp']:.4f} part-periods</b><br><br>
            
            <b>Step 2: Menyeimbangkan Kebutuhan Periode</b><br>
            Akumulasi nilai part-period dihitung ke bawah baris demi baris pada jendela iterasi di bawah sampai mendekati target batas EPP di atas.
            </div>""", unsafe_allow_html=True)
            
        st.markdown("##### Langkah Iterasi:")
        fmt_ppb = {'Target EPP': '{:.2f}', 'Accumulated Part-Period': '{:.2f}', 'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}'}
        for step_idx, df_step in enumerate(res['ppb']['iters']):
            with st.expander(f"Iterasi {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_ppb), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['ppb'], max_capacity)
        render_cost_audit_window(res['ppb'], setup_cost, holding_cost, res['ppb']['rec'], res['ppb']['poh'])


    # ==========================================
    # 6. GLOBAL PERFORMANCE MATRIX COMPARISON (FIXED POIN 6: RED + INEFFICIENT VERDICT)
    # ==========================================
    st.markdown("---")
    st.header("🏁 Perbandingan Efisiensi Metode")
    
    biaya_dict = {
        'L4L': res['l4l']['total'], 
        'LUC': res['luc']['total'], 
        'EOQ': res['eoq']['total'], 
        'PPB': res['ppb']['total']
    }
    best_method = min(biaya_dict, key=biaya_dict.get)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        diff_l4l = res['l4l']['total'] - biaya_dict[best_method]
        if diff_l4l > 0:
            sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>Inefficient by {diff_l4l:,.2f}</div>"
            main_color = "#c62828"
        else:
            sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>"
            main_color = "#111111"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost L4L</div>
                        <div style='font-size: 22px; font-weight: 700; color: {main_color}; margin-top: 4px;'>{res['l4l']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        if diff_luc > 0:
            sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>Inefficient by {diff_luc:,.2f}</div>"
            main_color = "#c62828"
        else:
            sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>"
            main_color = "#111111"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost LUC</div>
                        <div style='font-size: 22px; font-weight: 700; color: {main_color}; margin-top: 4px;'>{res['luc']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        if diff_eoq > 0:
            sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>Inefficient by {diff_eoq:,.2f}</div>"
            main_color = "#c62828"
        else:
            sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>"
            main_color = "#111111"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost EOQ</div>
                        <div style='font-size: 22px; font-weight: 700; color: {main_color}; margin-top: 4px;'>{res['eoq']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        if diff_ppb > 0:
            sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>Inefficient by {diff_ppb:,.2f}</div>"
            main_color = "#c62828"
        else:
            sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>"
            main_color = "#111111"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost PPB</div>
                        <div style='font-size: 22px; font-weight: 700; color: {main_color}; margin-top: 4px;'>{res['ppb']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)

    st.success(f"Rekomendasi terbaik adalah menggunakan metode: **{best_method}**")


    # ==========================================
    # 7. GRAPH VISUALIZATION
    # ==========================================
    st.markdown("---")
    st.subheader("📉 Grafik Analisis Sensitivitas")
    
    cg1, cg2 = st.columns(2)
    with cg1:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        fig.patch.set_facecolor('#faf8f2')
        ax.set_facecolor('#faf8f2')
        
        ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#444444', '#6a0708', '#e65c00', '#2a7b4c'], width=0.45)
        ax.set_title("Comparison of Lot Sizing Methods", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax.set_xlabel('Lot Sizing Strategy', color='#111', fontsize=9, fontweight='bold')
        ax.set_ylabel('Total Cost', color='#111', fontsize=9, fontweight='bold')
        ax.grid(axis='y', linestyle=':', alpha=0.6)
        st.pyplot(fig)
        
    with cg2:
        scale_factors = np.arange(0.70, 1.31, 0.05) 
        s_l4l, s_luc, s_eoq, s_ppb, labels_pct = [], [], [], [], []
        
        for f in scale_factors:
            pct_val = int(round((f - 1) * 100))
            if pct_val > 30: 
                continue
            sim_demand = [max(1, int(d * f)) for d in gross_req]
            s_res = calculate_multi_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
            s_l4l.append(s_res['l4l']['total'])
            s_luc.append(s_res['luc']['total'])
            s_eoq.append(s_res['eoq']['total'])
            s_ppb.append(s_res['ppb']['total'])
            labels_pct.append(f"{pct_val:+}%")
        
        fig2, ax2 = plt.subplots(figsize=(7, 4.2))
        fig2.patch.set_facecolor('#faf8f2')
        ax2.set_facecolor('#faf8f2')
        
        ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#444444', linewidth=2)
        ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#6a0708', linewidth=2)
        ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#e65c00', linewidth=2)
        ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#2a7b4c', linewidth=2)
        
        ax2.set_title("Demand Change Sensitivity Chart", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax2.set_ylabel('Simulated Total Incurred Cost', color='#111', fontsize=9, fontweight='bold')
        ax2.set_xlabel('Customer Demand Change Sensitivity', color='#111', fontsize=9, fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.6)
        ax2.legend(facecolor='#faf8f2', fontsize=9)
        plt.xticks(rotation=30)
        st.pyplot(fig2)

    # Export Data Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Baseline Framework")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="L4L Plan")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="LUC Plan")
        pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="EOQ Plan")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="PPB Plan")
    
    buffer.seek(0)
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📥 Download Data Report", 
        data=buffer, 
        file_name="MRP_Lot_Sizing_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Silakan masukan data terlebih dahulu.")
