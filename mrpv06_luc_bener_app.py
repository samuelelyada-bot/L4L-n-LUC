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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
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

# Tooltip Descriptions (Help Menu Text)
l4l_help = "LOT-FOR-LOT (L4L): Orders exactly what is needed each period, minimizing holding costs but maximizing setup frequency."
luc_help = "LEAST UNIT COST (LUC): Groups successive periods as long as the average cost per unit keeps decreasing."
eoq_help = "ECONOMIC ORDER QUANTITY (EOQ): Balances setup and holding costs using average gross demand to find the optimal fixed order size."
ppb_help = "PART PERIOD BALANCING (PPB): A dynamic technique that looks for an order quantity where the total holding cost matches the setup cost as closely as possible."

# Header Help Icons Grid
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
# 2. SIDEBAR - INPUT PARAMETERS
# ==========================================
st.sidebar.header("Configuration Panel")

setup_cost = st.sidebar.number_input("Ordering / Setup Cost", min_value=0.0, value=100.0, step=10.0)
holding_cost = st.sidebar.number_input("Holding Cost (per unit / period)", min_value=0.0, value=2.0, step=0.5)
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

def highlight_status_iterasi(df):
    """
    FIXED BUG 3: Ditambahkan 'if i > 0' guard untuk mencegah indeks -1 (baris terakhir) 
    ter-override menjadi warna hijau jika iterasi hanya berjalan 1 baris lalu 'Stop'.
    """
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    n_rows = len(df)
    
    if n_rows == 0:
        return style_df
        
    stop_found = False
    for i in range(n_rows):
        status_val = str(df.iloc[i]['Status'])
        
        if 'Stop' in status_val:
            style_df.iloc[i] = 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
            stop_found = True
            if i > 0: # BUG 3 FIX TRAPPED HERE
                style_df.iloc[i-1] = 'background-color: #e8f5e9; color: #1b5e20; font-weight: bold;'
                
    if not stop_found:
        style_df.iloc[n_rows - 1] = 'background-color: #e8f5e9; color: #1b5e20; font-weight: bold;'
                
    return style_df

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
                df_kerja['Period'] = df_raw[col_periode].astype(str).str.upper()
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
    period_labels = df_kerja['Period'].astype(str).str.upper().tolist()
    
    st.markdown("##### Matrix Input Preview")
    df_preview_transposed = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    
    df_edited_preview = st.data_editor(df_preview_transposed, use_container_width=True)
    gross_req = df_edited_preview.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited_preview.loc['Scheduled Receipts'].astype(int).tolist()

    # ==========================================
    # CORE ALGORITHM - MULTI METHOD MRP 
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
                
                p_label = ", ".join([f"P{m+1}" for m in range(idx, k+1)])
                
                if uc <= min_uc:
                    min_uc, best_k = uc, k
                    status = "Feasible"
                    t_log.append({'Period': p_label, 'Total Units': acc_d, 'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                else:
                    status = "Stop (Prev Closer)"
                    t_log.append({'Period': p_label, 'Total Units': acc_d, 'Setup Cost': setup, 'Holding Cost': acc_h, 'Total Cost': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
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
                p_label = ", ".join([f"P{m+1}" for m in range(idx, k+1)])
                
                if new_cum_part_period <= epp_limit:
                    acc_d += net_req[k]
                    cum_part_period = new_cum_part_period
                    best_k = k
                    t_log.append({
                        'Period': p_label, 'Total Units': acc_d, 
                        'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Feasible"
                    })
                    # FIXED BUG 2: Jika sudah di penghujung periode terakhir dan masih 'Feasible', loop luar akan aman mengeksekusi data tanpa gantung.
                else:
                    dist_sebelum = abs(cum_part_period - epp_limit)
                    dist_sesudah = abs(new_cum_part_period - epp_limit)
                    
                    if dist_sesudah < dist_sebelum and cum_part_period > 0:
                        # Kasus di mana overshoot lebih mendekati target EPP limit
                        # FIXED BUG 1: Simpan nilai snapshot penambahan acc_d lama ke variabel terpisah agar baris stop k+1 tidak double counting
                        prev_acc_d = acc_d
                        acc_d += net_req[k]
                        cum_part_period = new_cum_part_period
                        best_k = k
                        t_log.append({
                            'Period': p_label, 'Total Units': acc_d, 
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period, 'Status': "Feasible"
                        })
                        if k + 1 < n:
                            p_label_next = ", ".join([f"P{m+1}" for m in range(idx, k+2)])
                            next_part = net_req[k+1] * ((k+1) - idx)
                            t_log.append({
                                'Period': p_label_next, 'Total Units': acc_d + net_req[k+1], 
                                'EPP Limit': epp_limit, 'Cumulative Part-Period': cum_part_period + next_part, 'Status': "Stop! Exceeds EPP Limit ⚠️"
                            })
                    else:
                        # Kasus di mana akumulasi sebelum overshoot yang lebih mendekati target
                        t_log.append({
                            'Period': p_label, 'Total Units': acc_d + net_req[k], 
                            'EPP Limit': epp_limit, 'Cumulative Part-Period': new_cum_part_period, 'Status': "Stop! Exceeds EPP Limit ⚠️"
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
    
    biaya_dict = {
        'Lot-for-Lot (L4L)': res['l4l']['total'], 
        'Least Unit Cost (LUC)': res['luc']['total'], 
        'Economic Order Quantity (EOQ)': res['eoq']['total'], 
        'Part Period Balancing (PPB)': res['ppb']['total']
    }
    best_method = min(biaya_dict, key=biaya_dict.get)

    # ==========================================
    # 4. MAIN INTERFACE - TABS FOR STRATEGIES
    # ==========================================
    st.markdown("---")
    st.header("Material Requirements Planning Matrix Breakdown")
    
    t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["📋 Lot-for-Lot (L4L)", "🔍 Least Unit Cost (LUC)", "🎯 Economic Order Quantity (EOQ)", "⚖️ Part Period Balancing (PPB)"])

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
            st.error(f"⚠️ **Capacity Violation Threshold Raised:** Inventory accumulation via {nama_metode} breaches physical facility space constraints ({max_cap} units).")

    with t_l4l:
        st.subheader("MRP Standard Grid Matrix — Lot-for-Lot")
        tampilkan_tabel_mrp("L4L", res['l4l'], max_capacity)

    with t_luc:
        st.subheader("Least Unit Cost Operational Evaluation Logs")
        format_luc = {'Setup Cost': '{:.2f}', 'Holding Cost': '{:.2f}', 'Total Cost': '{:.2f}', 'LUC (Cost/Unit)': '{:.4f}'}
        for idx, df_iter in enumerate(res['luc']['iters']):
            with st.expander(f"Order Cycle Discovery Step {idx+1}"):
                styled_df = df_iter.style.apply(highlight_status_iterasi, axis=None).format(format_luc)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        tampilkan_tabel_mrp("LUC", res['luc'], max_capacity)

    with t_eoq:
        st.subheader("Economic Order Quantity Model Assessment")
        with st.expander("Formula Calculation & Parameter Trace"):
            total_gross_req = sum(gross_req)
            n_periode = len(gross_req)
            avg_demand_calc = res['eoq']['avg_demand_gross']
            
            st.markdown("#### Operational Sizing Calculus Steps")
            st.markdown("**1. Data Discovery Parameters:**")
            st.markdown(f"""
            * Discrete Timeline Profile: `{gross_req}`
            * Total Gross Requirements = `{total_gross_req}` units
            * Planning Horizon Length ($n$) = `{n_periode}` periods
            """)
            
            st.markdown("**2. Periodic Average Target Rate ($D$):**")
            st.markdown(f"$$D = \\frac{{{total_gross_req}}}{{{n_periode}}} = {avg_demand_calc:.4f} \\text{{ units/period}}$$")
            
            nilai_atas = 2 * avg_demand_calc * setup_cost
            nilai_bagi = nilai_atas / holding_cost
            eoq_final_raw = math.sqrt(nilai_bagi)
            
            st.markdown("**3. Constant Value Synthesis:**")
            st.markdown(f"$$EOQ = \\sqrt{{\\frac{{2 \\times D \\times \\text{{Setup Cost}}}}{{\\text{{Holding Cost}}}}}} = {eoq_final_raw:.4f}$$")
            st.markdown(f"* Rounded up to practical unit lot size: **`{res['eoq']['size']}` units**.")
            
        st.info(f"💡 **Fixed Lot Control Rule:** Baseline order scale for the EOQ profile is locked at **{res['eoq']['size']} units** per cycle.")
        tampilkan_tabel_mrp("EOQ", res['eoq'], max_capacity)

    with t_ppb:
        st.subheader("Part Period Balancing Operational Evaluation Logs")
        format_ppb = {'EPP Limit': '{:.2f}', 'Cumulative Part-Period': '{:.2f}'}
        for idx, df_iter in enumerate(res['ppb']['iters']):
            with st.expander(f"Order Window Evaluation Strategy {idx+1}"):
                styled_df = df_iter.style.apply(highlight_status_iterasi, axis=None).format(format_ppb)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        tampilkan_tabel_mrp("PPB", res['ppb'], max_capacity)

    # ==========================================
    # 5. PERFORMANCE ANALYSIS & CHARTS
    # ==========================================
    st.markdown("---")
    st.header("Multi-Method Performance Analysis")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        diff_l4l = res['l4l']['total'] - biaya_dict[best_method]
        l4l_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ {diff_l4l:,.2f} Deviation</div>" if diff_l4l > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost L4L</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>{res['l4l']['total']:,.2f}</div>
                        {l4l_sub}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        luc_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ {diff_luc:,.2f} Deviation</div>" if diff_luc > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost LUC</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>{res['luc']['total']:,.2f}</div>
                        {luc_sub}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        eoq_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ {diff_eoq:,.2f} Deviation</div>" if diff_eoq > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost EOQ</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>{res['eoq']['total']:,.2f}</div>
                        {eoq_sub}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        ppb_sub = f"<div style='color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px;'>+ {diff_ppb:,.2f} Deviation</div>" if diff_ppb > 0 else "<div style='color: #15803d; font-size: 13px; font-weight: 600; margin-top: 4px;'>🏆 Optimal Strategy</div>"
        st.markdown(f"""<div style='background-color: #f4efdc; padding: 16px; border-radius: 6px; border-top: 4px solid #6a0708;'>
                        <div style='color: #4a4a4a; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Total Cost PPB</div>
                        <div style='font-size: 22px; font-weight: 700; color: #6a0708; margin-top: 4px;'>{res['ppb']['total']:,.2f}</div>
                        {ppb_sub}</div>""", unsafe_allow_html=True)

    st.info(f"💡 **Operational Recommendation:** **{best_method}** presents the most cost-efficient tactical approach for this demand pattern.")

    # Charts Area
    cg1, cg2 = st.columns(2)
    with cg1:
        st.markdown("### Cost Breakdown Framework")
        fig, ax = plt.subplots(figsize=(6, 4.5))
        fig.patch.set_facecolor('#faf8f2')
        ax.set_facecolor('#faf8f2')
        
        bars = ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#a01a1e', '#415a77', '#2a9d8f', '#e9c46a'])
        
        plt.xticks(rotation=20, fontsize=8, ha='right')
        ax.set_ylabel('Total Cost', fontsize=9, fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        
    with cg2:
        st.markdown("### Demand Sensitivity Simulation (-30% to +30%)")
        
        scale_factors = np.arange(0.70, 1.35, 0.05)
        s_l4l, s_luc, s_eoq, s_ppb, labels_pct = [], [], [], [], []
        
        for f in scale_factors:
            pct_val = int(round((f - 1) * 100))
            if pct_val > 30:  # Hard limit di 30%
                continue
            sim_demand = [max(1, int(d * f)) for d in gross_req]
            s_res = calculate_multi_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
            s_l4l.append(s_res['l4l']['total'])
            s_luc.append(s_res['luc']['total'])
            s_eoq.append(s_res['eoq']['total'])
            s_ppb.append(s_res['ppb']['total'])
            labels_pct.append(f"{pct_val}%" if pct_val <= 0 else f"+{pct_val}%")
        
        fig2, ax2 = plt.subplots(figsize=(7, 4.5))
        fig2.patch.set_facecolor('#faf8f2')
        ax2.set_facecolor('#faf8f2')
        ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#a01a1e')
        ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#415a77')
        ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#2a9d8f')
        ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#e9c46a')
        
        ax2.set_ylabel('Total Operation Cost', fontsize=9, fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.4)
        ax2.legend(fontsize=8)
        
        plt.xticks(rotation=0, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)

    # ==========================================
    # 6. EXPORT DATA LAYER
    # ==========================================
    st.markdown("---")
    st.subheader("Management Reporting Layer")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Baseline Requirements")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="L4L Model")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="LUC Model")
        pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="EOQ Model")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="PPB Model")
    
    buffer.seek(0)
        
    st.download_button(
        label="Download Analytical Performance Report (Excel)", 
        data=buffer, 
        file_name="OptiLot_MRP_Performance_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("💡 Establish baseline transaction vectors above to trigger automated matrix computations.")
