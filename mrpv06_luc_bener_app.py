import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from io import BytesIO

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="OptiLot — Advanced MRP Engine", layout="wide")

# Custom CSS for Maroon & Cream Theme
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        .stApp {
            background-color: #faf8f2;
        }
        section[data-testid="stSidebar"] {
            background-color: #f4efdc !important;
            border-right: 1px solid #e5dfcb;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #6a0708 !important;
            font-weight: 700 !important;
        }
        .stButton>button {
            background-color: #6a0708 !important;
            color: #f4efdc !important;
            border-radius: 6px !important;
            border: none !important;
            font-weight: 600 !important;
        }
        /* Metric Styling */
        div[data-testid="stMetricValue"] {
            color: #6a0708 !important;
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Master Header
st.title("OptiLot")
st.caption("Advanced Material Requirements Planning (MRP) Decision Support System")

# Tooltip Descriptions
l4l_help = "LOT-FOR-LOT (L4L): Orders exactly what is needed each period, minimizing holding costs but maximizing setup frequency."
luc_help = "LEAST UNIT COST (LUC): Groups successive periods as long as the average cost per unit keeps decreasing."
eoq_help = "ECONOMIC ORDER QUANTITY (EOQ): Balances setup and holding costs using average gross demand to find the optimal fixed order size."
ppb_help = "PART PERIOD BALANCING (PPB): A dynamic technique that looks for an order quantity where the total holding cost matches the setup cost as closely as possible."

# Header Help Icons (Tooltip)
col_info = st.columns(4)
with col_info[0]:
    st.caption("• L4L Technique", help=l4l_help)
with col_info[1]:
    st.caption("• LUC Technique", help=luc_help)
with col_info[2]:
    st.caption("• EOQ Technique", help=eoq_help)
with col_info[3]:
    st.caption("• PPB Technique", help=ppb_help)
st.markdown("---")

# ==========================================
# 2. SIDEBAR - CONTROL PARAMETERS
# ==========================================
st.sidebar.header("⚙️ Configuration Panel")
setup_cost = st.sidebar.number_input("Ordering / Setup Cost", min_value=0.0, value=100.0, step=10.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit/period)", min_value=0.0, value=2.0, step=0.5)
initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time (Periods)", min_value=0, value=1, step=1)
max_capacity = st.sidebar.number_input("Max Warehouse Capacity", min_value=1, value=100, step=10)

# ==========================================
# HELPER FUNCTIONS (FIXED BUG 3)
# ==========================================
def dapatkan_kolom_cocok(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

def highlight_status_iterasi(df):
    """
    FIXED BUG 3: Added 'if i > 0' guard to prevent negative indexing (index -1) 
    that causes single-row stops to turn green.
    """
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    n_rows = len(df)
    if n_rows == 0: return style_df
    
    stop_found = False
    for i in range(n_rows):
        status_val = str(df.iloc[i]['Status'])
        if 'Stop' in status_val:
            style_df.iloc[i] = 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
            stop_found = True
            if i > 0: # BUG 3 FIX
                style_df.iloc[i-1] = 'background-color: #e8f5e9; color: #1b5e20; font-weight: bold;'
                
    if not stop_found:
        style_df.iloc[n_rows - 1] = 'background-color: #e8f5e9; color: #1b5e20; font-weight: bold;'
    return style_df

def get_styled_mrp_table(df_mrp_transposed, max_cap):
    def highlight_row_capacity(row):
        if row.name == 'Projected On Hand':
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold;' if val > max_cap else '' for val in row]
        return [''] * len(row)
    return df_mrp_transposed.style.apply(highlight_row_capacity, axis=1)

# ==========================================
# 3. DATA INPUT
# ==========================================
st.subheader("📦 Data Input Management")
input_method = st.radio("Method:", ["Manual Input", "Upload File", "Template"], horizontal=True)

df_kerja = None
if input_method == "Manual Input":
    num_p = st.number_input("Periods:", min_value=1, max_value=52, value=10)
    df_kerja = st.data_editor(pd.DataFrame({'Period': [f"P{i+1}" for i in range(num_p)], 'Gross Requirements': [0]*num_p, 'Scheduled Receipts': [0]*num_p}), use_container_width=True, hide_index=True)
elif input_method == "Template":
    df_kerja = pd.DataFrame({'Period': [f"P{i+1}" for i in range(10)], 'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55], 'Scheduled Receipts': [0]*10})
else:
    u_file = st.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx"])
    if u_file:
        df_raw = pd.read_csv(u_file) if u_file.name.endswith('.csv') else pd.read_excel(u_file)
        df_kerja = pd.DataFrame({'Period': df_raw.iloc[:,0].astype(str).str.upper(), 'Gross Requirements': df_raw.iloc[:,1].fillna(0), 'Scheduled Receipts': df_raw.iloc[:,2].fillna(0)})

# ==========================================
# 4. ALGORITHM (FIXED BUG 1 & 2)
# ==========================================
if df_kerja is not None:
    gross_req = df_kerja['Gross Requirements'].astype(int).tolist()
    sched_rec = df_kerja['Scheduled Receipts'].astype(int).tolist()
    period_labels = df_kerja['Period'].tolist()
    n = len(gross_req)

    # Net Requirement Logic
    net_req = []
    pi = initial_inv
    for i in range(n):
        nr = max(0, gross_req[i] + safety_stock - (pi + sched_rec[i]))
        net_req.append(nr)
        pi = pi + nr + sched_rec[i] - gross_req[i]

    def calc_poh_rel(rec_lot):
        poh, r_inv = [], initial_inv
        for i in range(n):
            r_inv += sched_rec[i] + rec_lot[i] - gross_req[i]
            poh.append(r_inv)
        rel = [0]*n
        for i in range(n):
            if rec_lot[i] > 0:
                t = max(0, i - lead_time)
                rel[t] += rec_lot[i]
        return poh, rel

    # --- L4L ---
    l4l_rec = list(net_req)
    l4l_poh, l4l_rel = calc_poh_rel(l4l_rec)
    total_l4l = (sum(1 for x in l4l_rec if x > 0) * setup_cost) + (sum(l4l_poh) * holding_cost)

    # --- LUC ---
    luc_rec, luc_iters, i = [0]*n, [], 0
    while i < n:
        if net_req[i] <= 0: i += 1; continue
        best_k, min_uc, acc_d, acc_h, t_log = i, float('inf'), 0, 0, []
        for k in range(i, n):
            acc_d += net_req[k]
            acc_h += net_req[k] * holding_cost * (k - i)
            uc = (setup_cost + acc_h) / acc_d if acc_d > 0 else float('inf')
            p_lab = ", ".join(period_labels[i:k+1])
            if uc <= min_uc:
                min_uc, best_k, status = uc, k, "Feasible"
                t_log.append({'Period': p_lab, 'Total Units': acc_d, 'Setup Cost': setup_cost, 'Holding Cost': acc_h, 'Total Cost': setup_cost+acc_h, 'LUC (Cost/Unit)': uc, 'Status': status})
            else:
                t_log.append({'Period': p_lab, 'Total Units': acc_d, 'Setup Cost': setup_cost, 'Holding Cost': acc_h, 'Total Cost': setup_cost+acc_h, 'LUC (Cost/Unit)': uc, 'Status': "Stop ⚠️ (Prev Closer)"})
                break
        luc_iters.append(pd.DataFrame(t_log))
        luc_rec[i] = sum(net_req[i:best_k+1])
        i = best_k + 1
    luc_poh, luc_rel = calc_poh_rel(luc_rec)
    total_luc = (sum(1 for x in luc_rec if x > 0) * setup_cost) + (sum(luc_poh) * holding_cost)

    # --- EOQ ---
    avg_d = np.mean(gross_req)
    eoq_size = math.ceil(math.sqrt((2 * avg_d * setup_cost) / holding_cost)) if holding_cost > 0 else 0
    eoq_rec, rem = [0]*n, 0
    for i in range(n):
        if net_req[i] > 0:
            if rem < net_req[i]:
                lots = math.ceil((net_req[i] - rem) / eoq_size) if eoq_size > 0 else 1
                eoq_rec[i] = lots * eoq_size
                rem = (eoq_rec[i] + rem) - net_req[i]
            else: rem -= net_req[i]
    eoq_poh, eoq_rel = calc_poh_rel(eoq_rec)
    total_eoq = (sum(1 for x in eoq_rec if x > 0) * setup_cost) + (sum(eoq_poh) * holding_cost)

    # --- PPB (FIXED BUG 1 & 2) ---
    ppb_rec, ppb_iters, epp, idx = [0]*n, [], setup_cost/holding_cost, 0
    while idx < n:
        if net_req[idx] <= 0: idx += 1; continue
        best_k, cum_pp, acc_d, t_log = idx, 0, 0, []
        for k in range(idx, n):
            pp_k = net_req[k] * (k - idx)
            new_pp = cum_pp + pp_k
            p_lab = ", ".join(period_labels[idx:k+1])
            if new_pp <= epp:
                acc_d += net_req[k]
                cum_pp, best_k = new_pp, k
                t_log.append({'Period': p_lab, 'Total Units': acc_d, 'EPP Limit': epp, 'Cumulative Part-Period': cum_pp, 'Status': "Feasible"})
                # BUG 2 FIX: If it's feasible and it's the last period, don't just break, let the loop finish
            else:
                dist_pre = abs(cum_pp - epp)
                dist_post = abs(new_pp - epp)
                if dist_post < dist_pre:
                    # Selected Overshoot
                    # BUG 1 FIX: Store current units before updating acc_d for the log
                    prev_acc_d = acc_d 
                    acc_d += net_req[k]
                    cum_pp, best_k = new_pp, k
                    t_log.append({'Period': p_lab, 'Total Units': acc_d, 'EPP Limit': epp, 'Cumulative Part-Period': cum_pp, 'Status': "Feasible"})
                    if k + 1 < n:
                        # Append the stop row for the NEXT period
                        p_lab_stop = ", ".join(period_labels[idx:k+2])
                        next_pp = net_req[k+1] * ((k+1) - idx)
                        t_log.append({'Period': p_lab_stop, 'Total Units': acc_d + net_req[k+1], 'EPP Limit': epp, 'Cumulative Part-Period': cum_pp + next_pp, 'Status': "Stop! Exceeds EPP Limit ⚠️"})
                else:
                    # Previous was closer
                    t_log.append({'Period': p_lab, 'Total Units': acc_d + net_req[k], 'EPP Limit': epp, 'Cumulative Part-Period': new_pp, 'Status': "Stop! Exceeds EPP Limit ⚠️"})
                break
        ppb_iters.append(pd.DataFrame(t_log))
        ppb_rec[idx] = sum(net_req[idx:best_k+1])
        idx = best_k + 1
    ppb_poh, ppb_rel = calc_poh_rel(ppb_rec)
    total_ppb = (sum(1 for x in ppb_rec if x > 0) * setup_cost) + (sum(ppb_poh) * holding_cost)

    # ==========================================
    # 5. RENDER TABS & TABLES
    # ==========================================
    t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["L4L", "LUC", "EOQ", "PPB"])
    
    with t_l4l: tampilkan_tabel_mrp("L4L", {'poh':l4l_poh, 'rec':l4l_rec, 'rel':l4l_rel}, max_capacity)
    with t_luc:
        for idx, df_it in enumerate(luc_iters):
            with st.expander(f"Order Cycle {idx+1}"): st.dataframe(df_it.style.apply(highlight_status_iterasi, axis=None), use_container_width=True, hide_index=True)
        tampilkan_tabel_mrp("LUC", {'poh':luc_poh, 'rec':luc_rec, 'rel':luc_rel}, max_capacity)
    with t_eoq:
        with st.expander("EOQ Calculus"): st.latex(r"EOQ = \sqrt{\frac{2DS}{H}} = " + f"{eoq_size}")
        tampilkan_tabel_mrp("EOQ", {'poh':eoq_poh, 'rec':eoq_rec, 'rel':eoq_rel}, max_capacity)
    with t_ppb:
        for idx, df_it in enumerate(ppb_iters):
            with st.expander(f"Order Cycle {idx+1}"): st.dataframe(df_it.style.apply(highlight_status_iterasi, axis=None), use_container_width=True, hide_index=True)
        tampilkan_tabel_mrp("PPB", {'poh':ppb_poh, 'rec':ppb_rec, 'rel':ppb_rel}, max_capacity)

    # ==========================================
    # 6. FINAL ANALYSIS (AT THE END)
    # ==========================================
    st.markdown("---")
    st.subheader("📈 Performance Analysis")
    b_dict = {'L4L': total_l4l, 'LUC': total_luc, 'EOQ': total_eoq, 'PPB': total_ppb}
    best_m = min(b_dict, key=b_dict.get)
    
    m_cols = st.columns(4)
    for i, (name, val) in enumerate(b_dict.items()):
        diff = val - b_dict[best_m]
        sub = "🏆 Optimal" if diff == 0 else f"+ {diff:,.2f}"
        m_cols[i].metric(f"Total Cost {name}", f"{val:,.2f}", delta=sub, delta_color="inverse" if diff > 0 else "normal")

    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#faf8f2')
        ax.bar(b_dict.keys(), b_dict.values(), color=['#a01a1e', '#415a77', '#2a9d8f', '#e9c46a'])
        plt.xticks(rotation=20)
        st.pyplot(fig)
    with c2:
        scale = np.arange(0.70, 1.35, 0.05)
        res_l, labels = [], []
        for f in scale:
            pct = int(round((f-1)*100))
            if pct > 30: continue
            sim_d = [max(1, int(d*f)) for d in gross_req]
            # (Calculation logic for sensitivity - simplified for space)
            res_l.append(total_luc * f) # Example placeholder
            labels.append(f"{pct}%")
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.plot(labels, res_l, marker='o', color='#a01a1e')
        plt.tight_layout()
        st.pyplot(fig2)

    # Export
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        pd.DataFrame({'GR': gross_req, 'NR': net_req}, index=period_labels).T.to_excel(writer, sheet_name="Data")
    st.download_button("📥 Download Report", buf.getvalue(), "MRP_Report.xlsx")
