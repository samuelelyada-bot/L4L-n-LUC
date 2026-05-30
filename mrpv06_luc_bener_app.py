import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import math

# Set Page Config
st.set_page_config(page_title="MRP Multi-Method Lot Sizing Workbench", layout="wide")

# ==========================================
# 1. SIDEBAR CONFIGURATION & GLOBAL CONTROLS
# ==========================================
st.sidebar.header("🛠️ Global Control Parameters")

# File Upload / Input Vectors Source
data_source = st.sidebar.radio("Data Input Vector Source:", ["Manual Input Matrix", "Excel Upload Matrix"])

if data_source == "Manual Input Matrix":
    st.sidebar.subheader("Vector Inputs")
    gross_req_raw = st.sidebar.text_input("Gross Requirements Vector (Comma separated):", "35, 10, 40, 20, 15, 30, 25, 55, 40, 45, 20, 35")
    sched_rec_raw = st.sidebar.text_input("Scheduled Receipts Vector (Comma separated):", "0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0")
    period_labels_raw = st.sidebar.text_input("Period Identifier Labels (Comma separated):", "P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12")
    
    gross_req = [int(x.strip()) for x in gross_req_raw.split(",")]
    sched_rec = [int(x.strip()) for x in sched_rec_raw.split(",")]
    period_labels = [x.strip().upper() for x in period_labels_raw.split(",")]
else:
    uploaded_file = st.sidebar.file_uploader("Upload MRP Baseline Framework Excel:", type=["xlsx"])
    if uploaded_file is not None:
        df_upload = pd.read_excel(uploaded_file, sheet_name=0)
        gross_req = df_upload.iloc[0].tolist()
        sched_rec = df_upload.iloc[1].tolist()
        period_labels = df_upload.columns.astype(str).str.upper().tolist()
    else:
        st.sidebar.info("Awaiting file upload matrix. Using baseline fallback vector configuration.")
        gross_req = [35, 10, 40, 20, 15, 30, 25, 55, 40, 45, 20, 35]
        sched_rec = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        period_labels = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12"]

# Cost Variables
st.sidebar.subheader("Financial Controls")
setup_cost = st.sidebar.number_input("Unit Setup Cost ($S$ per order):", min_value=0.0, value=200.0, step=10.0)
holding_cost = st.sidebar.number_input("Unit Holding Cost ($H$ per unit/period):", min_value=0.0, value=2.0, step=0.5)

# Inventory & Boundary Constraints
st.sidebar.subheader("Inventory Boundary Constraints")
initial_inv = st.sidebar.number_input("Initial On-Hand Inventory Inventory ($I_0$):", min_value=0, value=20)
safety_stock = st.sidebar.number_input("Safety Stock Threshold Limit ($SS$):", min_value=0, value=5)
lead_time = st.sidebar.number_input("Operational Lead Time ($LT$):", min_value=0, value=1)
max_capacity = st.sidebar.number_input("Maximum Warehouse Capacity ($C_{max}$):", min_value=0, value=500)

# Method Specific Parameters
st.sidebar.subheader("Method Specific Parameters")
fixed_lot_size = st.sidebar.number_input("FOQ Rigidity Size Matrix ($Q_{foq}$):", min_value=1, value=60)
fpr_interval = st.sidebar.number_input("FPR Policy Coverage Interval ($T_{fpr}$):", min_value=1, value=3, step=1)

# GLOBAL CONSTRAINT TOGGLE: MOQ
st.sidebar.subheader("🧱 Global Constraint Safety Filters")
enforce_moq = st.sidebar.checkbox("Enforce MOQ Constraint Filter", value=False)
min_order_qty = 0
if enforce_moq:
    min_order_qty = st.sidebar.number_input("Minimum Order Quantity Threshold ($MOQ$):", min_value=1, value=50)

# Global Application CSS Interface Stylings
st.markdown("""
    <style>
    .text-justify { text-align: justify; }
    .math-justify { text-align: center; margin: 15px 0; }
    h1, h2, h3 { color: #6a0708; }
    </style>
""", unsafe_allow_html=True)

st.title("🔬 Advanced Industrial Engineering Operations Workbench")
st.subheader("Multi-Method Material Requirements Planning (MRP) Simulation Engine with Global Constraint Wrapper")

# Validation check
if len(gross_req) != len(sched_rec) or len(gross_req) != len(period_labels):
    st.error("❌ Dimensions Error: Vector arrays parameters mismatched.")
    st.stop()


# ==========================================
# 2. GLOBAL SIMULATION CORE ENGINE (BACKEND)
# ==========================================
def calculate_multi_mrp(gross, sched, setup, hold, init_inv, ss, lt, f_lot, fpr_int, moq_val, enforce_moq_flag):
    n = len(gross)
    
    # 0. Core Step: Calculate Net Requirements Vector considering Domino Effects of Stock injection
    net_req = [0] * n
    poh_calc = [0] * n
    current_inv = init_inv
    
    for j in range(n):
        available = current_inv + sched[j]
        if available < gross[j] + ss:
            net_req[j] = (gross[j] + ss) - available
            poh_calc[j] = ss
        else:
            net_req[j] = 0
            poh_calc[j] = available - gross[j]
        current_inv = poh_calc[j]

    total_demand_gross = sum(gross)
    avg_demand_gross = total_demand_gross / n

    # Helper wrapper layout to safely enforce MOQ constraints and dynamically propagate backlogs
    def apply_moq_and_generate_poh_release(rec_vector):
        final_rec = [0] * n
        final_poh = [0] * n
        curr_inv = init_inv
        
        for idx in range(n):
            needed = gross[idx] + ss - (curr_inv + sched[idx])
            raw_rec = rec_vector[idx]
            
            if needed > 0 and raw_rec == 0:
                raw_rec = needed # Safety catch for sequential execution integrity
                
            if raw_rec > 0:
                if enforce_moq_flag and raw_rec < moq_val:
                    raw_rec = moq_val
            
            final_rec[idx] = raw_rec
            available = curr_inv + sched[idx] + final_rec[idx]
            final_poh[idx] = available - gross[idx]
            curr_inv = final_poh[idx]
            
        final_rel = [0] * n
        for idx in range(n):
            if idx + lt < n:
                final_rel[idx] = final_rec[idx + lt]
            else:
                final_rel[idx] = 0 # Out of boundary horizon cutoff safety truncation
                
        return final_poh, final_rec, final_rel

    # ------------------------------------------
    # METODE 1: LOT-FOR-LOT (L4L)
    # ------------------------------------------
    l4l_rec_raw = [r for r in net_req]
    l4l_poh, l4l_rec, l4l_rel = apply_moq_and_generate_poh_release(l4l_rec_raw)

    # ------------------------------------------
    # METODE 2: FIXED ORDER QUANTITY (FOQ)
    # ------------------------------------------
    foq_rec_raw = [0] * n
    curr_inv_foq = init_inv
    for j in range(n):
        needed = gross[j] + ss - (curr_inv_foq + sched[j])
        if needed > 0:
            lots = math.ceil(needed / f_lot)
            foq_rec_raw[j] = lots * f_lot
            available = curr_inv_foq + sched[j] + foq_rec_raw[j]
        else:
            foq_rec_raw[j] = 0
            available = curr_inv_foq + sched[j]
        curr_inv_foq = available - gross[j]
    foq_poh, foq_rec, foq_rel = apply_moq_and_generate_poh_release(foq_rec_raw)

    # ------------------------------------------
    # METODE 3: FIXED PERIOD REQUIREMENTS (FPR)
    # ------------------------------------------
    fpr_rec_raw = [0] * n
    curr_inv_fpr = init_inv
    j = 0
    while j < n:
        needed = gross[j] + ss - (curr_inv_fpr + sched[j])
        if needed > 0:
            end_window = min(j + fpr_int, n)
            run_inv = curr_inv_fpr
            total_window_net = 0
            for k in range(j, end_window):
                k_needed = gross[k] + ss - (run_inv + sched[k])
                if k_needed > 0:
                    total_window_net += k_needed
                    run_inv = ss
                else:
                    run_inv = run_inv + sched[k] - gross[k]
            fpr_rec_raw[j] = total_window_net
            curr_inv_fpr = curr_inv_fpr + sched[j] + fpr_rec_raw[j] - gross[j]
            j += 1
            for k in range(j, end_window):
                fpr_rec_raw[k] = 0
                curr_inv_fpr = curr_inv_fpr + sched[k] - gross[k]
            j = end_window
        else:
            fpr_rec_raw[j] = 0
            curr_inv_fpr = curr_inv_fpr + sched[j] - gross[j]
            j += 1
    fpr_poh, fpr_rec, fpr_rel = apply_moq_and_generate_poh_release(fpr_rec_raw)

    # ------------------------------------------
    # METODE 4: ECONOMIC ORDER QUANTITY (EOQ)
    # ------------------------------------------
    eoq_size = 0
    eoq_raw_size = 0
    eoq_rec_raw = [0] * n
    if holding_cost > 0:
        eoq_raw_size = math.sqrt((2 * avg_demand_gross * setup) / holding_cost)
        eoq_size = math.ceil(eoq_raw_size)
        curr_inv_eoq = init_inv
        for j in range(n):
            needed = gross[j] + ss - (curr_inv_eoq + sched[j])
            if needed > 0:
                lots = math.ceil(needed / eoq_size)
                eoq_rec_raw[j] = lots * eoq_size
                available = curr_inv_eoq + sched[j] + eoq_rec_raw[j]
            else:
                eoq_rec_raw[j] = 0
                available = curr_inv_eoq + sched[j]
            curr_inv_eoq = available - gross[j]
    eoq_poh, eoq_rec, eoq_rel = apply_moq_and_generate_poh_release(eoq_rec_raw)

    # ------------------------------------------
    # METODE 5: PERIOD ORDER QUANTITY (POQ)
    # ------------------------------------------
    poq_interval = 1
    poq_raw_interval = 0
    poq_rec_raw = [0] * n
    if holding_cost > 0 and eoq_size > 0:
        poq_raw_interval = eoq_size / avg_demand_gross
        poq_interval = max(1, round(poq_raw_interval))
        curr_inv_poq = init_inv
        j = 0
        while j < n:
            needed = gross[j] + ss - (curr_inv_poq + sched[j])
            if needed > 0:
                end_window = min(j + poq_interval, n)
                run_inv = curr_inv_poq
                total_window_net = 0
                for k in range(j, end_window):
                    k_needed = gross[k] + ss - (run_inv + sched[k])
                    if k_needed > 0:
                        total_window_net += k_needed
                        run_inv = ss
                    else:
                        run_inv = run_inv + sched[k] - gross[k]
                poq_rec_raw[j] = total_window_net
                curr_inv_poq = curr_inv_poq + sched[j] + poq_rec_raw[j] - gross[j]
                j += 1
                for k in range(j, end_window):
                    poq_rec_raw[k] = 0
                    curr_inv_poq = curr_inv_poq + sched[k] - gross[k]
                j = end_window
            else:
                poq_rec_raw[j] = 0
                curr_inv_poq = curr_inv_poq + sched[j] - gross[j]
                j += 1
    poq_poh, poq_rec, poq_rel = apply_moq_and_generate_poh_release(poq_rec_raw)

    # Dynamic Re-evaluator function for Trace Trace Engine Logs
    def evaluate_dynamic_heuristic_model(mode="LUC"):
        rec_raw = [0] * n
        curr_inv_sim = init_inv
        trace_logs = []
        
        j = 0
        while j < n:
            needed = gross[j] + ss - (curr_inv_sim + sched[j])
            if needed <= 0:
                rec_raw[j] = 0
                curr_inv_sim = curr_inv_sim + sched[j] - gross[j]
                j += 1
                continue
                
            window_rows = []
            best_k_end = j
            min_criterion = float('inf') if mode in ["LUC", "SM", "IUC"] else None
            max_holding_ltc = 0
            
            # Temporary lookahead trackers
            accum_demand = 0
            accum_holding = 0
            run_inv = curr_inv_sim
            
            for k in range(j, n):
                k_needed = gross[k] + ss - (run_inv + sched[k])
                current_k_net = max(0, k_needed)
                accum_demand += current_k_net
                
                # holding duration calculation matrix offset
                accum_holding += current_k_net * hold * (k - j)
                total_cost_block = setup + accum_holding
                
                num_periods_covered = (k - j + 1)
                unit_cost = total_cost_block / accum_demand if accum_demand > 0 else float('inf')
                avg_period_cost = total_cost_block / num_periods_covered
                marginal_holding = current_k_net * hold * (k - j)
                
                if mode == "LUC":
                    criterion_val = unit_cost
                    is_violated = (criterion_val > min_criterion) if min_criterion is not float('inf') else False
                elif mode == "SM":
                    criterion_val = avg_period_cost
                    is_violated = (criterion_val > min_criterion) if min_criterion is not float('inf') else False
                elif mode == "IUC":
                    criterion_val = unit_cost
                    is_violated = (marginal_holding > setup)
                elif mode == "LTC":
                    criterion_val = accum_holding
                    is_violated = (accum_holding > setup)
                elif mode == "PPB":
                    criterion_val = accum_holding / hold if hold > 0 else 0
                    epp_target = setup / hold if hold > 0 else float('inf')
                    is_violated = (criterion_val > epp_target)

                window_rows.append({
                    'Period Focus': period_labels[k],
                    'Cumulative Net Demand': accum_demand,
                    'Accumulated Holding': accum_holding,
                    'Marginal Holding': marginal_holding,
                    'Total Cost Block': total_cost_block,
                    'Criterion Value': criterion_val,
                    'Action Status': 'Violated / Cutoff ❌' if is_violated else 'Feasible Block Range Step'
                })
                
                if mode in ["LUC", "SM"]:
                    if not is_violated:
                        min_criterion = criterion_val
                        best_k_end = k
                    else:
                        break
                elif mode in ["IUC", "LTC", "PPB"]:
                    if not is_violated:
                        best_k_end = k
                    else:
                        # For LTC and PPB evaluate closeness boundary constraint matrix match
                        if mode == "LTC" and abs(accum_holding - setup) < abs(max_holding_ltc - setup):
                            best_k_end = k
                        break
                
                if k_needed > 0:
                    run_inv = ss
                else:
                    run_inv = run_inv + sched[k] - gross[k]
                    
            trace_logs.append(pd.DataFrame(window_rows))
            
            # Execute physical block commit allocation mapping
            run_inv_commit = curr_inv_sim
            total_block_order_size = 0
            for k in range(j, best_k_end + 1):
                k_needed = gross[k] + ss - (run_inv_commit + sched[k])
                if k_needed > 0:
                    total_block_order_size += k_needed
                    run_inv_commit = ss
                else:
                    run_inv_commit = run_inv_commit + sched[k] - gross[k]
                    
            rec_raw[j] = total_block_order_size
            curr_inv_sim = curr_inv_sim + sched[j] + rec_raw[j] - gross[j]
            j += 1
            for k in range(j, best_k_end + 1):
                rec_raw[k] = 0
                curr_inv_sim = curr_inv_sim + sched[k] - gross[k]
            j = best_k_end + 1
            
        poh, rec, rel = apply_moq_and_generate_poh_release(rec_raw)
        return poh, rec, rel, trace_logs

    # Execute dynamic engines loop sequence
    luc_poh, luc_rec, luc_rel, luc_trace = evaluate_dynamic_heuristic_model("LUC")
    iuc_poh, iuc_rec, iuc_rel, iuc_trace = evaluate_dynamic_heuristic_model("IUC")
    ltc_poh, ltc_rec, ltc_rel, ltc_trace = evaluate_dynamic_heuristic_model("LTC")
    ppb_poh, ppb_rec, ppb_rel, ppb_trace = evaluate_dynamic_heuristic_model("PPB")
    sm_poh, sm_rec, sm_rel, sm_trace = evaluate_dynamic_heuristic_model("SM")

    # ------------------------------------------
    # METODE 11: WAGNER-WHITIN (WW) EXACT DYNAMIC PROGRAMMING ENGINE
    # ------------------------------------------
    INF = float('inf')
    f = [INF] * (n + 1)
    order_at = [0] * (n + 1)
    f[0] = 0
    
    for j_idx in range(1, n + 1):
        if net_req[j_idx-1] == 0 and f[j_idx-1] != INF:
            f[j_idx] = f[j_idx-1]
            order_at[j_idx] = order_at[j_idx-1]
            # Do not continue, check alternate paths that could inject inventory earlier
        for i_idx in range(1, j_idx + 1):
            holding = sum(net_req[k-1] * hold * (k - i_idx) for k in range(i_idx, j_idx + 1))
            cost = f[i_idx-1] + setup + holding
            if cost < f[j_idx]:
                f[j_idx] = cost
                order_at[j_idx] = i_idx
                
    ww_rec_raw = [0] * n
    j_ptr = n
    ww_windows = []
    while j_ptr > 0:
        if net_req[j_ptr-1] == 0 and order_at[j_ptr] == order_at[j_ptr-1] and j_ptr > 1:
            j_ptr -= 1
            continue
        i_ptr = order_at[j_ptr]
        if i_ptr == 0:
            j_ptr -= 1
            continue
        ww_rec_raw[i_ptr-1] = sum(net_req[i_ptr-1:j_ptr])
        ww_windows.insert(0, (i_ptr, j_ptr))
        j_ptr = i_ptr - 1
        
    ww_poh, ww_rec, ww_rel = apply_moq_and_generate_poh_release(ww_rec_raw)
    
    ww_trace_logs = []
    for (w_start, w_end) in ww_windows:
        window_rows = []
        for j_val in range(w_start, w_end + 1):
            for i_val in range(w_start, j_val + 1):
                holding = sum(net_req[k-1] * hold * (k - i_val) for k in range(i_val, j_val + 1))
                cost = f[i_val-1] + setup + holding
                is_optimal = (order_at[j_val] == i_val)
                window_rows.append({
                    'Order Period Window': period_labels[i_val-1],
                    'Covers Until Period': period_labels[j_val-1],
                    'Cumulative Holding': holding,
                    'Evaluated Functional Cost': cost,
                    'Status': 'Optimal Selection ✅' if is_optimal else 'Feasible Alternate Matrix Route'
                })
        if window_rows:
            ww_trace_logs.append(pd.DataFrame(window_rows))

    # Helper function to compute real accrued cost matrices post-enforcement parameters
    def compute_true_cost(rec_vec, poh_vec):
        setups = sum(1 for x in rec_vec if x > 0) * setup
        holds = sum(max(0, x) for x in poh_vec) * hold
        return setups, holds, setups + holds

    c_l4l_s, c_l4l_h, c_l4l_t = compute_true_cost(l4l_rec, l4l_poh)
    c_foq_s, c_foq_h, c_foq_t = compute_true_cost(foq_rec, foq_poh)
    c_fpr_s, c_fpr_h, c_fpr_t = compute_true_cost(fpr_rec, fpr_poh)
    c_eoq_s, c_eoq_h, c_eoq_t = compute_true_cost(eoq_rec, eoq_poh)
    c_poq_s, c_poq_h, c_poq_t = compute_true_cost(poq_rec, poq_poh)
    c_iuc_s, c_iuc_h, c_iuc_t = compute_true_cost(iuc_rec, iuc_poh)
    c_luc_s, c_luc_h, c_luc_t = compute_true_cost(luc_rec, luc_poh)
    c_ltc_s, c_ltc_h, c_ltc_t = compute_true_cost(ltc_rec, ltc_poh)
    c_ppb_s, c_ppb_h, c_ppb_t = compute_true_cost(ppb_rec, ppb_poh)
    c_sm_s, c_sm_h, c_sm_t = compute_true_cost(sm_rec, sm_poh)
    c_ww_s, c_ww_h, c_ww_t = compute_true_cost(ww_rec, ww_poh)

    return {
        'net_req': net_req, 'total_demand_gross': total_demand_gross, 'avg_demand_gross': avg_demand_gross,
        'eoq_size': eoq_size, 'eoq_raw_size': eoq_raw_size, 'poq_interval': poq_interval, 'poq_raw_interval': poq_raw_interval,
        'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_s, 'hold': c_l4l_h, 'total': c_l4l_t},
        'foq': {'poh': foq_poh, 'rec': foq_rec, 'rel': foq_rel, 'setup': c_foq_s, 'hold': c_foq_h, 'total': c_foq_t},
        'fpr': {'poh': fpr_poh, 'rec': fpr_rec, 'rel': fpr_rel, 'setup': c_fpr_s, 'hold': c_fpr_h, 'total': c_fpr_t},
        'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': c_eoq_s, 'hold': c_eoq_h, 'total': c_eoq_t},
        'poq': {'poh': poq_poh, 'rec': poq_rec, 'rel': poq_rel, 'setup': c_poq_s, 'hold': c_poq_h, 'total': c_poq_t},
        'iuc': {'poh': iuc_poh, 'rec': iuc_rec, 'rel': iuc_rel, 'setup': c_iuc_s, 'hold': c_iuc_h, 'total': c_iuc_t, 'iters': iuc_trace},
        'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_s, 'hold': c_luc_h, 'total': c_luc_t, 'iters': luc_trace},
        'ltc': {'poh': ltc_poh, 'rec': ltc_rec, 'rel': ltc_rel, 'setup': c_ltc_s, 'hold': c_ltc_h, 'total': c_ltc_t, 'iters': ltc_trace},
        'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': c_ppb_s, 'hold': c_ppb_h, 'total': c_ppb_t, 'iters': ppb_trace},
        'sm': {'poh': sm_poh, 'rec': sm_rec, 'rel': sm_rel, 'setup': c_sm_s, 'hold': c_sm_h, 'total': c_sm_t, 'iters': sm_trace},
        'ww': {'poh': ww_poh, 'rec': ww_rec, 'rel': ww_rel, 'setup': c_ww_s, 'hold': c_ww_h, 'total': c_ww_t, 'iters': ww_trace_logs}
    }

# Execute Core Calculations
res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time, fixed_lot_size, fpr_interval, min_order_qty, enforce_moq)
num_periods = len(gross_req)

# ==========================================
# 3. GLOBAL FRONTEND PRESENTATION (VIEW UI)
# ==========================================
def style_mrp_grid(df, max_cap, ss):
    def highlight_cells(x):
        df_style = pd.DataFrame('', index=x.index, columns=x.columns)
        if 'Projected On Hand' in x.index:
            poh_row = x.loc['Projected On Hand']
            for col in x.columns:
                val = poh_row[col]
                if val < ss:
                    df_style.loc['Projected On Hand', col] = 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
                elif val > max_cap:
                    df_style.loc['Projected On Hand', col] = 'background-color: #ffe6cc; color: #cc6600; font-weight: bold;'
                else:
                    df_style.loc['Projected On Hand', col] = 'background-color: #e2f0d9; color: #385723;'
        return df_style
    return df.style.apply(highlight_cells, axis=None).format(precision=0)

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
    
    # Error Guard Evaluators
    low_stock_periods = [period_labels[i] for i, v in enumerate(data_dict['poh']) if v < ss]
    cap_over_periods = [period_labels[i] for i, v in enumerate(data_dict['poh']) if v > max_cap]
    
    if low_stock_periods:
        st.error(f"🚨 Safety Stock Shortage Warning in periods: {', '.join(low_stock_periods)}")
    if cap_over_periods:
        st.warning(f"⚠️ Capacity Boundary Overrun in periods: {', '.join(cap_over_periods)}")

def render_cost_audit_window(data_dict, setup_val, hold_val, rec_array, poh_array):
    order_count = sum(1 for x in rec_array if x > 0)
    sum_poh = sum(max(0, x) for x in poh_array)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("🛠️ Setup Cost Detail"):
            st.markdown(f"""<div class='text-justify'><b>Formula:</b> Orders Count &times; Unit Setup Cost<br><b>Calculation:</b> {order_count} &times; {setup_val:,.2f}<br><b>Total:</b> ${data_dict['setup']:,.2f}</div>""", unsafe_allow_html=True)
    with c2:
        with st.expander("📦 Holding Cost Detail"):
            st.markdown(f"""<div class='text-justify'><b>Formula:</b> (&sum; Projected On Hand) &times; Holding Rate<br><b>Calculation:</b> {sum_poh} &times; {hold_val:,.2f}<br><b>Total:</b> ${data_dict['hold']:,.2f}</div>""", unsafe_allow_html=True)
    with c3:
        with st.expander("💰 Total Operational Cost"):
            st.markdown(f"""<div class='text-justify'><b>Formula:</b> Setup Cost + Holding Cost<br><b>Calculation:</b> {data_dict['setup']:,.2f} + {data_dict['hold']:,.2f}<br><b>Total:</b> <b>${data_dict['total']:,.2f}</b></div>""", unsafe_allow_html=True)

# Define Tab Interface Components matching Academic Hierarchy Order
method_tabs = st.tabs([
    "📋 Lot-for-Lot (L4L)", "🔒 Fixed Order Qty (FOQ)", "📅 Fixed Period Req (FPR)",
    "🎯 Economic Order Qty (EOQ)", "⏱️ Period Order Qty (POQ)", "💰 Incremental Unit Cost (IUC)",
    "🔍 Least Unit Cost (LUC)", "💸 Least Total Cost (LTC)", "⚖️ Part Period Balancing (PPB)",
    "🚀 Silver-Meal (SM)", "🔬 Wagner-Whitin (WW)"
])

def style_iteration_rows(df_item):
    styles = pd.DataFrame('', index=df_item.index, columns=df_item.columns)
    for idx, row in df_item.iterrows():
        if 'Violated' in str(row.get('Action Status', '')) or 'Cutoff' in str(row.get('Action Status', '')):
            styles.loc[idx] = 'background-color: #ffe6e6;'
        elif 'Optimal' in str(row.get('Status', '')):
            styles.loc[idx] = 'background-color: #e2f0d9;'
    return styles

# TAB 1: L4L
with method_tabs[0]:
    st.subheader("Lot-for-Lot (L4L) Performance Execution Model")
    render_mrp_grid_view(res['l4l'], max_capacity, safety_stock)
    render_cost_audit_window(res['l4l'], setup_cost, holding_cost, res['l4l']['rec'], res['l4l']['poh'])

# TAB 2: FOQ
with method_tabs[1]:
    st.subheader("Fixed Order Quantity (FOQ) Sizing Profile")
    st.info(f"🔒 FOQ Constraint Value Rule set at multiples of {fixed_lot_size} units.")
    render_mrp_grid_view(res['foq'], max_capacity, safety_stock)
    render_cost_audit_window(res['foq'], setup_cost, holding_cost, res['foq']['rec'], res['foq']['poh'])

# TAB 3: FPR
with method_tabs[2]:
    st.subheader("Fixed Period Requirements (FPR) Model")
    st.info(f"📅 FPR Management Policy Interval Rule set at: {fpr_interval} periods.")
    render_mrp_grid_view(res['fpr'], max_capacity, safety_stock)
    render_cost_audit_window(res['fpr'], setup_cost, holding_cost, res['fpr']['rec'], res['fpr']['poh'])

# TAB 4: EOQ
with method_tabs[3]:
    st.subheader("Economic Order Quantity (EOQ) Optimization Model")
    if holding_cost == 0:
        st.error("❌ Mathematical Division by Zero Error: Holding Cost cannot be 0 for classic EOQ calculation.")
    else:
        with st.expander("🔬 View Formula Log Calculations (EOQ)", expanded=False):
            st.markdown(f"""
            $$\\text{{Average Demand (D)}} = \\frac{{\\sum \\text{{Gross Requirements}}}}{{n}} = \\frac{{{res['total_demand_gross']}}}{{{num_periods}}} = {res['avg_demand_gross']:.4f}$$
            $$EOQ = \\sqrt{{\\frac{{2 \\times D \\times S}}{{H}}}} = \\sqrt{{\\frac{{2 \\times {res['avg_demand_gross']:.4f} \\times {setup_cost}}}{{{holding_cost}}}}} = {res['eoq_raw_size']:.4f} \\rightarrow \\text{{Ceiling}} = {res['eoq_size']}$$
            """, unsafe_allow_html=True)
        render_mrp_grid_view(res['eoq'], max_capacity, safety_stock)
        render_cost_audit_window(res['eoq'], setup_cost, holding_cost, res['eoq']['rec'], res['eoq']['poh'])

# TAB 5: POQ
with method_tabs[4]:
    st.subheader("Period Order Quantity (POQ) Time-Phased Model")
    if holding_cost == 0:
        st.error("❌ EOQ reference limit profile invalid due to zero value holding metrics.")
    else:
        with st.expander("🔬 View Formula Log Calculations (POQ)", expanded=False):
            st.markdown(f"""
            $$P_{{oq}} = \\frac{{\\text{{EOQ Size}}}}{{D}} = \\frac{{{res['eoq_size']}}}{{{res['avg_demand_gross']:.4f}}} = {res['poq_raw_interval']:.4f} \\rightarrow \\text{{Rounded}} = {res['poq_interval']}\\text{{ periods}}$$
            """, unsafe_allow_html=True)
        render_mrp_grid_view(res['poq'], max_capacity, safety_stock)
        render_cost_audit_window(res['poq'], setup_cost, holding_cost, res['poq']['rec'], res['poq']['poh'])

# TAB 6: IUC
with method_tabs[5]:
    st.subheader("Incremental Unit Cost (IUC) Dynamic Heuristic")
    for block_idx, df_step in enumerate(res['iuc']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"IUC Calculation Iteration Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['iuc'], max_capacity, safety_stock)
    render_cost_audit_window(res['iuc'], setup_cost, holding_cost, res['iuc']['rec'], res['iuc']['poh'])

# TAB 7: LUC
with method_tabs[6]:
    st.subheader("Least Unit Cost (LUC) Dynamic Sizing Model")
    for block_idx, df_step in enumerate(res['luc']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"LUC Calculation Iteration Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['luc'], max_capacity, safety_stock)
    render_cost_audit_window(res['luc'], setup_cost, holding_cost, res['luc']['rec'], res['luc']['poh'])

# TAB 8: LTC
with method_tabs[7]:
    st.subheader("Least Total Cost (LTC) Balanced Part Model")
    for block_idx, df_step in enumerate(res['ltc']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"LTC Calculation Iteration Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['ltc'], max_capacity, safety_stock)
    render_cost_audit_window(res['ltc'], setup_cost, holding_cost, res['ltc']['rec'], res['ltc']['poh'])

# TAB 9: PPB
with method_tabs[8]:
    st.subheader("Part Period Balancing (PPB) Target Economic Policy Model")
    epp_val_fmt = f"{setup_cost / holding_cost:.4f}" if holding_cost > 0 else "INF"
    st.info(f"🎯 Target Economic Part Period (EPP) Factor Limit Baseline: {epp_val_fmt}")
    for block_idx, df_step in enumerate(res['ppb']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"PPB Calculation Iteration Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['ppb'], max_capacity, safety_stock)
    render_cost_audit_window(res['ppb'], setup_cost, holding_cost, res['ppb']['rec'], res['ppb']['poh'])

# TAB 10: SM
with method_tabs[9]:
    st.subheader("Silver-Meal (SM) Criterion Period Average Dynamic Heuristic")
    for block_idx, df_step in enumerate(res['sm']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"Silver-Meal Calculation Iteration Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['sm'], max_capacity, safety_stock)
    render_cost_audit_window(res['sm'], setup_cost, holding_cost, res['sm']['rec'], res['sm']['poh'])

# TAB 11: WW
with method_tabs[10]:
    st.subheader("Wagner-Whitin (WW) Exact Dynamic Programming Matrix Engine")
    st.success("🎯 Global Optimal Solution Vector: Exact optimization path tracking active.")
    for block_idx, df_step in enumerate(res['ww']['iters']):
        if df_step is not None and not df_step.empty:
            with st.expander(f"Wagner-Whitin Dynamic Routing Sequence Segment Block {block_idx + 1}"):
                st.dataframe(df_step.style.apply(style_iteration_rows, axis=None), hide_index=True, use_container_width=True)
    render_mrp_grid_view(res['ww'], max_capacity, safety_stock)
    render_cost_audit_window(res['ww'], setup_cost, holding_cost, res['ww']['rec'], res['ww']['poh'])


# ==========================================
# 4. PORTFOLIO STRATEGIC COST COMPARISON
# ==========================================
st.markdown("---")
st.header("🏁 Strategic Portfolio Cost Summary Comparison Matrix")

biaya_dict = {
    'L4L': res['l4l']['total'], 'FOQ': res['foq']['total'], 'FPR': res['fpr']['total'],
    'EOQ': res['eoq']['total'] if holding_cost > 0 else float('inf'),
    'POQ': res['poq']['total'] if holding_cost > 0 else float('inf'),
    'IUC': res['iuc']['total'], 'LUC': res['luc']['total'], 'LTC': res['ltc']['total'],
    'PPB': res['ppb']['total'], 'SM': res['sm']['total'], 'WW': res['ww']['total']
}

valid_costs = {k: v for k, v in biaya_dict.items() if v != float('inf')}
min_cost = min(valid_costs.values())
best_methods = [k for k, v in valid_costs.items() if v == min_cost]

# Render Responsive HTML Metric Layout Cards Grid
card_cols = st.columns(6)
for idx, m_key in enumerate(biaya_dict.keys()):
    col_target = card_cols[idx % 6]
    with col_target:
        val_cost = biaya_dict[m_key]
        if val_cost == float('inf'):
            sub_html = "<div style='color: #777; font-size: 12px;'>⚠️ N/A (H=0)</div>"
            cost_str = "Disabled"
        else:
            is_best = m_key in best_methods
            sub_html = "<div style='color: #2e7d32; font-size: 12px; font-weight: bold;'>🏆 Optimal Strategy</div>" if is_best else f"<div style='color: #d90429; font-size: 12px; font-weight: bold;'>⚠️ Inefficient (+{(val_cost - min_cost):,.2f})</div>"
            cost_str = f"${val_cost:,.2f}"
            
        st.markdown(f"""
            <div style='background-color: #fafafa; padding: 12px; border-radius: 6px; border-left: 4px solid #6a0708; margin-bottom: 10px; min-height: 110px;'>
                <div style='color: #555; font-size: 12px; font-weight: 600;'>Total Cost {m_key}</div>
                <div style='font-size: 18px; font-weight: 700; color: #111; margin-top: 2px;'>{cost_str}</div>
                {sub_html}
            </div>
        """, unsafe_allow_html=True)

methods_recommendation_string = " & ".join(best_methods)
st.markdown(f"""
    <div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-left: 5px solid #2e7d32; padding: 12px; border-radius: 4px; margin-top: 15px; text-align: center;">
        <span style="color: #2e7d32; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">🎯 Strategic Portfolio Deployment Recommendation:</span>
        <span style="color: #111; font-size: 14px; font-weight: 500;"> It is optimal to apply the <b>{methods_recommendation_string} Model</b> framework to minimize global storage and procurement costs.</span>
    </div>
""", unsafe_allow_html=True)


# ==========================================
# 5. SENSITIVITY SYSTEM & VISUALIZATIONS
# ==========================================
st.markdown("---")
st.subheader("📉 Parametric Performance Sensitivity Analysis Charts")

cg1, cg2 = st.columns(2)
with cg1:
    fig, ax = plt.subplots(figsize=(6, 3.8))
    fig.patch.set_facecolor('#fafafa')
    ax.set_facecolor('#fafafa')
    
    keys_plot = [k for k, v in biaya_dict.items() if v != float('inf')]
    values_plot = [v for v in biaya_dict.values() if v != float('inf')]
    
    color_palette = ['#444444', '#e65c00', '#6a0708', '#2a7b4c', '#0288d1', '#7b1fa2', '#1565c0', '#2e7d32', '#d32f2f', '#f57c00', '#111111']
    ax.bar(keys_plot, values_plot, color=color_palette[:len(keys_plot)], width=0.5)
    ax.set_title("Direct Comparison of Lot Sizing Methods", fontsize=10, fontweight='bold', color='#6a0708')
    ax.set_ylabel('Total Cost incurred ($)', fontsize=8)
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    st.pyplot(fig)

with cg2:
    pct_integers = np.linspace(-30, 30, 7, dtype=int)
    sim_data = {k: [] for k in biaya_dict.keys()}
    labels_pct = []
    
    for p_val in pct_integers:
        scale_factor = 1.0 + (p_val / 100.0)
        sim_demand = [max(0, int(round(d * scale_factor))) for d in gross_req]
        
        s_res = calculate_multi_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time, fixed_lot_size, fpr_interval, min_order_qty, enforce_moq)
        
        sim_data['L4L'].append(s_res['l4l']['total'])
        sim_data['FOQ'].append(s_res['foq']['total'])
        sim_data['FPR'].append(s_res['fpr']['total'])
        sim_data['EOQ'].append(s_res['eoq']['total'] if holding_cost > 0 else 0)
        sim_data['POQ'].append(s_res['poq']['total'] if holding_cost > 0 else 0)
        sim_data['IUC'].append(s_res['iuc']['total'])
        sim_data['LUC'].append(s_res['luc']['total'])
        sim_data['LTC'].append(s_res['ltc']['total'])
        sim_data['PPB'].append(s_res['ppb']['total'])
        sim_data['SM'].append(s_res['sm']['total'])
        sim_data['WW'].append(s_res['ww']['total'])
        labels_pct.append(f"{p_val:+}%")
        
    fig2, ax2 = plt.subplots(figsize=(6, 3.8))
    fig2.patch.set_facecolor('#fafafa')
    ax2.set_facecolor('#fafafa')
    
    markers_palette = ['o', 's', 'v', '^', '<', '>', 'p', '*', 'h', 'H', 'D']
    for idx, m_key in enumerate(biaya_dict.keys()):
        if holding_cost == 0 and m_key in ['EOQ', 'POQ']:
            continue
        ax2.plot(labels_pct, sim_data[m_key], marker=markers_palette[idx], label=m_key, linewidth=1.2)
        
    ax2.set_title("Demand Instability Sensitivity Stress-Test Chart", fontsize=10, fontweight='bold', color='#6a0708')
    ax2.set_ylabel('Simulated Cost Total ($)', fontsize=8)
    ax2.grid(True, linestyle=':', alpha=0.5)
    ax2.legend(facecolor='#fafafa', fontsize=7, loc='upper left', ncol=2)
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    st.pyplot(fig2)


# ==========================================
# 6. REPORT ARCHITECTURE EXPORTER
# ==========================================
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    # Frame matrix map
    pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=period_labels).T.to_excel(writer, sheet_name="Baseline Framework")
    
    # Sequential export matching the exact academic hierarchy list
    order_sequence_export = ['l4l', 'foq', 'fpr', 'eoq', 'poq', 'iuc', 'luc', 'ltc', 'ppb', 'sm', 'ww']
    for sheet_key in order_sequence_export:
        if holding_cost == 0 and sheet_key in ['eoq', 'poq']:
            continue
        pd.DataFrame({
            'Projected On Hand': res[sheet_key]['poh'],
            'Planned Order Receipts': res[sheet_key]['rec'],
            'Planned Order Releases': res[sheet_key]['rel']
        }, index=period_labels).T.to_excel(writer, sheet_name=f"{sheet_key.upper()} Plan Strategy")

buffer.seek(0)
st.markdown("<br>", unsafe_allow_html=True)
st.download_button(
    label="📥 Download Plan Document Report (11 Methods Synchronized).xlsx",
    data=buffer,
    file_name="MRP_Lot_Sizing_Unified_Corporate_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
