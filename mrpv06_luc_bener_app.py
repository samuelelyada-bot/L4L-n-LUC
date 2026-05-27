import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import io
from io import BytesIO

# ==========================================
# 1. PAGE CONFIGURATION & PREMIUM EMERGE SKIN
# ==========================================
st.set_page_config(page_title="OptiLot — Advanced MRP Engine", layout="wide")

# Custom architectural skin injection
st.markdown("""
    <style>
        /* Base typography setting */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Premium Canvas Layout Coloring */
        .stApp {
            background-color: #faf8f2;
        }
        
        /* Master Sidebar Custom Skin */
        section[data-testid="stSidebar"] {
            background-color: #f4efdc !important;
            border-right: 1px solid #e5dfcb;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3 {
            color: #6a0708 !important;
            font-weight: 700;
        }
        
        /* Typography overrides for premium editorial look */
        h1, h2, h3, h4, h5, h6 {
            color: #6a0708 !important;
            font-weight: 700 !important;
        }
        
        /* Clean Interface Separation Rules */
        hr {
            border-top: 1px solid #e5dfcb !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
        }
        
        /* High-Impact Interactive Elements */
        .stButton>button {
            background-color: #6a0708 !important;
            color: #f4efdc !important;
            border-radius: 6px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 0.5rem 2rem !important;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #a01a1e !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(106,7,8,0.15);
        }
    </style>
""", unsafe_allow_html=True)

# Master Header Platform Branding
st.title("OptiLot")
st.caption("Advanced Material Requirements Planning (MRP) Decision Support System")
st.markdown("---")

# ==========================================
# 2. SIDEBAR - INPUT PARAMETERS
# ==========================================
st.sidebar.header("Configuration Panel")

setup_cost = st.sidebar.number_input("Ordering / Setup Cost ($)", min_value=0.0, value=100000.0, step=500.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit / period)", min_value=0.0, value=2000.0, step=500.0)
initial_inv = st.sidebar.number_input("Initial Inventory", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time (Periods)", min_value=0, value=1, step=1)

st.sidebar.markdown("---")
st.sidebar.header("Operational Constraints")
max_capacity = st.sidebar.number_input("Maximum Warehouse Capacity (Units)", min_value=1, value=100, step=10)

# ==========================================
# HELPER FUNCTIONS (GLOBAL SCOPE & STYLING)
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
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold;' if val > max_cap else '' for val in row]
        return [''] * len(row)
    return df_mrp_transposed.style.apply(highlight_row_capacity, axis=1)

def highlight_stop(row):
    return ['background-color: #fee2e2; color: #991b1b; font-weight: bold;' if 'Stop!' in str(row['Status']) else '' for _ in row]

# ==========================================
# 3. DATA INPUT SECTION
# ==========================================
st.subheader("Data Input Management")

input_method = st.radio(
    "Select Data Input Method:", 
    ["Upload File (Excel / CSV)", "Manual Interface Input", "Use Template Dataset"]
)

df_kerja = None

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload data sheet (Supported formats: .xlsx, .xls, .csv)", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            col_periode = dapatkan_kolom_cocok(df_raw.columns, ['periode', 'mingguke', 'p', 'minggu', 'period', 'week'])
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
                st.error("❌ Gross Requirements (GR) column could not be automatically parsed.")
                
            if col_sr and col_sr in df_raw.columns:
                df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_kerja['Scheduled Receipts'] = 0
                
        except Exception as e:
            st.error(f"Failed to parse file matrix. Error: {e}")
            
elif input_method == "Manual Interface Input":
    num_periods_input = st.number_input("Planning Horizon (Periods):", min_value=1, max_value=52, value=10, step=1)
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
    
    st.markdown("##### Matrix Input Preview")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()

    # ==========================================
    # CORE ALGORITHM - MULTI METHOD MRP (UNTOUCHED LOGIC)
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

        # 1. LOT-FOR-LOT (L4L)
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = generate_poh_and_release(l4l_rec)
        c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        c_l4l_hold = sum(max(0, x) for x in l4l_poh) * hold

        # 2. LEAST UNIT COST (LUC)
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
                    status = "Stop! Cost Rises"
                    t_log.append({'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d, 'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                    break
            luc_iters.append(pd.DataFrame(t_log))
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
            else:
                pass
                
        eoq_poh, eoq_rel = generate_poh_and_release(eoq_rec)
        c_eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        c_eoq_hold = sum(max(0, x) for x in eoq_poh) * hold

        # 4. PART PERIOD BALANCING (PPB)
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
                        'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Balancing"
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
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Selected (Overshoot Closer)"
                        })
                    else:
                        t_log.append({
                            'Iteration From': f"P{idx+1}", 'To': f"P{k+1}", 'Total Units': acc_d + net_req[k], 
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': new_cum_part_period, 'Status': "Stop! Prior Step Closer"
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

    # RUN MRP ENGINE
    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    # ==========================================
    # 5. MAIN INTERFACE - PERFORMANCE TILES
    # ==========================================
    st.markdown("---")
    st.header("Multi-Method Performance Analysis")
    
    biaya_dict = {
        'Lot-for-Lot (L4L)': res['l4l']['total'], 
        'Least Unit Cost (LUC)': res['luc']['total'], 
        'Economic Order Quantity (EOQ)': res['eoq']['total'], 
        'Part Period Balancing (PPB)': res['ppb']['total']
    }
    best_method = min(biaya_dict, key=biaya_dict.get)
    
    # HTML Cards Component Rendering
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        diff_l4l = res['l4l']['total'] - biaya_dict[best_method]
        l4l_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ ${diff_l4l:,.2f} Deviation</div>" if diff_l4l > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost L4L</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>${res['l4l']['total']:,.2f}</div>
                        {l4l_sub}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        luc_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ ${diff_luc:,.2f} Deviation</div>" if diff_luc > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost LUC</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>${res['luc']['total']:,.2f}</div>
                        {luc_sub}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        eoq_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ ${diff_eoq:,.2f} Deviation</div>" if diff_eoq > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost EOQ</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>${res['eoq']['total']:,.2f}</div>
                        {eoq_sub}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        ppb_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ ${diff_ppb:,.2f} Deviation</div>" if diff_ppb > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost PPB</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>${res['ppb']['total']:,.2f}</div>
                        {ppb_sub}</div>""", unsafe_allow_html=True)

    st.info(f"💡 **Operational Recommendation:** **{best_method}** presents the most cost-efficient tactical approach for this demand pattern.")

    # ==========================================
    # 6. TABS ARTIFACTS VIEW
    # ==========================================
    tab_grafik, t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["📉 Charts & Sensitivity", "📋 Lot-for-Lot (L4L)", "🔍 Least Unit Cost (LUC)", "🎯 Economic Order Quantity (EOQ)", "⚖️ Part Period Balancing (PPB)"])

    with tab_grafik:
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("### Cost Breakdown Framework ($)")
            fig, ax = plt.subplots(figsize=(6, 4))
            fig.patch.set_facecolor('#faf8f2')
            ax.set_facecolor('#faf8f2')
            ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#a01a1e', '#415a77', '#2a9d8f', '#e9c46a'])
            plt.xticks(rotation=15, ha='right')
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            st.pyplot(fig)
        with cg2:
            st.markdown("### Demand Sensitivity Simulation")
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
            fig2.patch.set_facecolor('#faf8f2')
            ax2.set_facecolor('#faf8f2')
            ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#a01a1e')
            ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#415a77')
            ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#2a9d8f')
            ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#e9c46a')
            ax2.set_ylabel('Total Operation Cost ($)')
            ax2.grid(True,
