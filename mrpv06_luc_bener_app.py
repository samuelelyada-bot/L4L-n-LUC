import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import io

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="OptiLot - Advanced MRP Decision Support System", layout="wide")

# Inject custom CSS for clean, minimalist, and modern UI
st.markdown("""
    <style>
        /* Global font smoothing and clean background */
        .reportview-container {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        /* Minimalist Metric Cards */
        .metric-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 16px;
        }
        .metric-title {
            color: #64748b;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }
        .metric-status-optimal {
            color: #10b981;
            font-size: 13px;
            font-weight: 600;
            margin-top: 6px;
        }
        .metric-status-suboptimal {
            color: #ef4444;
            font-size: 13px;
            font-weight: 600;
            margin-top: 6px;
        }
    </style>
""", unsafe_allow_html=True)

# App Header
st.title("OptiLot")
st.caption("Advanced Material Requirements Planning (MRP) Decision Support System")
st.markdown("---")

# ==========================================
# 2. SIDEBAR - CONTROL PANEL
# ==========================================
st.sidebar.header("Configuration Panel")

setup_cost = st.sidebar.number_input("Ordering / Setup Cost ($)", min_value=0.0, value=100000.0, step=500.0)
holding_cost = st.sidebar.number_input("Holding Cost ($ / unit / period)", min_value=0.0, value=2000.0, step=500.0)
initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time (Periods)", min_value=0, value=1, step=1)

st.sidebar.markdown("---")
st.sidebar.header("Operational Constraints")
max_capacity = st.sidebar.number_input("Maximum Warehouse Capacity (Units)", min_value=1, value=100, step=10)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def dapatkan_kolom_cocok(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

def get_styled_mrp_table(df_mrp_transposed, max_cap):
    def highlight_row_capacity(row):
        if row.name == 'Projected On Hand':
            return ['background-color: #fef3c7; color: #d97706; font-weight: 600;' if val > max_cap else '' for val in row]
        return [''] * len(row)
    return df_mrp_transposed.style.apply(highlight_row_capacity, axis=1)

def highlight_stop(row):
    return ['background-color: #fee2e2; color: #991b1b; font-weight: 600;' if 'Stop!' in str(row['Status']) else '' for _ in row]

# ==========================================
# 3. DATA INPUT SECTION
# ==========================================
st.subheader("Data Input Management")

input_method = st.radio(
    "Select Data Input Method:", 
    ["Upload File (Excel / CSV)", "Manual Grid Entry", "Use Default Demo Data"],
    horizontal=True
)

df_kerja = None

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file (Supported: .xlsx, .xls, .csv)", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            col_periode = dapatkan_kolom_cocok(df_raw.columns, ['periode', 'period', 'mingguke', 'p', 'week'])
            col_gr = dapatkan_kolom_cocok(df_raw.columns, ['gr', 'grossrequirement', 'grossrequirements', 'kebutuhankotor'])
            col_sr = dapatkan_kolom_cocok(df_raw.columns, ['sr', 'scheduledreceipt', 'scheduledreceipts', 'penerimaanterjadwal'])
            
            df_kerja = pd.DataFrame()
            
            if col_periode and col_periode in df_raw.columns:
                df_kerja['Period'] = df_raw[col_periode].astype(str)
            else:
                df_kerja['Period'] = [f"P{i+1}" for i in range(len(df_raw))]
                
            if col_gr and col_gr in df_raw.columns:
                df_kerja['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int)
            else:
                st.error("❌ Gross Requirements (GR) column not automatically detected.")
                
            if col_sr and col_sr in df_raw.columns:
                df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_kerja['Scheduled Receipts'] = 0
                
        except Exception as e:
            st.error(f"Failed to read file. Error: {e}")
            
elif input_method == "Manual Grid Entry":
    num_periods_input = st.number_input("Define Number of Planning Periods:", min_value=1, max_value=52, value=10, step=1)
    init_data = {
        'Period': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55] if num_periods_input == 10 else [0] * num_periods_input,
        'Scheduled Receipts': [0] * num_periods_input
    }
    df_empty = pd.DataFrame(init_data)
    df_kerja = st.data_editor(df_empty, use_container_width=True, hide_index=True)

else:
    default_data = {
        'Period': [f"P{i}" for i in range(1, 11)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55],
        'Scheduled Receipts': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    }
    df_kerja = pd.DataFrame(default_data)

if df_kerja is not None and not df_kerja.empty:
    gross_req = df_kerja['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec = df_kerja['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_kerja['Period'].astype(str).tolist()
    
    st.markdown("##### Input Data Preview")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()

    # ==========================================
    # CORE ALGORITHM (UNTOUCHED)
    # ==========================================
    def calculate_multi_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)
        
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

        # 1. L4L
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = generate_poh_and_release(l4l_rec)
        c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        c_l4l_hold = sum(max(0, x) for x in l4l_poh) * hold

        # 2. LUC
        luc_rec = [0] * n
        luc_iters = []
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
                
                if uc <= min_uc:
                    min_uc, best_k = uc, k
                    status = "Selected (Min)"
                    t_log.append({'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d, 'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                else:
                    status = "Stop! Cost Increased"
                    t_log.append({'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d, 'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                    break
            luc_iters.append(pd.DataFrame(t_log))
            luc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
        luc_poh, luc_rel = generate_poh_and_release(luc_rec)
        c_luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        c_luc_hold = sum(max(0, x) for x in luc_poh) * hold

        # 3. EOQ
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
            else:
                pass
                
        eoq_poh, eoq_rel = generate_poh_and_release(eoq_rec)
        c_eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        c_eoq_hold = sum(max(0, x) for x in eoq_poh) * hold

        # 4. PPB
        ppb_rec = [0] * n
        ppb_iters = []
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
                
                if new_cum_part_period <= epp_limit:
                    acc_d += net_req[k]
                    cum_part_period = new_cum_part_period
                    best_k = k
                    t_log.append({
                        'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d, 
                        'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Approaching Balance"
                    })
                else:
                    dist_sebelum = abs(cum_part_period - epp_limit)
                    dist_sesudah = abs(new_cum_part_period - epp_limit)
                    
                    if dist_sesudah < dist_sebelum:
                        acc_d += net_req[k]
                        cum_part_period = new_cum_part_period
                        best_k = k
                        t_log.append({
                            'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d, 
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Stop! Closest but Exceeded"
                        })
                    else:
                        t_log.append({
                            'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d + net_req[k], 
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': new_cum_part_period, 'Status': "Stop! Previous Distance was Closer"
                        })
                    break
                    
            ppb_iters.append(pd.DataFrame(t_log))
            ppb_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
            
        ppb_poh, ppb_rel = generate_poh_and_release(ppb_rec)
        c_ppb_setup = sum(1 for x in ppb_rec if x > 0) * setup
        c_ppb_hold = sum(max(0, x) for x in ppb_poh) * hold

        return {
            'net_req': net_req,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_iters},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': c_eoq_setup, 'hold': c_eoq_hold, 'total': c_eoq_setup + c_eoq_hold, 'size': eoq_size, 'avg_demand_gross': avg_demand_gross},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': c_ppb_setup, 'hold': c_ppb_hold, 'total': c_ppb_setup + c_ppb_hold, 'iters': ppb_iters}
        }

    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    # ==========================================
    # 4. DASHBOARD PERFORMANCE COMPARISON
    # ==========================================
    st.markdown("---")
    st.subheader("Cost Performance Matrix")
    
    biaya_dict = {
        'Lot-for-Lot (L4L)': res['l4l']['total'], 
        'Least Unit Cost (LUC)': res['luc']['total'], 
        'Economic Order Quantity (EOQ)': res['eoq']['total'], 
        'Part Period Balancing (PPB)': res['ppb']['total']
    }
    best_method = min(biaya_dict, key=biaya_dict.get)
    
    # Modern Minimalist Cards Layout
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        diff_l4l = res['l4l']['total'] - biaya_dict[best_method]
        sub_text = "<div class='metric-status-optimal'>Optimal Strategy</div>" if diff_l4l == 0 else f"<div class='metric-status-suboptimal'>+ ${diff_l4l:,.2f} Variance</div>"
        st.markdown(f"""<div class='metric-card'>
                        <div class='metric-title'>Lot-for-Lot (L4L)</div>
                        <div class='metric-value'>${res['l4l']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        sub_text = "<div class='metric-status-optimal'>Optimal Strategy</div>" if diff_luc == 0 else f"<div class='metric-status-suboptimal'>+ ${diff_luc:,.2f} Variance</div>"
        st.markdown(f"""<div class='metric-card'>
                        <div class='metric-title'>Least Unit Cost (LUC)</div>
                        <div class='metric-value'>${res['luc']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        sub_text = "<div class='metric-status-optimal'>Optimal Strategy</div>" if diff_eoq == 0 else f"<div class='metric-status-suboptimal'>+ ${diff_eoq:,.2f} Variance</div>"
        st.markdown(f"""<div class='metric-card'>
                        <div class='metric-title'>Economic Order Quantity (EOQ)</div>
                        <div class='metric-value'>${res['eoq']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        sub_text = "<div class='metric-status-optimal'>Optimal Strategy</div>" if diff_ppb == 0 else f"<div class='metric-status-suboptimal'>+ ${diff_ppb:,.2f} Variance</div>"
        st.markdown(f"""<div class='metric-card'>
                        <div class='metric-title'>Part Period Balancing (PPB)</div>
                        <div class='metric-value'>${res['ppb']['total']:,.2f}</div>
                        {sub_text}</div>""", unsafe_allow_html=True)

    st.info(f"Optimal Recommendation: The **{best_method}** framework yields the highest economic efficiency for this demand structure.")

    # ==========================================
    # 5. DETAILED ANALYTICS TABS
    # ==========================================
    tab_grafik, t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["Analytics & Sensitivity", "Lot-for-Lot (L4L)", "Least Unit Cost (LUC)", "Economic Order Quantity (EOQ)", "Part Period Balancing (PPB)"])

    with tab_grafik:
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("### Total Cost Breakdown ($)")
            fig, ax = plt.subplots(figsize=(6, 4))
            # Minimalist gray/blue palette
            ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#94a3b8', '#64748b', '#475569', '#334155'])
            plt.xticks(rotation=15, ha='right')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', linestyle=':', alpha=0.5)
            st.pyplot(fig)
        with cg2:
            st.markdown("### Demand Sensitivity Analysis")
            scale_factors = np.arange(0.70, 1.35, 0.05)
            s_l4l, s_luc, s_eoq, s_ppb, labels_pct = [], [], [], [], []
            for f in scale_factors:
                sim_demand = [max(1, int(d * f)) for d in gross_req]
                s_res = calculate_multi_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
                s_l4l.append(s_res['l4l']['total'])
                s_luc.append(s_res['luc']['total'])
                s_eoq.append(s_res['eoq']['total'])
                s_ppb.append(s_res['ppb']['total'])
                labels_pct.append(f"{int(round((f-1)*100)):+}%")
            
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(labels_pct, s_l4l, label='L4L', color='#94a3b8', linestyle='--')
            ax2.plot(labels_pct, s_luc, label='LUC', color='#64748b', marker='o')
            ax2.plot(labels_pct, s_eoq, label='EOQ', color='#475569', marker='s')
            ax2.plot(labels_pct, s_ppb, label='PPB', color='#334155', marker='x')
            ax2.set_ylabel('Total Cost ($)')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.grid(True, linestyle=':', alpha=0.5)
            ax2.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig2)

    def tampilkan_tabel_mrp(nama_metode, data_dict, max_cap):
        df = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': data_dict['poh'],
            'Net Requirements': res['net_req'],
            'Planned Order Receipts': data_dict['rec'],
            'Planned Order Releases': data_dict['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        st.dataframe(get_styled_mrp_table(df, max_cap), use_container_width=True)
        if max(data_dict['poh']) > max_cap:
            st.warning(f"Capacity Warning: Projected Inventory level in {nama_metode} exceeds maximum warehouse capacity limit ({max_cap} units).")

    with t_l4l:
        st.markdown("### MRP Matrix - Lot-for-Lot")
        tampilkan_tabel_mrp("L4L", res['l4l'], max_capacity)

    with t_luc:
        st.markdown("### MRP Matrix - Least Unit Cost")
        with st.expander("View Calculation Iterations"):
            format_luc = {
                'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'LUC (Cost/Unit)': '{:.4f}'
            }
            for idx, df_iter in enumerate(res['luc']['iters']):
                st.markdown(f"**Lot Formation Step {idx+1}:**")
                # Translated the iteration log headers dynamically for the view
                df_iter_en = df_iter.rename(columns={
                    'Iterasi Dari': 'From', 'Hingga': 'To', 'Total Unit': 'Total Units',
                    'Biaya Pesan': 'Setup Cost', 'Biaya Simpan': 'Holding Cost', 'Total Biaya': 'Total Cost'
                })
                styled_df = df_iter_en.style.apply(highlight_stop, axis=1).format(format_luc)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        tampilkan_tabel_mrp("LUC", res['luc'], max_capacity)

    with t_eoq:
        st.markdown("### MRP Matrix - Economic Order Quantity")
        with st.expander("View Formulas & Calculations"):
            total_gross_req = sum(gross_req)
            n_periode = len(gross_req)
            avg_demand_calc = res['eoq']['avg_demand_gross']
            
            st.markdown("#### Lot Size Calculation Steps:")
            st.markdown(f"""
            * Total Gross Requirements ($\sum$ Gross Req) = `{total_gross_req}` units
            * Planning Horizon ($n$) = `{n_periode}` periods
            * Average Demand per Period ($D$) = `{avg_demand_calc:.4f}` units/period
            """)
            st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times D \\times \\text{{Setup Cost}}}}{{\\text{{Holding Cost}}}}}}$$")
            st.markdown(f"Calculated Discrete EOQ Lot Size: **`{res['eoq']['size']}` units**.")
            
        tampilkan_tabel_mrp("EOQ", res['eoq'], max_capacity)

    with t_ppb:
        st.markdown("### MRP Matrix - Part Period Balancing")
        with st.expander("View Part Period Balancing Iterations"):
            format_ppb = {
                'EPP Limit': '{:.2f}', 'Cumulative Part-Period': '{:.2f}'
            }
            for idx, df_iter in enumerate(res['ppb']['iters']):
                st.markdown(f"**Lot Formation Step {idx+1}:**")
                df_iter_en = df_iter.rename(columns={
                    'Iterasi Dari': 'From', 'Hingga': 'To', 'Total Unit': 'Total Units',
                    'Batas EPP': 'EPP Limit', 'Part-Period Kumulatif': 'Cumulative Part-Period'
                })
                styled_df = df_iter_en.style.apply(highlight_stop, axis=1).format(format_ppb)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        tampilkan_tabel_mrp("PPB", res['ppb'], max_capacity)

    # ==========================================
    # 6. EXPORT MANAGEMENT
    # ==========================================
    st.markdown("---")
    st.subheader("Data Export")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Base Demand Data")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="L4L Method")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="LUC Method")
        pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="EOQ Method")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="PPB Method")
    
    buffer.seek(0)
        
    st.download_button(
        label="Download Comprehensive Report (Excel)", 
        data=buffer, 
        file_name="MRP_MultiMethod_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please insert demand requirements above to initiate the MRP engine.")
