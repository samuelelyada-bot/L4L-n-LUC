import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import io

# ==========================================
# 1. PAGE CONFIGURATION & ENTERPRISE CSS INJECTION
# ==========================================
st.set_page_config(page_title="NexusMRP Engine - Enterprise DSS", layout="wide")

# Custom CSS for Deep Maroon Theme, Pastel Table Masking, and Structural Windows
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #faf8f2;
    }
    
    /* Main Content Headers */
    h1, h2, h3 {
        color: #6a0708 !important;
        font-weight: 700 !important;
    }
    
    h4, h5, h6 {
        color: #111111 !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar Overhaul (Deep Maroon Dominant) */
    [data-testid="stSidebar"] {
        background-color: #6a0708 !important;
    }
    
    /* CRITICAL FIX: Forces ALL labels, text paragraphs, and spans inside Sidebar to Cream/White */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #faf8f2 !important;
        font-weight: 600 !important;
    }
    
    /* Secondary small text inside sidebar inputs */
    [data-testid="stSidebar"] p {
        font-weight: 400 !important;
        opacity: 0.9;
    }
    
    /* Main Content Widget Labels */
    .stNumberInput label, .stRadio label {
        color: #111111 !important;
        font-weight: 600 !important;
    }
    
    /* Primary Action Buttons */
    .stButton>button {
        background-color: #6a0708 !important;
        color: #faf8f2 !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #d90429 !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.15);
    }
    
    /* Unified Window Blocks (Equation & Breakdown Containers) */
    .calculation-window {
        background-color: #f4efdc;
        border-left: 6px solid #6a0708;
        padding: 22px;
        border-radius: 6px;
        margin-bottom: 25px;
        color: #111111;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    
    .window-text-justify {
        text-align: justify;
        line-height: 1.6;
        margin-bottom: 12px;
    }
    
    /* Operational Breakdown KPI Display Cards */
    .kpi-card {
        background-color: #f4efdc;
        padding: 18px;
        border-radius: 6px;
        border-top: 4px solid #6a0708;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 NexusMRP Engine — Enterprise Decision Support System")
st.caption("Advanced Material Requirements Planning Multi-Method Optimization Platform")
st.markdown("---")

# ==========================================
# 2. GLOSSARY SECTION (SHIFTED TO THE VERY TOP — 4 MODULAR EXPANDERS)
# ==========================================
st.subheader("📚 System Reference Manual & Knowledge Base Glossary")
g_col1, g_col2, g_col3, g_col4 = st.columns(4)

with g_col1:
    with st.expander("📋 1. Lot-for-Lot (L4L)", expanded=False):
        st.markdown("""<div class='window-text-justify'>
        <b>Concept:</b> Orders exact absolute volume constraints matching discrete net periods instantly.<br><br>
        <b>Equation Paradigm:</b><br>$Lot(t) = Net\\_Requirement(t)$<br><br>
        <b>Advantage Strategy:</b> Drives inventory carrying charge factors down to bare absolute minimum zero points.
        </div>""", unsafe_allow_html=True)

with g_col2:
    with st.expander("🎯 2. Economic Order Quantity (EOQ)", expanded=False):
        st.markdown("""<div class='window-text-justify'>
        <b>Concept:</b> Establishes fixed structural sizing boundaries balancing average annualized production cycles perfectly.<br><br>
        <b>Advantage Strategy:</b> Provides high asset utilization efficiency when multi-period gross profiles maintain linear predictability constants.
        </div>""", unsafe_allow_html=True)

with g_col3:
    with st.expander("🔍 3. Least Unit Cost (LUC)", expanded=False):
        st.markdown("""<div class='window-text-justify'>
        <b>Concept:</b> Sequential search algorithm aggregating horizons continuously until individual unit cost optimization points break trends.<br><br>
        <b>Advantage Strategy:</b> Minimizes cost variations by tracking specific trial horizons dynamically.
        </div>""", unsafe_allow_html=True)

with g_col4:
    with st.expander("⚖️ 4. Part Period Balancing (PPB)", expanded=False):
        st.markdown("""<div class='window-text-justify'>
        <b>Concept:</b> Equates carrying charges against setup factors looking for optimal look-ahead closest-distance convergence coordinates.<br><br>
        <b>Advantage Strategy:</b> Achieves exceptional balancing precision across heavily spiked discrete parameter inputs.
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. SIDEBAR PARAMETER SELECTION
# ==========================================
st.sidebar.header("⚙️ Control Dashboard")

st.sidebar.subheader("Financial Factors")
setup_cost = st.sidebar.number_input("Setup / Ordering Cost", min_value=0.0, value=100000.0, step=500.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit/period)", min_value=0.0, value=2000.0, step=100.0)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("Inventory Profiles")
initial_inv = st.sidebar.number_input("Initial On-Hand Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock Level", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time Duration (Periods)", min_value=0, value=1, step=1)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("Operational Boundaries")
max_capacity = st.sidebar.number_input("Maximum Warehouse Capacity (Units)", min_value=1, value=100, step=10)


# ==========================================
# UTILITY HELPER & PASTEL MASKING FUNCTIONS
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

# FIXED: Re-engineered with ultra-soft pastel transparencies for extreme clarity
def style_iteration_rows(df_step):
    style_matrix = pd.DataFrame('', index=df_step.index, columns=df_step.columns)
    for idx, row in df_step.iterrows():
        status_str = str(row['Status'])
        if "Stop" in status_str:
            # Ultra-soft pastel pink/red transparency
            style_matrix.loc[idx] = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
        elif "Selected" in status_str or "Horizon End" in status_str:
            # Ultra-soft pastel light green transparency
            style_matrix.loc[idx] = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    return style_matrix


# ==========================================
# 4. DATA ACQUISITION & WORKBENCH EDITOR
# ==========================================
st.subheader("📊 Requirements & Inbound Supply Workbench")

input_method = st.radio(
    "Select Target Data Source Configuration:", 
    ["Upload External File (Excel / CSV)", "Interactive App Data Grid Manual Entry", "Load Pre-Configured Blueprint Template"]
)

df_workbench = None

if input_method == "Upload External File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload requirement documents (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
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
                st.error("❌ Data Engine Error: Gross Requirements (GR) attribute could not be mapped automatically.")
                
            if col_sr and col_sr in df_raw.columns:
                df_workbench['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_workbench['Scheduled Receipts'] = 0
        except Exception as e:
            st.error(f"Engine Failed to Parse Uploaded Manifest. Trace: {e}")
            
elif input_method == "Interactive App Data Grid Manual Entry":
    num_periods_input = st.number_input("Horizon Planning Length (Periods):", min_value=1, max_value=52, value=10, step=1)
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
    
    st.markdown("##### 🔍 Active Input Data Matrix Summary")
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

    # Run Calculations Engine
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
            st.error(f"⚠️ Operational Capacity Violation: Projected On-Hand exceeds maximum asset constraint threshold ({max_cap} units).")

    # FIXED CHRONOLOGY: Display calculations first, then wrap operational costs in a clean window container at the bottom
    def render_cost_audit_window(data_dict, setup_val, hold_val, rec_array, poh_array):
        order_count = sum(1 for x in rec_array if x > 0)
        sum_poh = sum(max(0, x) for x in poh_array)
        
        st.markdown("<br><h5>💰 Operational Strategy Financial Breakdown</h5>", unsafe_allow_html=True)
        st.markdown("<div class='calculation-window'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class='kpi-card'>
                <h6>Total Setup Cost</h6>
                <h3>{data_dict['setup']:,.2f}</h3>
                <p style='color:#555; font-size:12px;'>Formula:<br>{order_count} Orders × {setup_val:,.2f}</p>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='kpi-card'>
                <h6>Total Holding Cost</h6>
                <h3>{data_dict['hold']:,.2f}</h3>
                <p style='color:#555; font-size:12px;'>Formula:<br>{sum_poh} Accumulated Units × {hold_val:,.2f}</p>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class='kpi-card'>
                <h6>Total Operational Strategy Cost</h6>
                <h3 style='color: #6a0708;'>{data_dict['total']:,.2f}</h3>
                <p style='color:#555; font-size:12px;'>Sum Matrix:<br>Setup Cost + Holding Cost Summary</p>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 5. METHODS EXECUTION TABS
    # ==========================================
    st.markdown("---")
    st.subheader("⚙️ Localized Sizing Heuristics Execution Modules")
    
    t_l4l, t_eoq, t_luc, t_ppb = st.tabs([
        "📋 Lot-for-Lot (L4L)", 
        "🎯 Economic Order Quantity (EOQ)", 
        "🔍 Least Unit Cost (LUC)", 
        "⚖️ Part Period Balancing (PPB)"
    ])

    # TAB 1: LOT-FOR-LOT
    with t_l4l:
        st.subheader("Lot-for-Lot (L4L) Master Execution Matrix")
        render_mrp_grid_view(res['l4l'], max_capacity)
        render_cost_audit_window(res['l4l'], setup_cost, holding_cost, res['l4l']['rec'], res['l4l']['poh'])

    # TAB 2: EOQ (FIXED TO DOWNWARD FLOW, RATA KANAN-KIRI, WRAPPED IN 1 WINDOW)
    with t_eoq:
        st.subheader("Economic Order Quantity (EOQ) Sizing Optimization")
        
        avg_d_calc = res['eoq']['avg_demand_gross']
        val_top = 2 * avg_d_calc * setup_cost
        val_div = val_top / holding_cost
        eoq_raw_val = math.sqrt(val_div)
        
        st.markdown("#### 📝 Sizing Optimization Formulation Equation Window")
        st.markdown("<div class='calculation-window'>", unsafe_allow_html=True)
        
        st.markdown("<div class='window-text-justify'><b>Step 1: Compute Average Demand Gross Per Period (D)</b><br>"
                    "The framework aggregates all requirements split across active planning windows divided by horizon metrics to locate linear trends.</div>", unsafe_allow_html=True)
        st.latex(r"D = \frac{\sum \text{Gross Requirements}}{n} = \frac{" + str(sum(gross_req)) + "}{" + str(num_periods) + r"} = " + f"{avg_d_calc:.4f}" + r"\text{ Units/Period}")
        
        st.markdown("<div class='window-text-justify'><b>Step 2: Apply Classical Square-Root Sizing Mathematical Equation</b><br>"
                    "This calculates the absolute mathematical cross-over equilibrium balancing point where ordering cost matches structural carrying charges.</div>", unsafe_allow_html=True)
        st.latex(r"EOQ = \sqrt{\frac{2 \times D \times \text{Setup Cost}}{\text{Holding Cost}}} = \sqrt{\frac{2 \times " + f"{avg_d_calc:.4f}" + r"\times " + f"{setup_cost:.2f}" + "}{" + f"{holding_cost:.2f}" + r" }}")
        st.latex(r"EOQ = \sqrt{" + f"{val_div:.4f}" + r"} = " + f"{eoq_raw_val:.4f}" + r"\text{ Units}")
        
        st.markdown(f"<div class='window-text-justify'><b>Step 3: Discrete Upper Integer Ceiling Bound Rounding</b><br>"
                    f"Because inventory quantities cannot be processed fractionally, an upper ceiling bound locking sequence is deployed. "
                    f"Discrete Lot Factor Quantity Constraint Locked Value = <b>{res['eoq']['size']} Units</b> per Order Placement.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        render_mrp_grid_view(res['eoq'], max_capacity)
        render_cost_audit_window(res['eoq'], setup_cost, holding_cost, res['eoq']['rec'], res['eoq']['poh'])

    # TAB 3: LUC (FIXED PASTEL COLOR MASKING)
    with t_luc:
        st.subheader("Least Unit Cost (LUC) Iterative Sizing Matrix")
        st.markdown("#### 🔬 Dynamic Lot Compilation Optimization Processing Steps")
        
        fmt_luc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'Unit Cost': '{:.4f}'}
        for step_idx, df_step in enumerate(res['luc']['iters']):
            with st.expander(f"Step Block {step_idx + 1} — Lot Consolidation Initialization Trace Window", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_luc), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['luc'], max_capacity)
        render_cost_audit_window(res['luc'], setup_cost, holding_cost, res['luc']['rec'], res['luc']['poh'])

    # TAB 4: PPB (FIXED TO DOWNWARD FLOW, RATA KANAN-KIRI, WRAPPED IN 1 WINDOW)
    with t_ppb:
        st.subheader("Part Period Balancing (PPB) Dynamic Policy Execution Grid")
        
        st.markdown("#### ⚖️ Economic Part Period (EPP) Target Metric Identification Window")
        st.markdown("<div class='calculation-window'>", unsafe_allow_html=True)
        st.markdown("<div class='window-text-justify'><b>Step 1: Compute Target Balanced EPP Baseline Limit</b><br>"
                    "The system calculates the exact equilibrium threshold coefficient where the financial strain of holding one stock unit across one period perfectly balances single setup expenses.</div>", unsafe_allow_html=True)
        st.latex(r"EPP = \frac{\text{Setup Cost}}{\text{Holding Cost}} = \frac{" + f"{setup_cost:.2f}" + "}{" + f"{holding_cost:.2f}" + r"} = " + f"{res['ppb']['epp']:.4f}" + r"\text{ Part-Periods}")
        st.markdown("<div class='window-text-justify'><i>Operational Logic Insight:</i> The EPP coefficient is used as a cumulative benchmark reference scale. "
                    "Horizons are clustered continuously as long as the trial part-period sum closely balances out this target.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("#### 🔬 Balanced Horizon Iterative Search Traces Execution Stream")
        fmt_ppb = {'Target EPP': '{:.2f}', 'Accumulated Part-Period': '{:.2f}'}
        for step_idx, df_step in enumerate(res['ppb']['iters']):
            with st.expander(f"Step Block {step_idx + 1} — Part Period Equating Calibration Trace Window", expanded=True):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None).format(fmt_ppb), hide_index=True, use_container_width=True)
                
        render_mrp_grid_view(res['ppb'], max_capacity)
        render_cost_audit_window(res['ppb'], setup_cost, holding_cost, res['ppb']['rec'], res['ppb']['poh'])


    # ==========================================
    # 6. GLOBAL PERFORMANCE MATRIX COMPARISON
    # ==========================================
    st.markdown("---")
    st.header("🏁 Global Portfolio Performance Matrix Comparison")
    
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
        sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>+{diff_l4l:,.2f} Variance</div>" if diff_l4l > 0 else "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Minimum Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost L4L</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111; margin-top: 4px;'>{res['l4l']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>+{diff_luc:,.2f} Variance</div>" if diff_luc > 0 else "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Minimum Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost LUC</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111; margin-top: 4px;'>{res['luc']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>+{diff_eoq:,.2f} Variance</div>" if diff_eoq > 0 else "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Minimum Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost EOQ</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111; margin-top: 4px;'>{res['eoq']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        sub_text = f"<div style='color: #c62828; font-size: 13px; font-weight: bold;'>+{diff_ppb:,.2f} Variance</div>" if diff_ppb > 0 else "<div style='color: #2e7d32; font-size: 13px; font-weight: bold;'>🏆 Optimal Minimum Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 8px; border-left: 5px solid #6a0708;'>
                        <div style='color: #333; font-size: 13px; font-weight: 600;'>Total Cost PPB</div>
                        <div style='font-size: 22px; font-weight: 700; color: #111; margin-top: 4px;'>{res['ppb']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)

    st.success(f"🏆 Recommendation Verdict: Deploy **{best_method}** strategy to minimize structural inventory expenditures.")


    # ==========================================
    # 7. VISUALIZATION ENGINE - REVISED GRAPHS (LABELS FIXED)
    # ==========================================
    st.markdown("---")
    st.subheader("📉 Advanced Parametric Demand Stress Testing Sensitivity Analysis")
    
    cg1, cg2 = st.columns(2)
    with cg1:
        st.markdown("##### Strategy Cost Comparison Profile")
        fig, ax = plt.subplots(figsize=(7, 4.2))
        fig.patch.set_facecolor('#faf8f2')
        ax.set_facecolor('#faf8f2')
        
        # CHANGED: Clean short names, straight text, with clear Axis Labels
        ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#444444', '#6a0708', '#e65c00', '#2a7b4c'], width=0.45)
        ax.set_title("Comparison of Lot Sizing Methods", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax.set_xlabel('Lot Sizing Strategy', color='#111', fontsize=9, fontweight='bold')
        ax.set_ylabel('Total Cost', color='#111', fontsize=9, fontweight='bold')
        ax.grid(axis='y', linestyle=':', alpha=0.6)
        st.pyplot(fig)
        
    with cg2:
        st.markdown("##### Dynamic Boundary Risk Stress Profile")
        
        # FIXED CRITICAL BOUNDARY: Scaled exactly from -30% to +30% to stay perfectly inside the designated threshold
        scale_factors = np.arange(0.70, 1.35, 0.05) 
        s_l4l, s_luc, s_eoq, s_ppb, labels_pct = [], [], [], [], []
        
        for f in scale_factors:
            pct_val = int(round((f - 1) * 100))
            if pct_val > 30: # Hard stop constraint filter to remove any leak to +35%
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
        
        # CHANGED: Cleaned Legends and translated axes cleanly
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

    # ==========================================
    # 8. DATA EXPORT DISPATCH DESK
    # ==========================================
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
        label="📥 Download Data Report Manifest", 
        data=buffer, 
        file_name="NexusMRP_Optimized_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("💡 Workbench Framework Notice: Please enter data variables or upload structural manifests inside the entry section to execute system engines.")
