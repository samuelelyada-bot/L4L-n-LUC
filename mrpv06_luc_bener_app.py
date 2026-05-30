import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import math

# ==========================================
# 1. CORE CONFIGURATION & CSS STYLING (UNTOUCHED)
# ==========================================
st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 95%; }
    .text-justify { text-align: justify; text-justify: inter-word; }
    .card-metric {
        background-color: #f8f9fa;
        border-left: 5px solid #6a0708;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .badge-moq {
        background-color: #ffe3e3;
        color: #b7094c;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: 0.85em;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔬 Advanced Industrial Engineering Operations Workbench")
st.subheader("Multi-Method Material Requirements Planning (MRP) Simulation Engine")

# ==========================================
# 2. DATA ACQUISITION WORKBENCH (UNTOUCHED)
# ==========================================
st.sidebar.header("🛠️ Input Parameter")
data_mode = st.sidebar.selectbox("Mode Input Data", ["Default Template", "Input Manual Matrix", "Upload Excel Framework"])

if data_mode == "Default Template":
    demands = [35, 10, 40, 20, 15, 30, 25, 55, 40, 45, 20, 35]
    s_receipts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    period_labels = [f"P{i+1}" for i in range(12)]
elif data_mode == "Input Manual Matrix":
    dem_str = st.sidebar.text_input("Gross Requirements (pisahkan dengan koma)", "35,10,40,20,15,30,25,55,40,45,20,35")
    rec_str = st.sidebar.text_input("Scheduled Receipts (pisahkan dengan koma)", "0,0,0,0,0,0,0,0,0,0,0,0")
    lbl_str = st.sidebar.text_input("Label Periode (pisahkan dengan koma)", "P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11,P12")
    demands = [int(x.strip()) for x in dem_str.split(",")]
    s_receipts = [int(x.strip()) for x in rec_str.split(",")]
    period_labels = [x.strip() for x in lbl_str.split(",")]
else:
    uploaded_file = st.sidebar.file_uploader("Upload File Excel Baseline", type=["xlsx"])
    if uploaded_file is not None:
        df_upload = pd.read_excel(uploaded_file)
        demands = df_upload.iloc[0].tolist()
        s_receipts = df_upload.iloc[1].tolist()
        period_labels = df_upload.columns.astype(str).tolist()
    else:
        demands = [35, 10, 40, 20, 15, 30, 25, 55, 40, 45, 20, 35]
        s_receipts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        period_labels = [f"P{i+1}" for i in range(12)]

n = len(demands)

# Financial Controls & Inventory Boundaries
setup = st.sidebar.number_input("Setup Cost / Ordering Cost ($)", min_value=0.0, value=200.0, step=10.0)
hold = st.sidebar.number_input("Holding Cost / unit / periode ($)", min_value=0.0, value=2.0, step=0.5)
init_inv = st.sidebar.number_input("Persediaan Awal (Initial Inventory)", min_value=0, value=20)
ss = st.sidebar.number_input("Safety Stock (SS)", min_value=0, value=5)
lt = st.sidebar.number_input("Lead Time (LT)", min_value=0, value=1)
max_capacity = st.sidebar.number_input("Kapasitas Maksimum Gudang", min_value=0, value=500)

# SIDEBAR TAMBAHAN (SESUAI ROADMAP)
st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("🔧 Universal Constraint")
use_moq = st.sidebar.checkbox("Apply MOQ Constraint", value=False)
moq_value = st.sidebar.number_input("MOQ Value (units)", min_value=1, value=50, step=5, disabled=not use_moq)
moq_val = moq_value if use_moq else 0

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.subheader("📅 FPR Parameter")
fpr_interval = st.sidebar.number_input("FPR Interval (periods)", min_value=1, max_value=52, value=3, step=1)

build_trace = st.sidebar.checkbox("Build Iteration Trace Logs", value=True)


# ==========================================
# 3. GLOBAL SIMULATION CORE ENGINE
# ==========================================
def calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt, moq_val, foq_val_tab):
    n = len(demands)
    
    # Hitung Net Requirements Baseline
    net_req = [0] * n
    poh_baseline = [0] * n
    r_inv = init_inv
    for i in range(n):
        avail = r_inv + s_receipts[i]
        if avail < demands[i] + ss:
            net_req[i] = (demands[i] + ss) - avail
            r_inv = ss
        else:
            net_req[i] = 0
            r_inv = avail - demands[i]
        poh_baseline[i] = r_inv

    # REVISI: generate_poh_and_release dengan 3 return values & akomodasi Global MOQ
    def generate_poh_and_release(rec_lot, moq_val=0):
        actual_rec = []
        for i in range(n):
            raw = rec_lot[i]
            actual = max(raw, moq_val) if (moq_val > 0 and raw > 0) else raw
            actual_rec.append(actual)
        poh = []
        r_inv = init_inv
        for i in range(n):
            r_inv += s_receipts[i] + actual_rec[i] - demands[i]
            poh.append(r_inv)
        rel_lot = [0] * n
        for i in range(n):
            if actual_rec[i] > 0:
                target = i - lt
                rel_lot[max(0, target)] += actual_rec[i]
        return poh, rel_lot, actual_rec

    # --- 1. LOT-FOR-LOT (L4L) ---
    l4l_rec = [r for r in net_req]
    l4l_poh, l4l_rel, l4l_actual = generate_poh_and_release(l4l_rec, moq_val)
    c_l4l_setup = sum(1 for x in l4l_actual if x > 0) * setup
    c_l4l_hold  = sum(max(0, x) for x in l4l_poh) * hold

    # --- 2. ECONOMIC ORDER QUANTITY (EOQ) ---
    avg_d = sum(demands) / n
    eoq_val = math.sqrt((2 * avg_d * setup) / hold) if hold > 0 else 0
    eoq_q = max(1, round(eoq_val))
    eoq_rec = [0] * n
    r_inv_eoq = init_inv
    for i in range(n):
        avail = r_inv_eoq + s_receipts[i]
        if avail < demands[i] + ss:
            needed = (demands[i] + ss) - avail
            lots = math.ceil(needed / eoq_q)
            eoq_rec[i] = lots * eoq_q
            r_inv_eoq = avail + eoq_rec[i] - demands[i]
        else:
            eoq_rec[i] = 0
            r_inv_eoq = avail - demands[i]
    eoq_poh, eoq_rel, eoq_actual = generate_poh_and_release(eoq_rec, moq_val)
    c_eoq_setup = sum(1 for x in eoq_actual if x > 0) * setup
    c_eoq_hold  = sum(max(0, x) for x in eoq_poh) * hold

    # --- 3. PERIOD ORDER QUANTITY (POQ) ---
    poq_t = max(1, round(eoq_q / avg_d)) if avg_d > 0 else 1
    poq_rec = [0] * n
    i = 0
    while i < n:
        if net_req[i] > 0:
            w_end = min(i + poq_t, n)
            poq_rec[i] = sum(net_req[i:w_end])
            i = w_end
        else:
            i += 1
    poq_poh, poq_rel, poq_actual = generate_poh_and_release(poq_rec, moq_val)
    c_poq_setup = sum(1 for x in poq_actual if x > 0) * setup
    c_poq_hold  = sum(max(0, x) for x in poq_poh) * hold

    # --- 4. FIXED ORDER QUANTITY (FOQ) ---
    foq_rec = [0] * n
    r_inv_foq = init_inv
    for i in range(n):
        avail = r_inv_foq + s_receipts[i]
        if avail < demands[i] + ss:
            needed = (demands[i] + ss) - avail
            lots = math.ceil(needed / foq_val_tab)
            foq_rec[i] = lots * foq_val_tab
            r_inv_foq = avail + foq_rec[i] - demands[i]
        else:
            foq_rec[i] = 0
            r_inv_foq = avail - demands[i]
    foq_poh, foq_rel, foq_actual = generate_poh_and_release(foq_rec, moq_val)
    c_foq_setup = sum(1 for x in foq_actual if x > 0) * setup
    c_foq_hold  = sum(max(0, x) for x in foq_poh) * hold

    # --- 5. FIXED PERIOD REQUIREMENTS (FPR) --- BARU
    fpr_rec = [0] * n
    i = 0
    while i < n:
        window_end = min(i + fpr_interval, n)
        total_window = sum(net_req[i:window_end])
        if total_window > 0:
            fpr_rec[i] = total_window
        i = window_end
    fpr_poh, fpr_rel, fpr_actual = generate_poh_and_release(fpr_rec, moq_val)
    c_fpr_setup = sum(1 for x in fpr_actual if x > 0) * setup
    c_fpr_hold  = sum(max(0, x) for x in fpr_poh) * hold

    # --- 6. INCREMENTAL UNIT COST (IUC) --- BARU (Zero-Demand Fixed)
    iuc_rec = [0] * n
    iuc_trace_logs = []
    idx = 0
    while idx < n:
        if net_req[idx] == 0:
            idx += 1
            continue
        best_k = idx
        min_inc_uc = float('inf')
        prev_total_cost = 0
        acc_d = 0
        t_log = []
        for k in range(idx, n):
            acc_h_k = sum(net_req[m] * hold * (m - idx) for m in range(idx, k + 1))
            total_cost_k = setup + acc_h_k
            if net_req[k] == 0:
                prev_total_cost = total_cost_k
                continue
            delta_cost  = total_cost_k - prev_total_cost
            delta_units = net_req[k]
            inc_uc = delta_cost / delta_units
            acc_d += net_req[k]
            covered_str = ", ".join([f"P{m+1}" for m in range(idx, k + 1)])
            if inc_uc < min_inc_uc:
                min_inc_uc = inc_uc
                best_k = k
                prev_total_cost = total_cost_k
                if build_trace:
                    t_log.append({
                        'Periods Covered': covered_str, 'Total Units': acc_d,
                        'Setup Cost': setup, 'Holding Cost': acc_h_k,
                        'Total Cost': total_cost_k, 'Inc. Unit Cost': inc_uc,
                        'Status': 'Feasible'
                    })
            else:
                if build_trace:
                    t_log.append({
                        'Periods Covered': covered_str, 'Total Units': acc_d,
                        'Setup Cost': setup, 'Holding Cost': acc_h_k,
                        'Total Cost': total_cost_k, 'Inc. Unit Cost': inc_uc,
                        'Status': 'Stop ⚠️ (Inc. Cost Rising)'
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
            iuc_trace_logs.append(df_step)
        iuc_rec[idx] = sum(net_req[idx:best_k + 1])
        idx = best_k + 1
    iuc_poh, iuc_rel, iuc_actual = generate_poh_and_release(iuc_rec, moq_val)
    c_iuc_setup = sum(1 for x in iuc_actual if x > 0) * setup
    c_iuc_hold  = sum(max(0, x) for x in iuc_poh) * hold

    # --- 7. LEAST TOTAL COST (LTC) ---
    ltc_rec = [0] * n
    ltc_trace_logs = []
    i = 0
    while i < n:
        if net_req[i] > 0:
            best_k = i
            min_diff = float('inf')
            t_log = []
            for k in range(i, n):
                h_cost = sum(net_req[m] * hold * (m - i) for m in range(i, k + 1))
                diff = abs(h_cost - setup)
                if build_trace:
                    t_log.append({'Range': f"P{i+1}-P{k+1}", 'Setup': setup, 'Holding': h_cost, 'Diff': diff})
                if diff < min_diff:
                    min_diff = diff
                    best_k = k
                if h_cost > setup:
                    break
            if build_trace: ltc_trace_logs.append(pd.DataFrame(t_log))
            ltc_rec[i] = sum(net_req[i:best_k + 1])
            i = best_k + 1
        else:
            i += 1
    ltc_poh, ltc_rel, ltc_actual = generate_poh_and_release(ltc_rec, moq_val)
    c_ltc_setup = sum(1 for x in ltc_actual if x > 0) * setup
    c_ltc_hold  = sum(max(0, x) for x in ltc_poh) * hold

    # --- 8. LEAST UNIT COST (LUC) ---
    luc_rec = [0] * n
    luc_trace_logs = []
    i = 0
    while i < n:
        if net_req[i] > 0:
            best_k = i
            min_uc = float('inf')
            t_log = []
            for k in range(i, n):
                qty = sum(net_req[i:k + 1])
                if qty == 0: continue
                h_cost = sum(net_req[m] * hold * (m - i) for m in range(i, k + 1))
                uc = (setup + h_cost) / qty
                if build_trace:
                    t_log.append({'Range': f"P{i+1}-P{k+1}", 'Qty': qty, 'Total Cost': setup + h_cost, 'Unit Cost': uc})
                if uc <= min_uc:
                    min_uc = uc
                    best_k = k
                else:
                    break
            if build_trace: luc_trace_logs.append(pd.DataFrame(t_log))
            luc_rec[i] = sum(net_req[i:best_k + 1])
            i = best_k + 1
        else:
            i += 1
    luc_poh, luc_rel, luc_actual = generate_poh_and_release(luc_rec, moq_val)
    c_luc_setup = sum(1 for x in luc_actual if x > 0) * setup
    c_luc_hold  = sum(max(0, x) for x in luc_poh) * hold

    # --- 9. PART PERIOD BALANCING (PPB) ---
    ppb_rec = [0] * n
    ppb_trace_logs = []
    epp = setup / hold if hold > 0 else 0
    i = 0
    while i < n:
        if net_req[i] > 0:
            best_k = i
            min_diff = float('inf')
            t_log = []
            for k in range(i, n):
                pp = sum(net_req[m] * (m - i) for m in range(i, k + 1))
                diff = abs(pp - epp)
                if build_trace:
                    t_log.append({'Range': f"P{i+1}-P{k+1}", 'Cum Part-Periods': pp, 'EPP': epp, 'Diff': diff})
                if diff < min_diff:
                    min_diff = diff
                    best_k = k
                if pp > epp:
                    break
            if build_trace: ppb_trace_logs.append(pd.DataFrame(t_log))
            ppb_rec[i] = sum(net_req[i:best_k + 1])
            i = best_k + 1
        else:
            i += 1
    ppb_poh, ppb_rel, ppb_actual = generate_poh_and_release(ppb_rec, moq_val)
    c_ppb_setup = sum(1 for x in ppb_actual if x > 0) * setup
    c_ppb_hold  = sum(max(0, x) for x in ppb_poh) * hold

    # --- 10. SILVER-MEAL (SM) ---
    sm_rec = [0] * n
    sm_trace_logs = []
    i = 0
    while i < n:
        if net_req[i] > 0:
            best_k = i
            min_ac = float('inf')
            t_log = []
            for k in range(i, n):
                h_cost = sum(net_req[m] * hold * (m - i) for m in range(i, k + 1))
                ac = (setup + h_cost) / (k - i + 1)
                if build_trace:
                    t_log.append({'Range': f"P{i+1}-P{k+1}", 'Total Cost': setup + h_cost, 'Avg Cost/Periode': ac})
                if ac <= min_ac:
                    min_ac = ac
                    best_k = k
                else:
                    break
            if build_trace: sm_trace_logs.append(pd.DataFrame(t_log))
            sm_rec[i] = sum(net_req[i:best_k + 1])
            i = best_k + 1
        else:
            i += 1
    sm_poh, sm_rel, sm_actual = generate_poh_and_release(sm_rec, moq_val)
    c_sm_setup = sum(1 for x in sm_actual if x > 0) * setup
    c_sm_hold  = sum(max(0, x) for x in sm_poh) * hold

    # --- 11. WAGNER-WHITIN (WW) ---
    ww_rec = [0] * n
    f = [0] * (n + 1)
    j_best = [0] * (n + 1)
    for t in range(1, n + 1):
        min_c = float('inf')
        best_j = 0
        for j in range(1, t + 1):
            h_cost = sum(net_req[m-1] * hold * (m - j) for m in range(j, t + 1))
            current_c = f[j-1] + setup + h_cost
            if current_c < min_c:
                min_c = current_c
                best_j = j
        f[t] = min_c
        j_best[t] = best_j
    t = n
    while t > 0:
        j = j_best[t]
        ww_rec[j-1] = sum(net_req[j-1:t])
        t = j - 1
    ww_poh, ww_rel, ww_actual = generate_poh_and_release(ww_rec, moq_val)
    c_ww_setup = sum(1 for x in ww_actual if x > 0) * setup
    c_ww_hold  = sum(max(0, x) for x in ww_poh) * hold

    return {
        'net_req': net_req, 'eoq_q': eoq_q, 'poq_t': poq_t,
        'l4l': {'poh': l4l_poh, 'rec': l4l_actual, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
        'eoq': {'poh': eoq_poh, 'rec': eoq_actual, 'rel': eoq_rel, 'setup': c_eoq_setup, 'hold': c_eoq_hold, 'total': c_eoq_setup + c_eoq_hold},
        'poq': {'poh': poq_poh, 'rec': poq_actual, 'rel': poq_rel, 'setup': c_poq_setup, 'hold': c_poq_hold, 'total': c_poq_setup + c_poq_hold},
        'foq': {'poh': foq_poh, 'rec': foq_actual, 'rel': foq_rel, 'setup': c_foq_setup, 'hold': c_foq_hold, 'total': c_foq_setup + c_foq_hold},
        'fpr': {'poh': fpr_poh, 'rec': fpr_actual, 'rel': fpr_rel, 'setup': c_fpr_setup, 'hold': c_fpr_hold, 'total': c_fpr_setup + c_fpr_hold},
        'iuc': {'poh': iuc_poh, 'rec': iuc_actual, 'rel': iuc_rel, 'setup': c_iuc_setup, 'hold': c_iuc_hold, 'total': c_iuc_setup + c_iuc_hold, 'logs': iuc_trace_logs},
        'ltc': {'poh': ltc_poh, 'rec': ltc_actual, 'rel': ltc_rel, 'setup': c_ltc_setup, 'hold': c_ltc_hold, 'total': c_ltc_setup + c_ltc_hold, 'logs': ltc_trace_logs},
        'luc': {'poh': luc_poh, 'rec': luc_actual, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'logs': luc_trace_logs},
        'ppb': {'poh': ppb_poh, 'rec': ppb_actual, 'rel': ppb_rel, 'setup': c_ppb_setup, 'hold': c_ppb_hold, 'total': c_ppb_setup + c_ppb_hold, 'logs': ppb_trace_logs},
        'sm':  {'poh': sm_poh,  'rec': sm_actual,  'rel': sm_rel,  'setup': c_sm_setup,  'hold': c_sm_hold,  'total': c_sm_setup + c_sm_hold,   'logs': sm_trace_logs},
        'ww':  {'poh': ww_poh,  'rec': ww_actual,  'rel': ww_rel,  'setup': c_ww_setup,  'hold': c_ww_hold,  'total': c_ww_setup + c_ww_hold}
    }


# Initialize Matrix Session state for FOQ Internal parameter inside the Tab
if 'foq_val' not in st.session_state:
    st.session_state.foq_val = 60

res = calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt, moq_val, st.session_state.foq_val)


# ==========================================
# 4. VIEW ENGINE UI RENDERERS (UNTOUCHED LOGIC)
# ==========================================
def render_mrp_grid_view(method_data):
    df_grid = pd.DataFrame({
        "Gross Requirements": demands,
        "Scheduled Receipts": s_receipts,
        "Projected On Hand": method_data['poh'],
        "Net Requirements": res['net_req'],
        "Planned Order Receipts": method_data['rec'],
        "Planned Order Releases": method_data['rel']
    }, index=period_labels).T
    
    def highlight_poh(row):
        styles = [''] * len(row)
        if row.name == 'Projected On Hand':
            for idx, val in enumerate(row):
                if val < ss:
                    styles[idx] = 'background-color: #ffd2d2; color: #b7094c; font-weight: bold;'
                elif val > max_capacity:
                    styles[idx] = 'background-color: #ffe6cc; color: #d66800; font-weight: bold;'
                else:
                    styles[idx] = 'background-color: #e2f0d9; color: #274e13;'
        return styles

    st.dataframe(df_grid.style.apply(highlight_poh, axis=1).format(precision=0), use_container_width=True)
    
    # Violation indicators
    low_stock = [period_labels[i] for i, v in enumerate(method_data['poh']) if v < ss]
    over_capacity = [period_labels[i] for i, v in enumerate(method_data['poh']) if v > max_capacity]
    if low_stock: st.error(f"🚨 Safety Stock Shortage Warning on periods: {', '.join(low_stock)}")
    if over_capacity: st.warning(f"⚠️ Capacity Limit Overrun on periods: {', '.join(over_capacity)}")

def render_cost_audit_window(method_data, label):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='card-metric'><b>Setup / Ordering Cost ({label})</b><h3>${method_data['setup']:,.2f}</h3></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='card-metric'><b>Holding Cost ({label})</b><h3>${method_data['hold']:,.2f}</h3></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='card-metric' style='border-left: 5px solid #2a9d8f;'><b>Total Balanced Cost</b><h3>${method_data['total']:,.2f}</h3></div>", unsafe_allow_html=True)


# ==========================================
# 5. TAB SYSTEM ASSEMBLY (URUTAN BARU REVISI)
# ==========================================
tabs_list = st.tabs([
    "📋 L4L", "🎯 EOQ", "⏱️ POQ", "🔒 FOQ", "📅 FPR", 
    "💰 IUC", "💸 LTC", "🔍 LUC", "⚖️ PPB", "🚀 Silver-Meal", "🔬 Wagner-Whitin"
])

# tabs_list[0] -> Lot-for-Lot
with tabs_list[0]:
    st.subheader("Lot-for-Lot (L4L) Performance Execution Plan")
    render_mrp_grid_view(res['l4l'])
    render_cost_audit_window(res['l4l'], "L4L")

# tabs_list[1] -> EOQ
with tabs_list[1]:
    st.subheader("Economic Order Quantity (EOQ) Classical Model")
    st.markdown(f"**Calculated Academic Reference Variable Quantity:** {res['eoq_q']} units")
    render_mrp_grid_view(res['eoq'])
    render_cost_audit_window(res['eoq'], "EOQ")

# tabs_list[2] -> POQ
with tabs_list[2]:
    st.subheader("Period Order Quantity (POQ) Derived Model")
    st.markdown(f"**Derived Time Interval:** Grouping order requirements every {res['poq_t']} periods")
    render_mrp_grid_view(res['poq'])
    render_cost_audit_window(res['poq'], "POQ")

# tabs_list[3] -> FOQ
with tabs_list[3]:
    st.subheader("Fixed Order Quantity (FOQ) Parameterized Plan")
    st.session_state.foq_val = st.number_input("Set Rigidity Fixed Lot Size Matrix Quantity:", min_value=1, value=st.session_state.foq_val, step=5)
    render_mrp_grid_view(res['foq'])
    render_cost_audit_window(res['foq'], "FOQ")

# tabs_list[4] -> FPR (BARU)
with tabs_list[4]:
    st.subheader("Fixed Period Requirements (FPR) Model")
    st.markdown(f"**Management Interval Preference Rule:** Covering demands every {fpr_interval} periods fixed.")
    render_mrp_grid_view(res['fpr'])
    render_cost_audit_window(res['fpr'], "FPR")

# tabs_list[5] -> IUC (BARU)
with tabs_list[5]:
    st.subheader("Incremental Unit Cost (IUC) Dynamic Heuristic")
    if build_trace and 'logs' in res['iuc']:
        for i, df in enumerate(res['iuc']['logs']):
            with st.expander(f"IUC Block Group Horizon Window Step Iteration {i+1}", expanded=False):
                st.dataframe(df, use_container_width=True, hide_index=True)
    render_mrp_grid_view(res['iuc'])
    render_cost_audit_window(res['iuc'], "IUC")

# tabs_list[6] -> LTC
with tabs_list[6]:
    st.subheader("Least Total Cost (LTC) Balance Model")
    if build_trace and 'logs' in res['ltc']:
        for i, df in enumerate(res['ltc']['logs']):
            with st.expander(f"LTC Balance Range Trace Matrix Block Iteration {i+1}", expanded=False):
                st.dataframe(df, use_container_width=True)
    render_mrp_grid_view(res['ltc'])
    render_cost_audit_window(res['ltc'], "LTC")

# tabs_list[7] -> LUC
with tabs_list[7]:
    st.subheader("Least Unit Cost (LUC) Iterative Model")
    if build_trace and 'logs' in res['luc']:
        for i, df in enumerate(res['luc']['logs']):
            with st.expander(f"LUC Mathematical Step Look-Ahead Block Iteration {i+1}", expanded=False):
                st.dataframe(df, use_container_width=True)
    render_mrp_grid_view(res['luc'])
    render_cost_audit_window(res['luc'], "LUC")

# tabs_list[8] -> PPB
with tabs_list[8]:
    st.subheader("Part Period Balancing (PPB) Model")
    st.markdown(f"**Economic Part Period Factor Limit Target:** {setup/hold if hold > 0 else 'INF'}")
    if build_trace and 'logs' in res['ppb']:
        for i, df in enumerate(res['ppb']['logs']):
            with st.expander(f"PPB Part Balancing Array Evaluation Step Iteration {i+1}", expanded=False):
                st.dataframe(df, use_container_width=True)
    render_mrp_grid_view(res['ppb'])
    render_cost_audit_window(res['ppb'], "PPB")

# tabs_list[9] -> Silver-Meal
with tabs_list[9]:
    st.subheader("Silver-Meal (SM) Criterion Optimization Strategy")
    if build_trace and 'logs' in res['sm']:
        for i, df in enumerate(res['sm']['logs']):
            with st.expander(f"Silver-Meal Averaging Logic Tree Evaluation Step Iteration {i+1}", expanded=False):
                st.dataframe(df, use_container_width=True)
    render_mrp_grid_view(res['sm'])
    render_cost_audit_window(res['sm'], "SM")

# tabs_list[10] -> Wagner-Whitin
with tabs_list[10]:
    st.subheader("Wagner-Whitin (WW) Exact Dynamic Programming Solution Strategy")
    st.success("🎯 Exact Optimum Achieved Route System.")
    render_mrp_grid_view(res['ww'])
    render_cost_audit_window(res['ww'], "WW")


# ==========================================
# 6. PORTFOLIO METRICS & SUMMARY COMPARISON
# ==========================================
st.markdown("---")
st.header("🏁 Strategic Portfolio Cost Summary Comparison Matrix")

biaya_dict = {
    'L4L': res['l4l']['total'], 'EOQ': res['eoq']['total'], 'POQ': res['poq']['total'],
    'FOQ': res['foq']['total'], 'FPR': res['fpr']['total'], 'IUC': res['iuc']['total'],
    'LTC': res['ltc']['total'], 'LUC': res['luc']['total'], 'PPB': res['ppb']['total'],
    'SM': res['sm']['total'], 'WW': res['ww']['total']
}

min_cost = min(biaya_dict.values())
best_methods = [k for k, v in biaya_dict.items() if v == min_cost]

# Info Note Keterbatasan MOQ di UI
if use_moq:
    st.markdown(f"""
        <div style="background-color: #fff4e6; border-left: 5px solid #ff922b; padding: 10px; border-radius: 4px; margin-bottom: 15px;">
            ⚠️ <b>Note Keterbatasan Akademis:</b> Universal Constraint <b>MOQ ({moq_val} unit)</b> aktif. 
            Hal ini dapat mendistorsi keandalan heuristik alami (seperti Silver-Meal atau Wagner-Whitin) karena sisa stok yang membengkak dipaksa maju ke periode berikutnya.
        </div>
    """, unsafe_allow_html=True)

cols_grid = st.columns(4)
for idx, (m_name, m_cost) in enumerate(biaya_dict.items()):
    with cols_grid[idx % 4]:
        is_opt = m_name in best_methods
        moq_badge = f" <span class='badge-moq'>MOQ Rules ({moq_val})</span>" if (use_moq and res[m_name.lower()]['rec'] != [0]*n) else ""
        border_color = "#2a9d8f" if is_opt else "#6a0708"
        bg_color = "#f1fbf9" if is_opt else "#f8f9fa"
        
        st.markdown(f"""
            <div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 12px; border-radius: 4px; margin-bottom: 10px;">
                <span style="font-weight: bold; color: #333;">{m_name}</span> {moq_badge}
                <h4 style="margin: 5px 0 0 0; color: {border_color};">${m_cost:,.2f}</h4>
                <span style="font-size: 0.8em; color: #777;">{"🏆 Optimal Choice" if is_opt else f"Delta: +${m_cost - min_cost:,.2f}"}</span>
            </div>
        """, unsafe_allow_html=True)


# ==========================================
# 7. SENSITIVITY SYSTEM & EXPORTER
# ==========================================
st.markdown("---")
st.subheader("📉 Parametric Performance Sensitivity Analysis Charts")

c_g1, c_g2 = st.columns(2)
with c_g1:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#444' if k not in best_methods else '#2a9d8f' for k in biaya_dict.keys()])
    ax.set_title("Total Cost Analysis Across Matrix Layout")
    ax.set_ylabel("Incurred Cost Total ($)")
    plt.xticks(rotation=45)
    st.pyplot(fig)

with c_g2:
    pct_changes = [-30, -20, -10, 0, 10, 20, 30]
    sens_data = {k: [] for k in biaya_dict.keys()}
    
    for p in pct_changes:
        scaled_demands = [max(0, int(round(d * (1 + p/100)))) for d in demands]
        s_res = calculate_multi_mrp(scaled_demands, s_receipts, setup, hold, init_inv, ss, lt, moq_val, st.session_state.foq_val)
        for k in biaya_dict.keys():
            sens_data[k].append(s_res[k.lower()]['total'])
            
    fig2, ax2 = plt.subplots(figsize=(6, 3.5))
    for k in biaya_dict.keys():
        ax2.plot([f"{p}%" for p in pct_changes], sens_data[k], label=k, marker='o', alpha=0.7)
    ax2.set_title("Demand Instability Stress-Test Matrix")
    ax2.set_ylabel("Total Cost ($)")
    ax2.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1, 1))
    st.pyplot(fig2)

# Excel Export Sequence
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    pd.DataFrame({'Gross Requirements': demands, 'Scheduled Receipts': s_receipts, 'Net Requirements': res['net_req']}, index=period_labels).T.to_excel(writer, sheet_name="Baseline Framework")
    for k in biaya_dict.keys():
        sk = k.lower()
        pd.DataFrame({
            'Projected On Hand': res[sk]['poh'],
            'Planned Order Receipts': res[sk]['rec'],
            'Planned Order Releases': res[sk]['rel']
        }, index=period_labels).T.to_excel(writer, sheet_name=f"{k} Strategy Plan")

excel_buffer.seek(0)
st.download_button(
    label="📥 Download Plan Document Report (11 Methods Synchronized).xlsx",
    data=excel_buffer,
    file_name="MRP_Lot_Sizing_Portfolio_Corporate_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)


# ==========================================
# 8. ACADEMIC GLOSSARY SECTION (BARU)
# ==========================================
st.markdown("---")
with st.expander("📚 Industrial Engineering Lot Sizing Methodology Glossary"):
    st.markdown("""
    * **📋 Lot-for-Lot (L4L):** Strategi pemenuhan instan yang memproduksi/memesan tepat sebesar jumlah kebutuhan bersih (*net requirement*) di setiap periode tanpa melakukan konsolidasi waktu. Meminimalkan ongkos simpan menjadi nol tetapi memicu ongkos pesan yang sangat tinggi.
    * **🎯 Economic Order Quantity (EOQ):** Pendekatan statistik klasik berbasis akar kuadrat rata-rata permintaan untuk mencari ukuran lot pesanan konstan statis yang menyeimbangkan total ongkos simpan dan ongkos pesan secara global.
    * **⏱️ Period Order Quantity (POQ):** Transformasi dari nilai matematika EOQ menjadi interval waktu peninjauan dinamis berbasis perputaran inventori rata-rata.
    * **🔒 Fixed Order Quantity (FOQ):** Kebijakan pengadaan kaku menggunakan aturan ukuran lot tetap (*rigid lot size*) yang ditentukan oleh kapasitas kontainer, batasan mesin, atau kontrak pemasok luar.
    * **📅 Fixed Period Requirements (FPR):** Kebijakan penjadwalan kaku berbasis waktu diskret di mana sistem secara konstan mengonsolidasikan dan memesan kebutuhan bersih untuk beberapa periode mendatang yang tetap (*fixed peniod coverage*), murni berdasarkan preferensi logistik manajemen tanpa kalkulasi EOQ.
    * **💰 Incremental Unit Cost (IUC):** Heuristik dinamis yang menganalisis penambahan (*marginal*) biaya simpan unit dari periode ke periode berikutnya secara parsial. Keputusan pemotongan lot baru (*cutoff*) dieksekusi seketika ketika laju kenaikan ongkos simpan marginal dari unit tambahan melebihi batas nilai *setup cost*.
    * **💸 Least Total Cost (LTC):** Metode heuristik dinamis penyeimbang biaya (*cost-balancing technique*) yang terus mengonsolidasikan kebutuhan periode ke depan hingga titik di mana akumulasi ongkos simpan bernilai paling mendekati ongkos pesan (*setup cost*).
    * **🔍 Least Unit Cost (LUC):** Heuristik dinamis berorientasi efisiensi per unit produksi, yang mencari ukuran lot dengan membagi total biaya (setup + holding) terhadap volume pesanan terkonsolidasi guna mencapai ongkos per unit terkecil.
    * **⚖️ Part Period Balancing (PPB):** Modifikasi dari prinsip LTC yang mengonversi rasio ekonomi biaya menjadi parameter batas mutlak *Economic Part Period* (EPP) untuk menyelaraskan akumulasi perkalian unit-periode.
    * **🚀 Silver-Meal (SM):** Salah satu heuristik dinamis paling terkenal di dunia *Inventory Control* yang berfokus meminimalkan rata-rata biaya total per periode operasi sepanjang horison waktu cakupan lot.
    * **🔬 Wagner-Whitin (WW):** Algoritma optimasi eksak berbasis pemrograman dinamis (*Dynamic Programming*) yang menjamin penemuan jalur keputusan pemesanan dengan total kombinasi biaya operasi paling minimum secara global.
    """)
