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

    /* Fixed Height Utility to Guarantee Grid Symmetry */
    .glossary-card {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #e0dbcd;
        border-top: 4px solid #6a0708;
        min-height: 160px;
        margin-bottom: 10px;
    }
    .glossary-title {
        color: #6a0708;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 6px;
    }
    
    /* Justify Math Equation Wrapper */
    .math-justify .katex-display {
        text-align: justify !important;
        margin-left: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 MRP Lot Sizing Calculator — Ultimate 10-Method Edition")
st.markdown("---")


# ==========================================
# 2. GLOSSARY SECTION (FIXED BLOCK COHESION)
# ==========================================
st.subheader("📚 Glossary")

g_row1_col1, g_row1_col2, g_row1_col3, g_row1_col4, g_row1_col5 = st.columns(5)
with g_row1_col1:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>📋 1. Lot-for-Lot (L4L)</div><div class='text-justify'><b>Concept:</b> Orders exact net requirements per discrete period.<br><b>Function:</b> Minimizes holding values straight to a zero-point baseline.</div></div>""", unsafe_allow_html=True)
with g_row1_col2:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🎯 2. Economic Order Quantity (EOQ)</div><div class='text-justify'><b>Concept:</b> Establishes a fixed lot size based on structural average baseline demand profiles.<br><b>Function:</b> Maximizes cost balance stability.</div></div>""", unsafe_allow_html=True)
with g_row1_col3:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🔍 3. Least Unit Cost (LUC)</div><div class='text-justify'><b>Concept:</b> Aggregates upcoming period blocks sequentially until total cost per unit starts to climb.<br><b>Function:</b> Dynamic cost variance control.</div></div>""", unsafe_allow_html=True)
with g_row1_col4:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>⚖️ 4. Part Period Balancing (PPB)</div><div class='text-justify'><b>Concept:</b> Syncs setup costs against cumulative holding components by targeting Economic Part Period (EPP).<br><b>Function:</b> Drives balanced inventory costs.</div></div>""", unsafe_allow_html=True)
with g_row1_col5:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>💸 5. Least Total Cost (LTC)</div><div class='text-justify'><b>Concept:</b> Accumulates periods and enforces an immediate cut-off when holding cost matches or exceeds setup cost.<br><b>Function:</b> Sharp structural step heuristic.</div></div>""", unsafe_allow_html=True)

g_row2_col1, g_row2_col2, g_row2_col3, g_row2_col4, g_row2_col5 = st.columns(5)
with g_row2_col1:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🚀 6. Silver-Meal (SM)</div><div class='text-justify'><b>Concept:</b> Minimizes average total cost per period by incrementally scanning upcoming horizons.<br><b>Function:</b> Robust under volatile demand shifts.</div></div>""", unsafe_allow_html=True)
with g_row2_col2:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>⏱️ 7. Period Order Quantity (POQ)</div><div class='text-justify'><b>Concept:</b> Transforms classical EOQ metrics into optimized integer time-phased frequency coverage intervals.<br><b>Function:</b> Stabilizes ordering cycles.</div></div>""", unsafe_allow_html=True)
with g_row2_col3:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🔒 8. Fixed Order Quantity (FOQ)</div><div class='text-justify'><b>Concept:</b> Enforces rigid predefined vendor batch sizes multipliers whenever net positions drop below safety limits.<br><b>Function:</b> Standardizes freight handling.</div></div>""", unsafe_allow_html=True)
with g_row2_col4:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🧱 9. Minimum Order Quantity (MOQ)</div><div class='text-justify'><b>Concept:</b> Guarantees every discrete manufacturing procurement run matches or scales up to a mandatory vendor floor threshold.<br><b>Function:</b> Secures supplier execution lines.</div></div>""", unsafe_allow_html=True)
with g_row2_col5:
    st.markdown("""<div class='glossary-card'><div class='glossary-title'>🔬 10. Wagner-Whitin (WW)</div><div class='text-justify'><b>Concept:</b> Dynamic Programming optimization evaluating all possible combinations across horizons.<br><b>Function:</b> Guarantees mathematically global minimum cost.</div></div>""", unsafe_allow_html=True)

st.markdown("---")


# ==========================================
# 3. SIDEBAR PARAMETER INPUTS
# ==========================================
st.sidebar.header("⚙️ Control Dashboard")

setup_cost = st.sidebar.number_input("Setup Cost", min_value=0.0, value=100.0, step=5.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit/period)", min_value=0.0, value=2.0, step=0.5)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time", min_value=0, value=1, step=1)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

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
        elif "Selected" in status_str or "Horizon End" in status_str or "Optimal" in status_str:
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
    
    if num_periods_input == 10:
        default_gr = [35, 30, 40, 0, 10, 40, 30, 0, 30, 55]
    else:
        default_gr = [0] * num_periods_input
        
    init_data = {
        'Period': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': default_gr,
        'Scheduled Receipts': [0] * num_periods_input
    }
    
    st.markdown("##### ✏️ Edit Demand & Scheduled Receipts Data Below:")
    df_raw_manual = pd.DataFrame(init_data)
    df_workbench = st.data_editor(df_raw_manual, use_container_width=True, hide_index=True)

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
    
    st.markdown("##### Input Data Matrix Summary View (Transposed):")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    if input_method == "Manual Entry":
        st.dataframe(df_preview_transposed, use_container_width=True)
        df_edited_preview = df_preview_transposed
    else:
        df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
        
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()


    # ==========================================
    # INITIAL STRATEGY MODULES (TABS INITIALIZATION)
    # ==========================================
    st.markdown("---")
    st.subheader("⚙️ Lot Sizing Operational Performance Strategy Modules")
    
    tabs_list = st.tabs([
        "📋 L4L", "🎯 EOQ", "🔍 LUC", "⚖️ PPB", "🚀 Silver-Meal", 
        "⏱️ POQ", "🔒 FOQ", "🧱 MOQ", "💸 LTC", "🔬 Wagner-Whitin"
    ])

    with tabs_list[6]:
        fixed_lot_size = st.number_input("Enter Fixed Order Size (FOQ Multiplier):", min_value=0, value=0, step=5)
    with tabs_list[7]:
        min_order_qty = st.number_input("Enter Minimum Order Quantity (MOQ):", min_value=0, value=0, step=5)


    # ==========================================
    # CORE PROCESSING MATHEMATICAL ALGORITHMS
    # ==========================================
    def calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt, f_lot, m_qty, build_trace=True):
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
                
                covered_periods_str = ", ".join([period_labels[m] for m in range(idx, k+1)])
                
                if uc < min_uc:  
                    min_uc, best_k = uc, k
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d, 
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 
                            'Unit Cost': uc, 'Status': 'Feasible'
                        })
                else:
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d, 
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 
                            'Unit Cost': uc, 'Status': 'Stop ⚠️ (Limit Exceeded)'
                        })
                    break
            
            if build_trace:
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
        total_demand_gross = sum(demands)
        eoq_raw_size = math.sqrt((2 * avg_demand_gross * setup) / hold) if hold > 0 else 0
        eoq_size = math.ceil(eoq_raw_size)
        eoq_rec = [0] * n
        rem_stok = 0
        
        if hold > 0:
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
                    if build_trace:
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
                        if build_trace:
                            t_log.append({
                                'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                                'Target EPP': epp_limit, 'Accumulated Part-Period': cum_part_period,
                                'Status': 'Feasible (Closer Beyond Limit)'
                            })
                    else:
                        if build_trace:
                            t_log.append({
                                'Periods Covered': covered_periods_str, 'Total Units': acc_d + net_req[k],
                                'Target EPP': epp_limit, 'Accumulated Part-Period': new_cum_part_period,
                                'Status': 'Stop ⚠️ (Limit Exceeded)'
                            })
                    break
                    
            if build_trace:
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

        # 5. SILVER-MEAL (SM)
        sm_rec = [0] * n
        sm_trace_logs = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue
            best_k = idx
            min_avg_cost = float('inf')
            acc_d, acc_h = 0, 0
            t_log = []
            
            for k in range(idx, n):
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                t_cost = setup + acc_h
                n_periods_covered = k - idx + 1
                avg_cost = t_cost / n_periods_covered
                
                covered_periods_str = ", ".join([period_labels[m] for m in range(idx, k+1)])
                
                if avg_cost < min_avg_cost:
                    min_avg_cost = avg_cost
                    best_k = k
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost,
                            'Average Cost/Period': avg_cost, 'Status': 'Feasible'
                        })
                else:
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost,
                            'Average Cost/Period': avg_cost, 'Status': 'Stop ⚠️ (Limit Exceeded)'
                        })
                    break
                    
            if build_trace:
                df_step = pd.DataFrame(t_log)
                if not df_step.empty:
                    stop_exists = df_step['Status'].str.contains('Stop').any()
                    if stop_exists:
                        stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                        if stop_idx > 0:
                            df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
                    else:
                        df_step.at[df_step.index[-1], 'Status'] = 'Horizon End (Optimal)'
                sm_trace_logs.append(df_step)
                
            sm_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
            
        sm_poh, sm_rel = generate_poh_and_release(sm_rec)
        c_sm_setup = sum(1 for x in sm_rec if x > 0) * setup
        c_sm_hold = sum(max(0, x) for x in sm_poh) * hold

        # 6. PERIOD ORDER QUANTITY (POQ)
        poq_raw_interval = eoq_size / avg_demand_gross if avg_demand_gross > 0 and eoq_size > 0 else 1
        poq_interval = max(1, round(poq_raw_interval))
        
        poq_rec = [0] * n
        i = 0
        while i < n:
            window_end = min(i + poq_interval, n)
            total_window_net = sum(net_req[i:window_end])
            if total_window_net > 0:
                poq_rec[i] = total_window_net  
            i = window_end                 
            
        poq_poh, poq_rel = generate_poh_and_release(poq_rec)
        c_poq_setup = sum(1 for x in poq_rec if x > 0) * setup
        c_poq_hold = sum(max(0, x) for x in poq_poh) * hold

        # 7. FIXED ORDER QUANTITY (FOQ)
        foq_rec = [0] * n
        c_foq_setup, c_foq_hold = 0.0, 0.0
        if f_lot > 0:
            rem_foq_stok = 0
            for i in range(n):
                if net_req[i] > 0:
                    if rem_foq_stok < net_req[i]:
                        needed = net_req[i] - rem_foq_stok
                        multipliers = math.ceil(needed / f_lot)
                        foq_rec[i] = multipliers * f_lot
                        rem_foq_stok = (foq_rec[i] + rem_foq_stok) - net_req[i]
                    else:
                        rem_foq_stok -= net_req[i]
                        
        foq_poh, foq_rel = generate_poh_and_release(foq_rec)
        if f_lot > 0:
            c_foq_setup = sum(1 for x in foq_rec if x > 0) * setup
            c_foq_hold = sum(max(0, x) for x in foq_poh) * hold

        # 8. MINIMUM ORDER QUANTITY (MOQ)
        moq_rec = [0] * n
        c_moq_setup, c_moq_hold = 0.0, 0.0
        if m_qty > 0:
            rem_moq_stok = 0
            for i in range(n):
                if net_req[i] > 0:
                    if rem_moq_stok < net_req[i]:
                        needed = net_req[i] - rem_moq_stok
                        if needed < m_qty:
                            moq_rec[i] = m_qty
                        else:
                            moq_rec[i] = needed
                        rem_moq_stok = (moq_rec[i] + rem_moq_stok) - net_req[i]
                    else:
                        rem_moq_stok -= net_req[i]
                        
        moq_poh, moq_rel = generate_poh_and_release(moq_rec)
        if m_qty > 0:
            c_moq_setup = sum(1 for x in moq_rec if x > 0) * setup
            c_moq_hold = sum(max(0, x) for x in moq_poh) * hold

        # 9. LEAST TOTAL COST (LTC)
        ltc_rec = [0] * n
        ltc_trace_logs = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue
            best_k = idx
            acc_d, acc_h = 0, 0
            t_log = []
            for k in range(idx, n):
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                covered_periods_str = ", ".join([period_labels[m] for m in range(idx, k+1)])
                
                if acc_h < setup:
                    best_k = k
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Status': 'Feasible'
                        })
                    if hold == 0:  
                        break
                else:
                    if build_trace:
                        t_log.append({
                            'Periods Covered': covered_periods_str, 'Total Units': acc_d,
                            'Setup Cost': setup, 'Holding Cost': acc_h, 'Status': 'Stop ⚠️ (Holding ≥ Setup)'
                        })
                    break
                    
            if build_trace:
                df_step = pd.DataFrame(t_log)
                if not df_step.empty:
                    stop_exists = df_step['Status'].str.contains('Stop').any()
                    if stop_exists:
                        stop_idx = df_step[df_step['Status'].str.contains('Stop')].index[0]
                        if stop_idx > 0:
                            df_step.at[stop_idx - 1, 'Status'] = 'Selected (Optimal)'
                    else:
                        df_step.at[df_step.index[-1], 'Status'] = 'Horizon End (Optimal)'
                ltc_trace_logs.append(df_step)
                
            ltc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
            
        ltc_poh, ltc_rel = generate_poh_and_release(ltc_rec)
        c_ltc_setup = sum(1 for x in ltc_rec if x > 0) * setup
        c_ltc_hold = sum(max(0, x) for x in ltc_poh) * hold

        # 10. WAGNER-WHITIN (WW) — Exact DP Path Engine
        INF = float('inf')
        f = [INF] * (n + 1)
        order_at = [0] * (n + 1)
        f[0] = 0
        
        for j in range(1, n + 1):
            if net_req[j-1] == 0:
                f[j] = f[j-1]
                order_at[j] = order_at[j-1]
                continue
            for i in range(1, j + 1):
                holding = sum(net_req[k-1] * hold * (k - i) for k in range(i, j + 1))
                cost = f[i-1] + setup + holding
                if cost < f[j]:
                    f[j] = cost
                    order_at[j] = i
                    
        ww_rec = [0] * n
        j = n
        ww_windows = [] 
        while j > 0:
            if net_req[j-1] == 0:
                j -= 1
                continue
            i = order_at[j]
            if i == 0:  
                j -= 1
                continue
            ww_rec[i-1] = sum(net_req[i-1:j])
            ww_windows.insert(0, (i, j))
            j = i - 1
            
        ww_poh, ww_rel = generate_poh_and_release(ww_rec)
        c_ww_setup = sum(1 for x in ww_rec if x > 0) * setup
        c_ww_hold = sum(max(0, x) for x in ww_poh) * hold
        
        ww_trace_logs = []
        if build_trace:
            for (w_start, w_end) in ww_windows:
                window_rows = []
                for j_val in range(w_start, w_end + 1):
                    if net_req[j_val-1] == 0: continue
                    for i_val in range(w_start, j_val + 1):
                        # CRASH BUG RESOLVED BY DEWA CODING AUDIT (Murni menggunakan list comprehension standar tanpa enumerate)
                        holding = sum(net_req[k-1] * hold * (k - i_val) for k in range(i_val, j_val + 1))
                        cost = f[i_val-1] + setup + holding
                        is_optimal = (order_at[j_val] == i_val and cost == f[j_val])
                        window_rows.append({
                            'Order Period': period_labels[i_val-1],
                            'Covers Until': period_labels[j_val-1],
                            'Cumulative Holding': holding,
                            'Evaluated Cost': cost,
                            'Status': 'Optimal Selection ✅' if is_optimal else 'Feasible Combination'
                        })
                if window_rows:
                    ww_trace_logs.append(pd.DataFrame(window_rows))

        return {
            'net_req': net_req,
            'total_demand_gross': total_demand_gross,
            'avg_demand_gross': avg_demand_gross,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_trace_logs},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': c_eoq_setup, 'hold': c_eoq_hold, 'total': c_eoq_setup + c_eoq_hold, 'raw_size': eoq_raw_size, 'size': eoq_size},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': c_ppb_setup, 'hold': c_ppb_hold, 'total': c_ppb_setup + c_ppb_hold, 'iters': ppb_trace_logs, 'epp': epp_limit},
            'sm': {'poh': sm_poh, 'rec': sm_rec, 'rel': sm_rel, 'setup': c_sm_setup, 'hold': c_sm_hold, 'total': c_sm_setup + c_sm_hold, 'iters': sm_trace_logs},
            'poq': {'poh': poq_poh, 'rec': poq_rec, 'rel': poq_rel, 'setup': c_poq_setup, 'hold': c_poq_hold, 'total': c_poq_setup + c_poq_hold, 'raw_interval': poq_raw_interval, 'interval': poq_interval},
            'foq': {'poh': foq_poh, 'rec': foq_rec, 'rel': foq_rel, 'setup': c_foq_setup, 'hold': c_foq_hold, 'total': c_foq_setup + c_foq_hold, 'size': f_lot},
            'moq': {'poh': moq_poh, 'rec': moq_rec, 'rel': moq_rel, 'setup': c_moq_setup, 'hold': c_moq_hold, 'total': c_moq_setup + c_moq_hold, 'min_limit': m_qty},
            'ltc': {'poh': ltc_poh, 'rec': ltc_rec, 'rel': ltc_rel, 'setup': c_ltc_setup, 'hold': c_ltc_hold, 'total': c_ltc_setup + c_ltc_hold, 'iters': ltc_trace_logs},
            'ww': {'poh': ww_poh, 'rec': ww_rec, 'rel': ww_rel, 'setup': c_ww_setup, 'hold': c_ww_hold, 'total': c_ww_setup + c_ww_hold, 'iters': ww_trace_logs}
        }

    # Operational Logic Run With Complete Trace Build Activated
    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time, fixed_lot_size, min_order_qty, build_trace=True)
    num_periods = len(gross_req)

    # Global warning guard for zero holding cost (LTC rule constraint)
    if holding_cost == 0:
        st.warning("⚠️ **Holding Cost set to 0:** LTC and iterative models will automatically consolidate all parameters into a single bulk launch load pattern.")

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
            st.error(f"🚨 Shortage Warning: Safety stock violation / stockout occurred in periods: {', '.join(stockout_periods)}")
        if max(data_dict['poh']) > max_cap:
            st.error(f"⚠️ Capacity Boundary Overrun: Projected On Hand exceeds the warehouse capacity limit ({max_cap} units).")

    def render_cost_audit_window(data_dict, setup_val, hold_val, rec_array, poh_array):
        order_count = sum(1 for x in rec_array if x > 0)
        sum_poh = sum(max(0, x) for x in poh_array)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.expander("🛠️ Setup Cost Detail"):
                st.markdown(f"""<div class='text-justify'><b>Formula:</b><br>Orders Count &times; Unit Setup Cost<br><br><b>Calculation:</b><br>{order_count} &times; {setup_val:,.2f}<br><br><b>Total:</b> {data_dict['setup']:,.2f}</div>""", unsafe_allow_html=True)
        with c2:
            with st.expander("📦 Holding Cost Detail"):
                st.markdown(f"""<div class='text-justify'><b>Formula:</b><br>(&sum; Projected On Hand) &times; Holding Rate<br><br><b>Calculation:</b><br>{sum_poh} &times; {hold_val:,.2f}<br><br><b>Total:</b> {data_dict['hold']:,.2f}</div>""", unsafe_allow_html=True)
        with c3:
            with st.expander("💰 Total Operational Cost"):
                st.markdown(f"""<div class='text-justify'><b>Formula:</b><br>Setup Cost + Holding Cost<br><br><b>Calculation:</b><br>{data_dict['setup']:,.2f} + {data_dict['hold']:,.2f}<br><br><b>Total:</b> <b>{data_dict['total']:,.2f}</b></div>""", unsafe_allow_html=True)


    # ==========================================
    # 5. METHODS MODULES EXECUTION WORKBENCH TABS CONTENT
    # ==========================================
    # TAB 1: L4L
    with tabs_list[0]:
        st.subheader("Lot-for-Lot (L4L) Performance Execution Model")
        render_mrp_grid_view(res['l4l'], max_capacity, safety_stock)
        render_cost_audit_window(res['l4l'], setup_cost, holding_cost, res['l4l']['rec'], res['l4l']['poh'])

    # TAB 2: EOQ
    with tabs_list[1]:
        st.subheader("Economic Order Quantity (EOQ) Optimization")
        if holding_cost == 0:
            st.error("⚠️ **Mathematical Error:** Holding cost = 0. Rumus EOQ membutuhkan nilai $H > 0$ agar tidak terjadi pembagian dengan angka nol (Division by Zero).")
        else:
            with st.expander("🔬 CLICK HERE TO VIEW FORMULA LOG CALCULATIONS (EOQ)", expanded=True):
                avg_demand_fmt = f"{res['avg_demand_gross']:.4f}"
                setup_fmt = f"{setup_cost:,.2f}"
                hold_fmt = f"{holding_cost:,.2f}"
                eoq_raw_fmt = f"{res['eoq']['raw_size']:.4f}"
                
                st.markdown('<div class="text-justify">', unsafe_allow_html=True)
                st.markdown("### 📝 Sizing Steps for EOQ:")
                st.markdown("##### 1. Identify Input Gross Requirements Data Matrix:")
                st.write(f"- Data per Period: `{gross_req}`")
                st.write(f"- Total Demand ($\sum \\text{{Gross Req}}$) = `{res['total_demand_gross']}` units")
                st.write(f"- Planning Horizon ($n$) = `{num_periods}` periods")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="math-justify">', unsafe_allow_html=True)
                st.markdown(f"$$\\text{{Calculate Average Demand (D):}}$$")
                st.markdown(f"$$D = \\frac{{\\sum \\text{{Gross Req}}}}{{n}}$$")
                st.markdown(f"$$D = \\frac{{{res['total_demand_gross']}}}{{{num_periods}}}$$")
                st.markdown(f"$$D = {avg_demand_fmt}\\text{{ units/period}}$$")
                
                st.markdown("##### 2. Standard Square-Root Mathematical Equation Substitution:")
                st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times D \\times \\text{{Setup Cost}}}}{{\\text{{Holding Cost}}}}}}$$")
                st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times {avg_demand_fmt} \\times {setup_fmt}}}{{{hold_fmt}}}}}$$")
                st.markdown(f"$$EOQ = {eoq_raw_fmt}\\text{{ units}}$$")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="text-justify">', unsafe_allow_html=True)
                st.markdown("##### 3. Discrete Upper Integer Ceiling Rounding:")
                st.markdown(f"- Rounded up via ceiling constraints: **`{res['eoq']['size']}` units**.")
                st.markdown('</div>', unsafe_allow_html=True)
                
            st.info(f"💡 **Lot Sizing Matrix Status:** Fixed EOQ profile is locked at **{res['eoq']['size']} units** per order.")
            render_mrp_grid_view(res['eoq'], max_capacity, safety_stock)
            render_cost_audit_window(res['eoq'], setup_cost, holding_cost, res['eoq']['rec'], res['eoq']['poh'])

    # TAB 3: LUC
    with tabs_list[2]:
        st.subheader("Least Unit Cost (LUC) Iterative Consolidation Grid")
        fmt_luc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'Unit Cost': '{:.4f}'}
        for step_idx, df_step in enumerate(res['luc']['iters']):
            if df_step is None or df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_luc), hide_index=True, use_container_width=True)
        render_mrp_grid_view(res['luc'], max_capacity, safety_stock)
        render_cost_audit_window(res['luc'], setup_cost, holding_cost, res['luc']['rec'], res['luc']['poh'])

    # TAB 4: PPB
    with tabs_list[3]:
        st.subheader("Part Period Balancing (PPB) Dynamic Policy Grid")
        with st.expander("🔬 CLICK HERE TO VIEW DETAILED FORMULA LOG CALCULATIONS (PPB)", expanded=True):
            setup_fmt = f"{setup_cost:,.2f}"
            hold_fmt = f"{holding_cost:,.2f}"
            epp_fmt = f"{res['ppb']['epp']:.4f}" if holding_cost > 0 else "INF"
            
            st.markdown('<div class="text-justify">', unsafe_allow_html=True)
            st.markdown("### 📝 Sizing Steps for PPB:")
            st.markdown("##### 1. Identify Operational Control Parameters:")
            st.write(f"- Setup Cost Value = `{setup_cost:,.2f}` | Holding Cost Value = `{holding_cost:,.2f}`")
            st.markdown("##### 2. Calculate Balanced Economic Part Period (EPP) Target Limit Baseline:")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="math-justify">', unsafe_allow_html=True)
            st.markdown(f"$$EPP = \\frac{{\\text{{Setup Cost}}}}{{\\text{{Holding Cost}}}}$$")
            st.markdown(f"$$EPP = \\frac{{{setup_fmt}}}{{{hold_fmt}}}$$")
            st.markdown(f"$$EPP = {epp_fmt}\\text{{ part-periods}}$$")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="text-justify">', unsafe_allow_html=True)
            st.markdown(f"💡 **Part Period Matrix Target Status:** The EPP target limit constraint is locked at **{epp_fmt}** part-periods.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        fmt_ppb = {'Target EPP': '{:.2f}', 'Accumulated Part-Period': '{:.2f}'}
        for step_idx, df_step in enumerate(res['ppb']['iters']):
            if df_step is None or df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_ppb), hide_index=True, use_container_width=True)
        render_mrp_grid_view(res['ppb'], max_capacity, safety_stock)
        render_cost_audit_window(res['ppb'], setup_cost, holding_cost, res['ppb']['rec'], res['ppb']['poh'])

    # TAB 5: SM
    with tabs_list[4]:
        st.subheader("Silver-Meal (SM) Criterion Period Cost Average Heuristic")
        fmt_sm = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'Average Cost/Period': '{:.4f}'}
        for step_idx, df_step in enumerate(res['sm']['iters']):
            if df_step is None or df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_sm), hide_index=True, use_container_width=True)
        render_mrp_grid_view(res['sm'], max_capacity, safety_stock)
        render_cost_audit_window(res['sm'], setup_cost, holding_cost, res['sm']['rec'], res['sm']['poh'])

    # TAB 6: POQ
    with tabs_list[5]:
        st.subheader("Period Order Quantity (POQ) Time-Phased Sizing")
        if holding_cost == 0:
            st.error("⚠️ EOQ tidak valid karena Holding Cost = 0. Otomatis POQ tidak dapat dievaluasi.")
        else:
            with st.expander("🔬 CLICK HERE TO VIEW DETAILED FORMULA LOG CALCULATIONS (POQ)", expanded=True):
                eoq_size_fmt = f"{res['eoq']['size']}"
                avg_demand_fmt = f"{res['avg_demand_gross']:.4f}"
                poq_raw_fmt = f"{res['poq']['raw_interval']:.4f}"
                
                st.markdown('<div class="text-justify">', unsafe_allow_html=True)
                st.markdown("### 📝 Sizing Steps for POQ:")
                st.markdown("##### 1. Calculate Dynamic Ordering Frequency Coverage ($P_{oq}$):")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="math-justify">', unsafe_allow_html=True)
                st.markdown(f"$$P_{{oq}} = \\frac{{\\text{{EOQ Size}}}}{{D}}$$")
                st.markdown(f"$$P_{{oq}} = \\frac{{{eoq_size_fmt}}}{{{avg_demand_fmt}}}$$")
                st.markdown(f"$$P_{{oq}} = {poq_raw_fmt}\\text{{ periods}}$$")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="text-justify">', unsafe_allow_html=True)
                st.markdown("##### 2. Discrete Standard Integer Rounding Adjustment:")
                st.markdown(f"- Rounded via standard constraints: **`{res['poq']['interval']}` periods**.")
                st.markdown('</div>', unsafe_allow_html=True)
                
            st.info(f"💡 **POQ Policy Status:** Each order cycle covers **{res['poq']['interval']} periods**.")
            render_mrp_grid_view(res['poq'], max_capacity, safety_stock)
            render_cost_audit_window(res['poq'], setup_cost, holding_cost, res['poq']['rec'], res['poq']['poh'])

    # TAB 7: FOQ
    with tabs_list[6]:
        st.subheader("Fixed Order Quantity (FOQ) Rigid Sizing Model")
        if fixed_lot_size <= 0:
            st.warning("⚠️ FOQ calculation is disabled. Enter a Fixed Order Size (> 0) above to activate.")
        else:
            st.info(f"🔒 **FOQ Constraint Active:** Locked to multiples of **{res['foq']['size']} units**.")
            render_mrp_grid_view(res['foq'], max_capacity, safety_stock)
            render_cost_audit_window(res['foq'], setup_cost, holding_cost, res['foq']['rec'], res['foq']['poh'])

    # TAB 8: MOQ
    with tabs_list[7]:
        st.subheader("Minimum Order Quantity (MOQ) Supplier Boundary Model")
        if min_order_qty <= 0:
            st.warning("⚠️ MOQ calculation is disabled. Enter a Minimum Order Quantity (> 0) above to activate.")
        else:
            st.info(f"🧱 **MOQ Constraint Active:** Threshold enforced at **{res['moq']['min_limit']} units**.")
            render_mrp_grid_view(res['moq'], max_capacity, safety_stock)
            render_cost_audit_window(res['moq'], setup_cost, holding_cost, res['moq']['rec'], res['moq']['poh'])

    # TAB 9: LTC
    with tabs_list[8]:
        st.subheader("💸 Least Total Cost (LTC) Sequential Cut-off Grid")
        fmt_ltc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}'}
        for step_idx, df_step in enumerate(res['ltc']['iters']):
            if df_step is None or df_step.empty: continue
            with st.expander(f"Iteration Block {step_idx + 1}", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_ltc), hide_index=True, use_container_width=True)
        render_mrp_grid_view(res['ltc'], max_capacity, safety_stock)
        render_cost_audit_window(res['ltc'], setup_cost, holding_cost, res['ltc']['rec'], res['ltc']['poh'])

    # TAB 10: WAGNER-WHITIN (WW)
    with tabs_list[9]:
        st.subheader("🔬 Wagner-Whitin (WW) Exact Dynamic Programming Matrix")
        st.success("🎯 **Global Optimal Solution:** This exact algorithmic model evaluates all valid multi-period paths to secure the global cost minimum.")
        
        fmt_ww = {'Cumulative Holding': '{:.2f}', 'Evaluated Cost': '{:.2f}'}
        if res['ww']['iters']:
            for w_idx, df_window in enumerate(res['ww']['iters']):
                if df_window is None or df_window.empty: continue
                with st.expander(f"Order Window Segment Block {w_idx + 1}", expanded=True):
                    st.dataframe(df_window.style.apply(style_iteration_rows, axis=None).format(fmt_ww), hide_index=True, use_container_width=True)
        else:
            st.info("No trace operations needed for zero net requirement arrays.")
                
        render_mrp_grid_view(res['ww'], max_capacity, safety_stock)
        render_cost_audit_window(res['ww'], setup_cost, holding_cost, res['ww']['rec'], res['ww']['poh'])


    # ==========================================
    # 6. GLOBAL PERFORMANCE MATRIX COMPARISON
    # ==========================================
    st.markdown("---")
    st.header("🏁 Strategic Portfolio Cost Summary Comparison Matrix")
    
    biaya_dict = {
        'L4L': res['l4l']['total'], 'LUC': res['luc']['total'], 'PPB': res['ppb']['total'],
        'SM': res['sm']['total'], 'LTC': res['ltc']['total'], 'WW': res['ww']['total']
    }
    if holding_cost > 0:
        biaya_dict['EOQ'] = res['eoq']['total']
        biaya_dict['POQ'] = res['poq']['total']
    if fixed_lot_size > 0:
        biaya_dict['FOQ'] = res['foq']['total']
    if min_order_qty > 0:
        biaya_dict['MOQ'] = res['moq']['total']
    
    min_cost = min(biaya_dict.values())
    best_methods = [k for k, v in biaya_dict.items() if v == min_cost]
    
    grid_cards = st.columns(5)
    m_keys = list(biaya_dict.keys())
    
    for idx, key in enumerate(m_keys):
        col_target = grid_cards[idx % 5]
        with col_target:
            is_best = key in best_methods
            sub_text = "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 13px; font-weight: bold;'>⚠️ Inefficient by {biaya_dict[key] - min_cost:,.2f}</div>"
            caption_text = "<div style='font-size: 11px; color: #555555; font-style: italic; margin-top: 4px;'>🔬 Exact optimal (Dynamic Programming)</div>" if key == 'WW' else ""
            
            st.markdown(f"""
                <div style='background-color: #f4efdc; padding: 14px; border-radius: 8px; border-left: 5px solid #6a0708; margin-bottom: 15px; min-height: 140px;'>
                    <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost {key}</div>
                    <div style='font-size: 21px; font-weight: 700; color: #111111; margin-top: 4px;'>{biaya_dict[key]:,.2f}</div>
                    {sub_text}
                    {caption_text}
                </div>
            """, unsafe_allow_html=True)

    methods_string = " & ".join(best_methods)
    st.markdown(f"""
    <div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-left: 5px solid #2e7d32; padding: 14px; border-radius: 4px; margin-top: 20px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <span style="color: #2e7d32; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 4px;">
            🎯 Strategy Recommendation:
        </span>
        <span style="color: #111111; font-size: 15px; font-weight: 500;">
            It is highly recommended to <span style="color: #2e7d32; font-weight: 700;">Apply {methods_string} Model</span> to maximize overall operational efficiency.
        </span>
    </div>
    """, unsafe_allow_html=True)


    # ==========================================
    # 7. GRAPH VISUALIZATION (SHADOWING RESOLVED)
    # ==========================================
    st.markdown("---")
    st.subheader("📉 Parametric Sensitivity Analysis Charts")
    
    cg1, cg2 = st.columns(2)
    with cg1:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        fig.patch.set_facecolor('#faf8f2')
        ax.set_facecolor('#faf8f2')
        
        color_palette = ['#444444', '#e65c00', '#6a0708', '#2a7b4c', '#0288d1', '#7b1fa2', '#1565c0', '#2e7d32', '#d32f2f', '#f57c00']
        active_colors = color_palette[:len(biaya_dict)]
        
        ax.bar(biaya_dict.keys(), biaya_dict.values(), color=active_colors, width=0.5)
        ax.set_title("Comparison of Lot Sizing Methods", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax.set_xlabel('Lot Sizing Strategy', color='#111', fontsize=9, fontweight='bold')
        ax.set_ylabel('Total Cost', color='#111', fontsize=9, fontweight='bold')
        ax.grid(axis='y', linestyle=':', alpha=0.6)
        st.pyplot(fig)
        
    with cg2:
        pct_integers = np.linspace(-30, 30, 13, dtype=int)
        s_l4l, s_eoq, s_luc, s_ppb, s_sm, s_poq, s_foq, s_moq, s_ltc, s_ww, labels_pct = [], [], [], [], [], [], [], [], [], [], []
        
        for p_val in pct_integers:
            scale_factor = 1.0 + (p_val / 100.0)
            sim_demand = [int(round(d * scale_factor)) for d in gross_req]
            
            s_res = calculate_multi_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time, fixed_lot_size, min_order_qty, build_trace=False)
            
            s_l4l.append(s_res['l4l']['total'])
            s_luc.append(s_res['luc']['total'])
            s_ppb.append(s_res['ppb']['total'])
            s_sm.append(s_res['sm']['total'])
            s_ltc.append(s_res['ltc']['total'])
            s_ww.append(s_res['ww']['total'])
            if holding_cost > 0:
                s_eoq.append(s_res['eoq']['total'])
                s_poq.append(s_res['poq']['total'])
            if fixed_lot_size > 0:
                s_foq.append(s_res['foq']['total'])
            if min_order_qty > 0:
                s_moq.append(s_res['moq']['total'])
            
            labels_pct.append(f"{p_val:+}%")
        
        fig2, ax2 = plt.subplots(figsize=(7, 4.2))
        fig2.patch.set_facecolor('#faf8f2')
        ax2.set_facecolor('#faf8f2')
        
        ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#444444', linewidth=1.5)
        ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#6a0708', linewidth=1.5)
        ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#2a7b4c', linewidth=1.5)
        ax2.plot(labels_pct, s_sm, marker='d', label='SM', color='#0288d1', linewidth=1.5)
        ax2.plot(labels_pct, s_ltc, marker='P', label='LTC', color='#1565c0', linewidth=1.5)
        ax2.plot(labels_pct, s_ww, marker='H', label='WW', color='#2e7d32', linewidth=2.0, linestyle='--')
        if holding_cost > 0:
            ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#e65c00', linewidth=1.5)
            ax2.plot(labels_pct, s_poq, marker='v', label='POQ', color='#7b1fa2', linewidth=1.5)
        if fixed_lot_size > 0:
            ax2.plot(labels_pct, s_foq, marker='*', label='FOQ', color='#d32f2f', linewidth=1.5)
        if min_order_qty > 0:
            ax2.plot(labels_pct, s_moq, marker='X', label='MOQ', color='#f57c00', linewidth=1.5)
        
        ax2.set_title("Demand Change Sensitivity Chart", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax2.set_ylabel('Simulated Total Incurred Cost', color='#111', fontsize=9, fontweight='bold')
        ax2.set_xlabel('Customer Demand Change Sensitivity', color='#111', fontsize=9, fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.6)
        ax2.legend(facecolor='#faf8f2', fontsize=8, loc='upper left')
        plt.xticks(rotation=30)
        st.pyplot(fig2)


    # ==========================================
    # 8. REPORT EXPORT WORKBENCH
    # ==========================================
    st.markdown("---")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=period_labels).T.to_excel(writer, sheet_name="Baseline Framework")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="L4L Plan")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="LUC Plan")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="PPB Plan")
        pd.DataFrame({'Projected On Hand': res['sm']['poh'], 'Planned Order Receipts': res['sm']['rec'], 'Planned Order Releases': res['sm']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="Silver-Meal Plan")
        pd.DataFrame({'Projected On Hand': res['ltc']['poh'], 'Planned Order Receipts': res['ltc']['rec'], 'Planned Order Releases': res['ltc']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="LTC Plan")
        pd.DataFrame({'Projected On Hand': res['ww']['poh'], 'Planned Order Receipts': res['ww']['rec'], 'Planned Order Releases': res['ww']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="WW Plan")
        if holding_cost > 0:
            pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="EOQ Plan")
            pd.DataFrame({'Projected On Hand': res['poq']['poh'], 'Planned Order Receipts': res['poq']['rec'], 'Planned Order Releases': res['poq']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="POQ Plan")
        if fixed_lot_size > 0:
            pd.DataFrame({'Projected On Hand': res['foq']['poh'], 'Planned Order Receipts': res['foq']['rec'], 'Planned Order Releases': res['foq']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="FOQ Plan")
        if min_order_qty > 0:
            pd.DataFrame({'Projected On Hand': res['moq']['poh'], 'Planned Order Receipts': res['moq']['rec'], 'Planned Order Releases': res['moq']['rel']}, index=period_labels).T.to_excel(writer, sheet_name="MOQ Plan")
    
    buffer.seek(0)
    
    st.markdown("""
        <style>
        div.stDownloadButton > button p {
            color: #6a0708 !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
    with btn_col2:
        st.download_button(
            label="📥 Download Plan Document Report (10 Methods)", 
            data=buffer, 
            file_name="MRP_Lot_Sizing_Ultimate_Report.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True 
        )
else:
    st.info("Please initialize input values or upload transaction vectors to run calculation routines.")
