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

st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #faf8f2;
        color: #111111;
    }
    
    h1, h2, h3 {
        color: #6a0708 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #6a0708 !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #f4efdc !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] input {
        color: #111111 !important;
        font-weight: normal !important;
        background-color: #ffffff !important;
    }
    
    .stButton>button {
        background-color: #6a0708 !important;
        color: #faf8f2 !important;
        border-radius: 4px !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #d90429 !important;
    }
    
    .text-justify {
        text-align: justify !important;
        line-height: 1.5 !important;
        font-size: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 MRP Lot Sizing Calculator")
st.markdown("---")


# ==========================================
# 2. GLOSSARY SECTION
# ==========================================
st.subheader("📚 Glossary")
g_col1, g_col2, g_col3, g_col4 = st.columns(4)

with g_col1:
    with st.expander("📋 1. Lot-for-Lot (L4L)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Concept:</b> Orders inventory sizes matching exact net requirement constraints per discrete period.<br><br>
        <b>Function:</b> Minimizes holding values straight to a zero-point baseline.
        </div>""", unsafe_allow_html=True)

with g_col2:
    with st.expander("🎯 2. Economic Order Quantity (EOQ)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Concept:</b> Establishes a fixed structural lot sizing standard to find an equilibrium balance between ordering and holding profiles.<br><br>
        <b>Function:</b> Maximizes cost efficiencies when cross-horizon operational demands remain linear and highly predictable.
        </div>""", unsafe_allow_html=True)

with g_col3:
    with st.expander("🔍 3. Least Unit Cost (LUC)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Concept:</b> Iterative search routine that aggregates upcoming period blocks until the calculated total cost per unit starts to climb.<br><br>
        <b>Function:</b> Controls cost variances dynamic to changing horizon shifts.
        </div>""", unsafe_allow_html=True)

with g_col4:
    with st.expander("⚖️ 4. Part Period Balancing (PPB)", expanded=False):
        st.markdown("""<div class='text-justify'>
        <b>Concept:</b> Synchronizes setup costs against cumulative holding components across discrete time horizons by locating closest-fit factors.<br><br>
        <b>Function:</b> Drives balanced material cost optimization across variable parameter landscapes.
        </div>""", unsafe_allow_html=True)

st.markdown("---")


# ==========================================
# 3. SIDEBAR PARAMETER INPUTS
# ==========================================
st.sidebar.header("⚙️ Control Dashboard")

st.sidebar.subheader("💰 Financial Factors")  
setup_cost = st.sidebar.number_input("Setup Cost", min_value=0.0, value=100.0, step=5.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit/period)", min_value=0.0, value=2.0, step=0.5)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

st.sidebar.subheader("🗂️ Inventory Profiles")  
initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time", min_value=0, value=1, step=1)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

st.sidebar.subheader("🏭 Operational Boundaries")
max_capacity = st.sidebar.number_input("Maximum Warehouse Capacity (Units)", min_value=1, value=100, step=10)


# ==========================================
# UTILITY CORE HELPERS
# ==========================================
def find_matching_column(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

def style_mrp_grid(df_transposed, max_cap, ss):
    def check_capacity(row):
        styles = []
        if row.name == 'Projected On Hand':
            for val in row:
                if val > max_cap:
                    styles.append('background-color: #ffe0b2; color: #6a0708; font-weight: bold;')
                elif val < ss:
                    styles.append('background-color: #ffcdd2; color: #b71c1c; font-weight: bold;')
                else:
                    styles.append('')
            return styles
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
st.subheader("📊 Data Input workbench")

input_method = st.radio(
    "Select Input Configuration Method:", 
    ["Upload File", "Manual Entry", "Load Template"]
)

df_workbench = None

if input_method == "Upload File":
    uploaded_file = st.file_uploader("Upload demand documents (.csv, .xlsx)", type=["csv", "xlsx"])
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
                st.error("Failed to map Gross Requirements attribute automatically.")
                st.stop() 
                
            if col_sr and col_sr in df_raw.columns:
                df_workbench['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_workbench['Scheduled Receipts'] = 0
        except Exception as e:
            st.error(f"Engine parsing failure: {e}")
            st.stop()
            
elif input_method == "Manual Entry":
    num_periods_input = st.number_input("Planning Horizon Length (Periods):", min_value=1, max_value=52, value=10, step=1)
    
    # Sediakan data default jika horizon = 10, jika bukan 10 maka otomatis isi baseline 0 agar dinamis
    if num_periods_input == 10:
        default_gr = [35, 30, 40, 0, 10, 40, 30, 0, 30, 55]
    else:
        default_gr = [0] * num_periods_input
        
    init_data = {
        'Period': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': default_gr,
        'Scheduled Receipts': [0] * num_periods_input
    }
    
    # PERBAIKAN BUG NYATA: Transformasikan tabel input dasar menjadi data_editor interaktif
    st.markdown("##### ✏️ Edit Demand & Scheduled Receipts Data Below:")
    df_raw_manual = pd.DataFrame(init_data)
    df_workbench = st.data_editor(df_raw_manual, use_container_width=True, hide_index=True)

else:
    # Modul Load Template Tetap Statis sebagai Data Pembanding Contoh Kuliah
    default_data = {
        'Period': [f"P{i}" for i in range(1, 11)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55],
        'Scheduled Receipts': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    }
    df_workbench = pd.DataFrame(default_data)

# Sinkronisasi visualisasi matriks preview horizontal di bawah workbench
if df_workbench is not None and not df_workbench.empty:
    gross_req = df_workbench['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec = df_workbench['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_workbench['Period'].astype(str).tolist()
    
    st.markdown("##### Input Data Matrix Summary View (Transposed):")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    # Tampilkan preview final secara rapi (read-only atau jika diedit di sini juga ikut sinkron)
    df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()


    # ==========================================
    # CORE PROCESSING MATHEMATICAL ALGORITHMS
    # ==========================================
    def calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)
        
        # Calculate Net Requirements Matrix
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

        # Perbaikan Catatan 4: Menerima ss sebagai parameter untuk validasi visual di grid luar
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
                # Perbaikan Catatan 1: Hapus filter skip continue! Biarkan periode 0 masuk hitungan agar indeks penunjuk tidak loncat.
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                t_cost = setup + acc_h
                uc = t_cost / acc_d if acc_d > 0 else float('inf')
                
                covered_periods_str = ", ".join([period_labels[m] for m in range(idx, k+1)])
                
                if uc < min_uc:  
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
            if not df_step.empty:
                stop_exists = df_step['Status'].str.contains('Stop').any()
                if stop_exists:
                    stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                    if stop_idx > 0:
                        df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
                else:
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
        
        # Perbaikan Catatan 3: Hapus total blok else mubazir. Periode net_req=0 tidak perlu diutak-atik.
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
                covered_periods_str = ", ".join([period_labels[m] for m in range(idx, k+1)])
                
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
                    
                    # Perbaikan Catatan 2: Batasi look-ahead hanya sekali lewat break, hapus resiko over-consolidation
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
            if not df_step.empty:
                stop_exists = df_step['Status'].str.contains('Stop').any()
                if stop_exists:
                    stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                    if stop_idx > 0:
                        df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
                else:
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

    # Run Process Calculations
    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    def render_mrp_grid_view(data_dict, max_cap, ss):
        df = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': data_dict['poh'],
            'Net Requirements': res['net_req'],
            'Planned Order Receipts': data_dict['rec'],
            'Planned Order Releases': data_dict['rel']
        }, index=period_labels).T
        st.dataframe(style_mrp_grid(df, max_cap, ss), use_container_width=True)
        
        if min(data_dict['poh']) < ss:
            stockout_periods = [period_labels[i] for i, v in enumerate(data_dict['poh']) if v < ss]
            st.error(f"🚨 Shortage Warning: Stockout / Pelanggaran Safety Stock terjadi pada periode: {', '.join(stockout_periods)}")
        if max(data_dict['poh']) > max_cap:
            st.error(f"⚠️ Capacity Boundary Overrun: Projected On Hand melebihi batas kapasitas gudang ({max_cap} unit).")

    def render_cost_audit_window(data_dict, setup_val, hold_val, rec_array, poh_array):
        order_count = sum(1 for x in rec_array if x > 0)
        sum_poh = sum(max(0, x) for x in poh_array)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.expander("🛠️ Setup Cost Detail"):
                st.markdown(f"""<div class='text-justify'>
                <b>Formula:</b><br>Orders Count &times; Unit Setup Cost<br><br>
                <b>Calculation:</b><br>{order_count} &times; {setup_val:,.2f}<br><br>
                <b>Total:</b> {data_dict['setup']:,.2f}
                </div>""", unsafe_allow_html=True)
        with c2:
            with st.expander("📦 Holding Cost Detail"):
                st.markdown(f"""<div class='text-justify'>
                <b>Formula:</b><br>(&sum; Projected On Hand) &times; Holding Rate<br><br>
                <b>Calculation:</b><br>{sum_poh} &times; {hold_val:,.2f}<br><br>
                <b>Total:</b> {data_dict['hold']:,.2f}
                </div>""", unsafe_allow_html=True)
        with c3:
            with st.expander("💰 Total Operational Cost"):
                st.markdown(f"""<div class='text-justify'>
                <b>Formula:</b><br>Setup Cost + Holding Cost<br><br>
                <b>Calculation:</b><br>{data_dict['setup']:,.2f} + {data_dict['hold']:,.2f}<br><br>
                <b>Total:</b> <b>{data_dict['total']:,.2f}</b>
                </div>""", unsafe_allow_html=True)


    # ==========================================
    # 5. METHODS MODULES EXECUTION WORKBENCH TABS
    # ==========================================
    st.markdown("---")
    st.subheader("⚙️ Lot Sizing Operational Performance Strategy Modules")
    
    t_l4l, t_eoq, t_luc, t_ppb = st.tabs([
        "📋 Lot-for-Lot (L4L)", 
        "🎯 Economic Order Quantity (EOQ)", 
        "🔍 Least Unit Cost (LUC)", 
        "⚖️ Part Period Balancing (PPB)"
    ])

    # TAB 1: LOT-FOR-LOT
    with t_l4l:
        st.subheader("Lot-for-Lot (L4L) Performance Execution Model")
        render_mrp_grid_view(res['l4l'], max_capacity, safety_stock)
        render_cost_audit_window(res['l4l'], setup_cost, holding_cost, res['l4l']['rec'], res['l4l']['poh'])

    # TAB 2: EOQ
    with t_eoq:
        st.subheader("Economic Order Quantity (EOQ) Optimization")
        
        if holding_cost == 0:
            st.warning("⚠️ Holding cost bernilai 0. Formula log matematika EOQ dihentikan untuk mencegah pembagian nol.")
        else:
            with st.expander("🔬 CLICK HERE TO VIEW FORMULA LOG CALCULATIONS (EOQ)"):
                total_gross_req = sum(gross_req)
                n_periode = len(gross_req)
                avg_demand_calc = res['eoq']['avg_demand_gross']
                
                st.markdown("#### 📝 Sizing Steps for EOQ:")
                st.markdown("**1. Identify Input Gross Requirements Data Matrix:**")
                st.markdown(f"""
                * Data per Period: `{gross_req}`
                * Total Kebutuhan ($\sum$ Gross Req) = `{total_gross_req}` units / Planning Horizon ($n$) = `{n_periode}` periods
                * Average Demand ($D$) = `{avg_demand_calc:.4f}` units/period
                """)
                
                st.markdown("**2. Standard Square-Root Mathematical Equation Substitution:**")
                st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times D \\times \\text{{Setup Cost}}}}{{\\text{{Holding Cost}}}}}}$$")
                st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times {avg_demand_calc:.4f} \\times {setup_cost:,.2f}}}{{{holding_cost:,.2f}}}}}$$")
                st.markdown(f"$$EOQ = {math.sqrt((2 * avg_demand_calc * setup_cost) / holding_cost):.4f} \\text{{ units}}$$")
                
                st.markdown("**3. Discrete Upper Integer Ceiling Rounding:**")
                st.markdown(f"* Rounded up via ceiling constraints: **`{res['eoq']['size']}` units**.")
            
        st.info(f"💡 **Lot Sizing Matrix Status:** Batas Fixed Order Quantity untuk profil EOQ dikunci pada **{res['eoq']['size']} unit** per pesanan.")
        render_mrp_grid_view(res['eoq'], max_capacity, safety_stock)
        render_cost_audit_window(res['eoq'], setup_cost, holding_cost, res['eoq']['rec'], res['eoq']['poh'])

    # TAB 3: LUC
    with t_luc:
        st.subheader("Least Unit Cost (LUC) Iterative Consolidation Grid")
        st.markdown("##### Dynamic Lot Search Log Blocks Trace:")
        
        fmt_luc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'Unit Cost': '{:.4f}'}
        for step_idx, df_step in enumerate(res['luc']['iters']):
            if df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_luc), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['luc'], max_capacity, safety_stock)
        render_cost_audit_window(res['luc'], setup_cost, holding_cost, res['luc']['rec'], res['luc']['poh'])

    # TAB 4: PPB
    with t_ppb:
        st.subheader("Part Period Balancing (PPB) Dynamic Policy Grid")
        
        with st.expander("🔬 CLICK HERE TO VIEW DETAILED FORMULA LOG CALCULATIONS (PPB)", expanded=True):
            st.markdown("#### 📝 Sizing Steps for PPB:")
            st.markdown("**1. Identify Operational Control Parameters:**")
            st.markdown(f"""
            * Setup Cost Value = `{setup_cost:,.2f}` | Holding Cost Value = `{holding_cost:,.2f}`
            """)
            
            st.markdown("**2. Calculate Balanced Economic Part Period (EPP) Target Limit Baseline:**")
            st.markdown(r"$$EPP = \frac{\text{Setup Cost}}{\text{Holding Cost}}$$")
            st.markdown(f"$$EPP = \\frac{{{setup_cost:,.2f}}}{{{holding_cost:,.2f}}}$$")
            st.markdown(f"$$EPP = {res['ppb']['epp']:.4f} \\text{{ part-periods}}$$")
            
        st.info(f"💡 **Part Period Matrix Target Status:** Target batas EPP dikunci pada **{res['ppb']['epp']:.4f}** part-periods.")
        
        st.markdown("##### Iteration Steps Trace:")
        fmt_ppb = {'Target EPP': '{:.2f}', 'Accumulated Part-Period': '{:.2f}'}
        for step_idx, df_step in enumerate(res['ppb']['iters']):
            if df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_ppb), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['ppb'], max_capacity, safety_stock)
        render_cost_audit_window(res['ppb'], setup_cost, holding_cost, res['ppb']['rec'], res['ppb']['poh'])


    # ==========================================
    # 6. GLOBAL PERFORMANCE MATRIX COMPARISON
    # ==========================================
    st.markdown("---")
    st.header("🏁 Strategic Portfolio Cost Summary Comparison Matrix")
    
    biaya_dict = {
        'L4L': res['l4l']['total'], 
        'LUC': res['luc']['total'], 
        'EOQ': res['eoq']['total'], 
        'PPB': res['ppb']['total']
    }
    
    min_cost = min(biaya_dict.values())
    best_methods = [k for k, v in biaya_dict.items() if v == min_cost]
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        is_best = 'L4L' in best_methods
        sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 13px; font-weight: bold;'>⚠️ Inefficient by {res['l4l']['total'] - min_cost:,.2f}</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost L4L</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111111; margin-top: 4px;'>{res['l4l']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m2:
        is_best = 'LUC' in best_methods
        sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 13px; font-weight: bold;'>⚠️ Inefficient by {res['luc']['total'] - min_cost:,.2f}</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost LUC</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111111; margin-top: 4px;'>{res['luc']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m3:
        is_best = 'EOQ' in best_methods
        sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 13px; font-weight: bold;'>⚠️ Inefficient by {res['eoq']['total'] - min_cost:,.2f}</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost EOQ</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111111; margin-top: 4px;'>{res['eoq']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m4:
        is_best = 'PPB' in best_methods
        sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 13px; font-weight: bold;'>⚠️ Inefficient by {res['ppb']['total'] - min_cost:,.2f}</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost PPB</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111111; margin-top: 4px;'>{res['ppb']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)

    # Verdict Banner (Minimalist Center - Text Hijau Tema)
    methods_string = " & ".join(best_methods)
    st.markdown(f"""
    <div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-left: 5px solid #2e7d32; padding: 14px; border-radius: 4px; margin-top: 20px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <span style="color: #2e7d32; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 4px;">
            🎯 Strategy Recommendation:
        </span>
        <span style="color: #111111; font-size: 15px; font-weight: 500;">
            It is highly recommended to <span style="color: #2e7d32; font-weight: 700;">Apply {methods_string} Model</span> to maximize your overall operational efficiency.
        </span>
    </div>
    """, unsafe_allow_html=True)


    # ==========================================
    # 7. GRAPH VISUALIZATION
    # ==========================================
    st.markdown("---")
    st.subheader("📉 Parametric Sensitivity Analysis Charts")
    
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
            sim_demand = [int(round(d * f)) for d in gross_req]
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

    # Export Excel File Report workbench
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=period_labels).T.to_excel(writer, sheet_name="Baseline Framework")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="L4L Plan")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="LUC Plan")
        pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="EOQ Plan")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="PPB Plan")
    
    buffer.seek(0)
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📥 Download Plan Document Report", 
        data=buffer, 
        file_name="MRP_Lot_Sizing_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please initialize input values or upload transaction vectors to run calculation routines.")
