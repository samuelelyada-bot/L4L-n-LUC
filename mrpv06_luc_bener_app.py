import streamlit as st
import pandas as pd
import numpy as np
import math
import io
import matplotlib.pyplot as plt

# ==========================================
# 1. PAGE CONFIGURATION & CLEAN CSS OVERRIDE
# ==========================================
st.set_page_config(page_title="Advanced MRP Lot Sizing Workbench", layout="wide")

# Inject CSS Custom untuk layout dan mempertegas warna tombol download menjadi TEBAL & MERAH MARUN
st.markdown("""
    <style>
    .reportview-container { background-color: #faf8f2; }
    div.stDownloadButton > button p {
        color: #6a0708 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CORE TOP-LEVEL FUNCTIONS (FASE 1 & 2)
# ==========================================
def generate_poh_and_release(rec_lot, demands, s_receipts, init_inv, lt, n):
    """Menghitung matriks POH (Projected On Hand) dan PORel (Planned Order Release) secara independen."""
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

def calculate_cost_metrics(rec, poh, setup_cost, holding_cost):
    """Audit pengeluaran finansial operasional untuk setup dan holding cost."""
    s_c = sum(1 for x in rec if x > 0) * setup_cost
    h_c = sum(x * holding_cost for x in poh)
    return s_c, h_c, s_c + h_c

# --- ALGORITMA LOT SIZING MANDIRI ---

def algo_l4l(net_req, n):
    rec = [0] * n
    for i in range(n):
        if net_req[i] > 0:
            rec[i] = net_req[i]
    return rec

def algo_eoq(net_req, n, eoq_size):
    rec = [0] * n
    rem = 0
    for i in range(n):
        if net_req[i] > 0:
            if rem < net_req[i]:
                needed = net_req[i] - rem
                lots = math.ceil(needed / eoq_size) if eoq_size > 0 else 1
                rec[i] = lots * eoq_size
                rem = rec[i] + rem - net_req[i]
            else:
                rem -= net_req[i]
    return rec

def algo_luc(net_req, n, setup_cost, holding_cost, period_labels):
    rec = [0] * n
    trace_logs = []
    idx = 0
    while idx < n:
        if net_req[idx] == 0:
            idx += 1
            continue
        best_k = idx
        min_uc = float('inf')
        acc_d = 0
        acc_h = 0
        t_log = []
        for k in range(idx, n):
            acc_d += net_req[k]
            acc_h += net_req[k] * holding_cost * (k - idx)
            t_cost = setup_cost + acc_h
            uc = t_cost / acc_d if acc_d > 0 else float('inf')
            if uc < min_uc:
                min_uc = uc
                best_k = k
                t_log.append({
                    'Iteration': f"Start from {period_labels[idx]}", 'Period Evaluated': period_labels[k],
                    'Accumulated Demand': acc_d, 'Accumulated Holding': acc_h,
                    'Total Cost (S+H)': t_cost, 'Unit Cost': round(uc, 4), 'Status': 'Feasible (Closer)'
                })
            else:
                t_log.append({
                    'Iteration': f"Start from {period_labels[idx]}", 'Period Evaluated': period_labels[k],
                    'Accumulated Demand': acc_d, 'Accumulated Holding': acc_h,
                    'Total Cost (S+H)': t_cost, 'Unit Cost': round(uc, 4), 'Status': 'Stop ⚠️ (Cost Increased)'
                })
                break
        for item in t_log:
            if item['Period Evaluated'] == period_labels[best_k]:
                item['Status'] = 'Horizon End (Optimal)' if (best_k == n - 1 and item['Status'] != 'Stop ⚠️ (Cost Increased)') else 'Selected 🎯'
        trace_logs.extend(t_log)
        rec[idx] = sum(net_req[idx:best_k+1])
        idx = best_k + 1
    return rec, trace_logs

def algo_ppb(net_req, n, setup_cost, holding_cost, epp_target, period_labels):
    rec = [0] * n
    trace_logs = []
    idx = 0
    while idx < n:
        if net_req[idx] == 0:
            idx += 1
            continue
        best_k = idx
        acc_pp = 0
        t_log = []
        for k in range(idx, n):
            current_pp = net_req[k] * (k - idx)
            acc_pp += current_pp
            t_log.append({
                'Iteration': f"Start from {period_labels[idx]}", 'Period Evaluated': period_labels[k],
                'Net Req': net_req[k], 'Multiplier': f"({k}-{idx})", 'Part-Period Contribution': current_pp,
                'Accumulated Part-Period': round(acc_pp, 2), 'Target EPP': round(epp_target, 2), 'Status': 'Feasible'
            })
            if acc_pp > epp_target:
                dist_before = abs((acc_pp - current_pp) - epp_target)
                dist_after = abs(acc_pp - epp_target)
                if dist_after < dist_before:
                    best_k = k
                    t_log[-1]['Status'] = 'Feasible (Closer Beyond Limit)'
                else:
                    best_k = k - 1
                    t_log[-1]['Status'] = 'Stop ⚠️ (Limit Exceeded)'
                break
            else:
                best_k = k
        for item in t_log:
            if item['Period Evaluated'] == period_labels[best_k]:
                if item['Status'] not in ['Stop ⚠️ (Limit Exceeded)', 'Feasible (Closer Beyond Limit)']:
                    item['Status'] = 'Horizon End (Optimal)' if best_k == n - 1 else 'Selected 🎯'
        trace_logs.extend(t_log)
        rec[idx] = sum(net_req[idx:best_k+1])
        idx = best_k + 1
    return rec, trace_logs

def algo_silver_meal(net_req, n, setup_cost, holding_cost, period_labels):
    rec = [0] * n
    trace_logs = []
    idx = 0
    while idx < n:
        if net_req[idx] == 0:
            idx += 1
            continue
        best_k = idx
        min_avg = float('inf')
        acc_h = 0
        periods_covered = 0
        t_log = []
        for k in range(idx, n):
            acc_h += net_req[k] * holding_cost * (k - idx)
            periods_covered += 1
            t_cost = setup_cost + acc_h
            avg_cost = t_cost / periods_covered if periods_covered > 0 else float('inf')
            total_units_covered = sum(net_req[idx:k+1])
            
            if avg_cost < min_avg:
                min_avg = avg_cost
                best_k = k
                t_log.append({
                    'Iteration': f"Start from {period_labels[idx]}", 'Period Evaluated': period_labels[k],
                    'Periods Covered': periods_covered, 'Total Units': total_units_covered,
                    'Setup Cost': setup_cost, 'Holding Cost': acc_h, 'Total Cost (S+H)': t_cost,
                    'Avg Cost/Period': round(avg_cost, 4), 'Status': 'Feasible'
                })
            else:
                t_log.append({
                    'Iteration': f"Start from {period_labels[idx]}", 'Period Evaluated': period_labels[k],
                    'Periods Covered': periods_covered, 'Total Units': total_units_covered,
                    'Setup Cost': setup_cost, 'Holding Cost': acc_h, 'Total Cost (S+H)': t_cost,
                    'Avg Cost/Period': round(avg_cost, 4), 'Status': 'Stop ⚠️ (Cost Increased)'
                })
                break
        for item in t_log:
            if item['Period Evaluated'] == period_labels[best_k]:
                item['Status'] = 'Horizon End (Optimal)' if (best_k == n - 1 and item['Status'] != 'Stop ⚠️ (Cost Increased)') else 'Selected 🎯'
        trace_logs.extend(t_log)
        rec[idx] = sum(net_req[idx:best_k+1])
        idx = best_k + 1
    return rec, trace_logs

def algo_poq(net_req, n, poq_interval):
    rec = [0] * n
    i = 0
    while i < n:
        if net_req[i] == 0:
            i += 1
            continue
        window_end = min(i + poq_interval, n)
        total_demand_in_window = sum(net_req[i:window_end])
        if total_demand_in_window > 0:
            rec[i] = total_demand_in_window
        i = window_end
    return rec

def algo_foq(net_req, n, foq_size):
    rec = [0] * n
    rem = 0
    for i in range(n):
        if net_req[i] > 0:
            if rem < net_req[i]:
                needed = net_req[i] - rem
                lots = math.ceil(needed / foq_size) if foq_size > 0 else 1
                rec[i] = lots * foq_size
                rem = rec[i] + rem - net_req[i]
            else:
                rem -= net_req[i]
    return rec

def apply_moq_constraint(rec_lot, moq_size):
    return [max(x, moq_size) if x > 0 else 0 for x in rec_lot]

def find_matching_column(columns, candidates):
    for c in columns:
        if c.lower().replace(" ", "").replace("_", "") in candidates:
            return c
    return None

# ==========================================
# 3. GLOBAL CONTROLS SIDEBAR FRAMEWORK
# ==========================================
st.sidebar.title("🛠️ MRP Global Parameters")
setup_cost = st.sidebar.number_input("Setup/Ordering Cost (S):", min_value=1.0, value=100.0, step=10.0)
holding_cost = st.sidebar.number_input("Holding Cost/Unit/Period (h):", min_value=0.01, value=2.0, step=0.5)
initial_inv = st.sidebar.number_input("Initial Inventory On-Hand:", min_value=0, value=20)
safety_stock = st.sidebar.number_input("Safety Stock Threshold:", min_value=0, value=5)
lead_time = st.sidebar.number_input("Lead Time Offsetting (Periods):", min_value=0, value=1, step=1)

# Global Toggle untuk Mengaktifkan Aturan MOQ di Penjuru Sistem
apply_moq_global = st.sidebar.checkbox("Apply MOQ Constraint Globally")

# ==========================================
# 4. DATA ACQUISITION WORKBENCH (FIXED M.ENTRY & S.S.T)
# ==========================================
st.subheader("📊 Data Input workbench")
input_method = st.radio("Select Input Configuration Method:", ["Upload File", "Manual Entry", "Load Template"])
df_workbench = None

if input_method == "Upload File":
    uploaded_file = st.file_uploader("Upload demand documents (.csv, .xlsx)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            col_p = find_matching_column(df_raw.columns, ['periode', 'mingguke', 'p', 'minggu', 'period', 'week'])
            col_gr = find_matching_column(df_raw.columns, ['gr', 'grossrequirement', 'grossrequirements', 'kebutuhankotor'])
            col_sr = find_matching_column(df_raw.columns, ['sr', 'scheduledreceipt', 'scheduledreceipts', 'penerimaanterjadwal'])
            
            df_workbench = pd.DataFrame()
            df_workbench['Period'] = df_raw[col_p].astype(str) if col_p else [f"P{i+1}" for i in range(len(df_raw))]
            if col_gr:
                df_workbench['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int)
            else:
                st.error("Failed to map Gross Requirements attribute automatically.")
                st.stop()
            df_workbench['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int) if col_sr else 0
        except Exception as e:
            st.error(f"Engine parsing failure: {e}"); st.stop()
            
elif input_method == "Manual Entry":
    num_periods_input = st.number_input("Planning Horizon Length (Periods):", min_value=1, max_value=52, value=10, step=1)
    default_gr = [35, 30, 40, 0, 10, 40, 30, 0, 30, 55] if num_periods_input == 10 else [0] * num_periods_input
    init_data = {'Period': [f"P{i+1}" for i in range(num_periods_input)], 'Gross Requirements': default_gr, 'Scheduled Receipts': [0] * num_periods_input}
    st.markdown("##### ✏️ Edit Demand & Scheduled Receipts Data Below:")
    df_workbench = st.data_editor(pd.DataFrame(init_data), use_container_width=True, hide_index=True)
else:
    default_data = {'Period': [f"P{i}" for i in range(1, 11)], 'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55], 'Scheduled Receipts': [0]*10}
    df_workbench = pd.DataFrame(default_data)

# Sinkronisasi Data S.S.T (Single Source of Truth)
if df_workbench is not None and not df_workbench.empty:
    gross_req = df_workbench['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec = df_workbench['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_workbench['Period'].astype(str).tolist()
    
    st.markdown("##### Input Data Matrix Summary View (Transposed):")
    df_preview_transposed = pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec}, index=period_labels).T
    
    if input_method == "Manual Entry":
        st.dataframe(df_preview_transposed, use_container_width=True)
        df_edited_preview = df_preview_transposed
    else:
        df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
        
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()

    # ==========================================
    # 5. DATA COMPILATION & STAGE ENGINE
    # ==========================================
    n = len(gross_req)
    
    # Perhitungan Baseline Net Requirements Global
    net_req = []
    curr_inv = initial_inv
    for i in range(n):
        avail = curr_inv + sched_rec[i]
        if avail >= gross_req[i] + safety_stock:
            net_req.append(0); curr_inv = avail - gross_req[i]
        else:
            needed = (gross_req[i] + safety_stock) - avail
            net_req.append(needed); curr_inv = safety_stock

    # Baseline Parametrik Teoretis
    avg_d = np.mean(gross_req) if n > 0 else 0
    eoq_calc_val = math.ceil(math.sqrt((2 * setup_cost * avg_d) / holding_cost)) if holding_cost > 0 and avg_d > 0 else 1
    epp_target_val = setup_cost / holding_cost if holding_cost > 0 else float('inf')

    # Struktur Dictionary Session State Penampung Biaya Final untuk Komparasi Global
    if 'biaya_global' not in st.session_state:
        st.session_state.biaya_global = {}
        
    moq_size = st.session_state.get('moq_size_state', 0)

    # Helper untuk memproses visualisasi standardisasi grid tabel MRP
    def display_mrp_grid(p_labels, gr, sr, nr, rec, poh, rel):
        mrp_df = pd.DataFrame({
            'Gross Requirements': gr, 'Scheduled Receipts': sr, 'Net Requirements': nr,
            'Planned Order Receipts': rec, 'Projected On Hand': poh, 'Planned Order Releases': rel
        }, index=p_labels).T
        st.dataframe(mrp_df, use_container_width=True)

    st.markdown("---")
    st.subheader("⚙️ Tactical Execution per Sizing Method")

    # Penyusunan 8 Tab Sesuai Visi Desain UI Terbaru
    t_l4l, t_eoq, t_luc, t_ppb, t_sm, t_poq, t_foq, t_moq = st.tabs([
        "📋 L4L", "📦 EOQ", "💰 LUC", "⚖️ PPB", "📊 Silver-Meal", "⏱️ POQ", "🎯 FOQ", "🛡️ MOQ Config"
    ])

    # --- TAB 1: LOT-FOR-LOT ---
    with t_l4l:
        st.markdown("#### Lot-for-Lot Execution Framework")
        rec_arr = algo_l4l(net_req, n)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['L4L'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (L4L)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")

    # --- TAB 2: EOQ ---
    with t_eoq:
        st.markdown(f"#### Economic Order Quantity (Calculated Size: {eoq_calc_val} Units)")
        rec_arr = algo_eoq(net_req, n, eoq_calc_val)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['EOQ'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (EOQ)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")

    # --- TAB 3: LUC ---
    with t_luc:
        st.markdown("#### Least Unit Cost Optimization Engine")
        rec_arr, logs_luc = algo_luc(net_req, n, setup_cost, holding_cost, period_labels)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['LUC'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (LUC)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")
        st.markdown("##### 🔍 Least Unit Cost Trace Log Database")
        st.dataframe(pd.DataFrame(logs_luc), use_container_width=True, hide_index=True)

    # --- TAB 4: PPB ---
    with t_ppb:
        st.markdown(f"#### Part Period Balancing Optimization (Target EPP: {epp_target_val:.2f})")
        rec_arr, logs_ppb = algo_ppb(net_req, n, setup_cost, holding_cost, epp_target_val, period_labels)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['PPB'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (PPB)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")
        st.markdown("##### 🔍 Part Period Balancing Trace Log Database")
        st.dataframe(pd.DataFrame(logs_ppb), use_container_width=True, hide_index=True)

    # --- TAB 5: SILVER MEAL ---
    with t_sm:
        st.markdown("#### Silver-Meal Optimization Engine")
        rec_arr, logs_sm = algo_silver_meal(net_req, n, setup_cost, holding_cost, period_labels)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['Silver-Meal'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (Silver-Meal)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")
        st.markdown("##### 🔍 Silver-Meal Heuristic Trace Log Database")
        st.dataframe(pd.DataFrame(logs_sm), use_container_width=True, hide_index=True)

    # --- TAB 6: POQ ---
    with t_poq:
        st.markdown("#### Periodic Order Quantity Horizon Framework")
        poq_interval = st.number_input("Set Order Cycle Window Interval (Periods):", min_value=1, max_value=n if n > 0 else 12, value=3, step=1)
        rec_arr = algo_poq(net_req, n, poq_interval)
        if apply_moq_global and moq_size > 0:
            rec_arr = apply_moq_constraint(rec_arr, moq_size)
        poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
        s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
        st.session_state.biaya_global['POQ'] = t
        display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
        st.metric("Total Incurred Cost (POQ)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")

    # --- TAB 7: FOQ ---
    with t_foq:
        st.markdown("#### Fixed Order Quantity Paradigm Control")
        foq_size = st.number_input("Set Fixed Lot Size Quantity Configuration:", min_value=0, max_value=2000, value=0, step=10)
        
        # LOCK MECHANISM (Kunci Kalkulasi jika Input masih 0)
        if foq_size == 0:
            st.warning("⚠️ Silakan masukkan kuantitas FOQ terlebih dahulu pada kotak input di atas untuk menjalankan kalkulasi.")
            if 'FOQ' in st.session_state.biaya_global:
                del st.session_state.biaya_global['FOQ']
        else:
            rec_arr = algo_foq(net_req, n, foq_size)
            if apply_moq_global and moq_size > 0:
                rec_arr = apply_moq_constraint(rec_arr, moq_size)
            poh_arr, rel_arr = generate_poh_and_release(rec_arr, gross_req, sched_rec, initial_inv, lead_time, n)
            s, h, t = calculate_cost_metrics(rec_arr, poh_arr, setup_cost, holding_cost)
            st.session_state.biaya_global['FOQ'] = t
            display_mrp_grid(period_labels, gross_req, sched_rec, net_req, rec_arr, poh_arr, rel_arr)
            st.metric("Total Incurred Cost (FOQ)", f"${t:,.2f}", f"Setup: ${s} | Hold: ${h}")

    # --- TAB 8: MOQ CONFIGURATION ---
    with t_moq:
        st.markdown("#### 🛡️ Supplier MOQ Constraint Configuration")
        moq_input = st.number_input("Set Minimum Order Quantity (MOQ Threshold Size):", min_value=0, max_value=2000, value=0, step=5, key="moq_size_state")
        
        if moq_input > 0:
            if apply_moq_global:
                st.success(f"🛡️ Status MOQ: AKTIF ({moq_input} units) dan diaplikasikan ke seluruh penjuru metode.")
            else:
                st.info(f"💡 Batas MOQ tersimpan ({moq_input} units). Untuk menerapkannya, silakan centang 'Apply MOQ Constraint Globally' di Sidebar.")
        else:
            st.info("Status MOQ: Terbuka (0). Seluruh eksekusi metode berjalan murni tanpa restriksi batas minimal supplier.")

    # ==========================================
    # 6. SENSITIVITY CHARTS & EXPORT INTERFACE
    # ==========================================
    st.markdown("---")
    st.subheader("📉 Parametric Sensitivity Analysis Charts")
    
    c_graph1, c_graph2 = st.columns(2)
    
    with c_graph1:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        fig.patch.set_facecolor('#faf8f2'); ax.set_facecolor('#faf8f2')
        
        # Grafik Komparatif Dinamis (Hanya merender metode yang ada di session state)
        k_methods = list(st.session_state.biaya_global.keys())
        v_costs = list(st.session_state.biaya_global.values())
        
        if v_costs:
            ax.bar(k_methods, v_costs, color=['#444444', '#6a0708', '#e65c00', '#2a7b4c', '#5a189a', '#0077b6', '#f72585'], width=0.45)
            ax.set_title("Comparison of Lot Sizing Active Methods", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
            ax.set_ylabel('Total Cost', fontsize=9, fontweight='bold')
            ax.grid(axis='y', linestyle=':', alpha=0.6)
            st.pyplot(fig)
        else:
            st.info("No calculated cost data infrastructure found.")

    with c_graph2:
        scale_factors = np.arange(0.70, 1.31, 0.05)
        s_l4l, s_eoq, s_luc, s_ppb, s_sm, labels_pct = [], [], [], [], [], []
        
        # Jalankan simulasi stress test dinamis untuk metode stabil
        for f in scale_factors:
            pct_val = int(round((f - 1) * 100))
            if pct_val > 30: continue
            s_dem = [int(round(d * f)) for d in gross_req]
            
            # Simulasi Parsial Internal Stress Test
            s_nr = []
            c_inv = initial_inv
            for i in range(n):
                av = c_inv + sched_rec[i]
                if av >= s_dem[i] + safety_stock:
                    s_nr.append(0); c_inv = av - s_dem[i]
                else:
                    s_nr.append((s_dem[i] + safety_stock) - av); c_inv = safety_stock
            
            labels_pct.append(f"{pct_val:+}%")
            
            r_l4l = algo_l4l(s_nr, n); p_l4l, _ = generate_poh_and_release(r_l4l, s_dem, sched_rec, initial_inv, lead_time, n); _, _, t_l4l = calculate_cost_metrics(r_l4l, p_l4l, setup_cost, holding_cost); s_l4l.append(t_l4l)
            r_eoq = algo_eoq(s_nr, n, eoq_calc_val); p_eoq, _ = generate_poh_and_release(r_eoq, s_dem, sched_rec, initial_inv, lead_time, n); _, _, t_eoq = calculate_cost_metrics(r_eoq, p_eoq, setup_cost, holding_cost); s_eoq.append(t_eoq)
            r_luc, _ = algo_luc(s_nr, n, setup_cost, holding_cost, period_labels); p_luc, _ = generate_poh_and_release(r_luc, s_dem, sched_rec, initial_inv, lead_time, n); _, _, t_luc = calculate_cost_metrics(r_luc, p_luc, setup_cost, holding_cost); s_luc.append(t_luc)
            r_ppb, _ = algo_ppb(s_nr, n, setup_cost, holding_cost, epp_target_val, period_labels); p_ppb, _ = generate_poh_and_release(r_ppb, s_dem, sched_rec, initial_inv, lead_time, n); _, _, t_ppb = calculate_cost_metrics(r_ppb, p_ppb, setup_cost, holding_cost); s_ppb.append(t_ppb)
            r_sm, _ = algo_silver_meal(s_nr, n, setup_cost, holding_cost, period_labels); p_sm, _ = generate_poh_and_release(r_sm, s_dem, sched_rec, initial_inv, lead_time, n); _, _, t_sm = calculate_cost_metrics(r_sm, p_sm, setup_cost, holding_cost); s_sm.append(t_sm)

        fig2, ax2 = plt.subplots(figsize=(7, 4.2))
        fig2.patch.set_facecolor('#faf8f2'); ax2.set_facecolor('#faf8f2')
        ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#444444')
        ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#e65c00')
        ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#6a0708')
        ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#2a7b4c')
        ax2.plot(labels_pct, s_sm, marker='d', label='SM', color='#5a189a')
        ax2.set_title("Heuristics Demand Change Sensitivity Chart", fontsize=11, fontweight='bold', color='#6a0708', pad=12)
        ax2.grid(True, linestyle=':', alpha=0.6); ax2.legend(facecolor='#faf8f2', fontsize=9)
        plt.xticks(rotation=30)
        st.pyplot(fig2)

    # --- REPORT EXPORT SYSTEM ---
    st.markdown("---")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': net_req}, index=period_labels).T.to_excel(writer, sheet_name="Baseline Strategy")
        # Generator lembar kerja taktis hasil kalkulasi
        for m in k_methods:
            if m == 'L4L': r = algo_l4l(net_req, n)
            elif m == 'EOQ': r = algo_eoq(net_req, n, eoq_calc_val)
            elif m == 'LUC': r, _ = algo_luc(net_req, n, setup_cost, holding_cost, period_labels)
            elif m == 'PPB': r, _ = algo_ppb(net_req, n, setup_cost, holding_cost, epp_target_val, period_labels)
            elif m == 'Silver-Meal': r, _ = algo_silver_meal(net_req, n, setup_cost, holding_cost, period_labels)
            elif m == 'POQ': r = algo_poq(net_req, n, poq_interval)
            elif m == 'FOQ': r = algo_foq(net_req, n, foq_size)
            
            if apply_moq_global and moq_size > 0:
                r = apply_moq_constraint(r, moq_size)
            p, rl = generate_poh_and_release(r, gross_req, sched_rec, initial_inv, lead_time, n)
            pd.DataFrame({'Projected On Hand': p, 'Planned Order Receipts': r, 'Planned Order Releases': rl}, index=period_labels).T.to_excel(writer, sheet_name=f"{m} Plan")
            
    buffer.seek(0)
    
    c_btn1, c_btn2, c_btn3 = st.columns([1, 2, 1])
    with c_btn2:
        st.download_button(
            label="📥 Download Plan Document Report", data=buffer,
            file_name="MRP_Comprehensive_Lot_Sizing_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    st.info("Please initialize input values or upload transaction vectors to run calculation routines.")
