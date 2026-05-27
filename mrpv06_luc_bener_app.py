import streamlit as st
import pandas as pd
import numpy as np
import math
from io import BytesIO

# ==========================================
# 1. PAGE CONFIGURATION & MODERN THEME INJECTION
# ==========================================
st.set_page_config(page_title="OptiLot — Advanced MRP Engine", layout="wide")

# Custom structural and stylistic skin injection
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
        
        /* Structured Data Representation Containers */
        div[data-testid="stMetricValue"] {
            color: #6a0708 !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #4a4a4a !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
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
        
        /* Clean Interface Separation Rules */
        hr {
            border-top: 1px solid #e5dfcb !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Master Header Platform Branding
st.title("OptiLot")
st.caption("Advanced Material Requirements Planning (MRP) Decision Support System")

l4l_help = "LOT-FOR-LOT (L4L): Orders exactly what is needed each period, minimizing holding costs but maximizing setup frequency."
luc_help = "LEAST UNIT COST (LUC): Groups successive periods as long as the average cost per unit keeps decreasing."
eoq_help = "ECONOMIC ORDER QUANTITY (EOQ): Balances setup and holding costs using average gross demand to find the optimal fixed order size."
ppb_help = "PART PERIOD BALANCING (PPB): A dynamic technique that looks for an order quantity where the total holding cost matches the setup cost as closely as possible."

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
setup_cost = st.sidebar.number_input("Ordering / Setup Cost ($)", min_value=0.0, value=100000.0, step=5000.0)
holding_cost = st.sidebar.number_input("Holding Cost (H) (per unit/period)", min_value=0.0, value=2000.0, step=500.0)
initial_inventory = st.sidebar.number_input("Initial Inventory", min_value=0, value=30, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=0, step=1)
lead_time = st.sidebar.number_input("Lead Time (Periods)", min_value=0, value=1, step=1)

# ==========================================
# HELPER FUNCTIONS (UNTOUCHED)
# ==========================================
def dapatkan_kolom_cocok(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

def format_lokal_id(number, is_decimal=False):
    """Format numbers using standard notation rules."""
    if is_decimal:
        string_num = f"{number:f}".rstrip('0').rstrip('.')
        if '.' in string_num:
            integer_part, decimal_part = string_num.split('.')
            integer_part = f"{int(integer_part):,}"
            return f"{integer_part}.{decimal_part}"
        return f"{int(string_num):,}"
    return f"{int(round(number)):,}"

def highlight_luc_warning(row):
    if row['Is_Higher_Internal']:
        return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(row)
    return [''] * len(row)

def highlight_ppb_stop(row):
    if 'Stop' in str(row['Status']):
        return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(row)
    return [''] * len(row)

def calculate_net_requirements(gross_req, sched_rec, init_inv, ss):
    """Rolling NR calculation: NR_t = max(0, GR_t + SS - (OHI_{t-1} + SR_t))."""
    net_req_list = []
    projected_inv = init_inv
    for k in range(len(gross_req)):
        nr = max(0, gross_req[k] + ss - (projected_inv + sched_rec[k]))
        net_req_list.append(nr)
        projected_inv = projected_inv + nr + sched_rec[k] - gross_req[k]
    return net_req_list

def compute_luc_holding_cost(net_req_slice):
    holding = 0.0
    for k in range(len(net_req_slice)):
        ohi_akhir_k = sum(net_req_slice[k + 1:])
        holding += ohi_akhir_k * holding_cost
    return holding

def generate_poh_and_release(rec_lot, demands, s_receipts, init_inv, lt):
    n = len(demands)
    poh, r_inv = [], init_inv
    for i in range(n):
        r_inv += s_receipts[i] + rec_lot[i] - demands[i]
        poh.append(r_inv)

    rel_lot = [0] * n
    for i in range(n):
        if rec_lot[i] > 0:
            target = i - lt
            if target >= 0:
                rel_lot[target] += rec_lot[i]
            else:
                rel_lot[0] += rec_lot[i]
    return poh, rel_lot

# ==========================================
# 3. DATA INPUT SECTION
# ==========================================
st.subheader("📦 Data Input Management")
input_method = st.radio("Data Input Method:", ["Upload File", "Manual Input", "Template Data"], horizontal=True)

df_kerja = None

if input_method == "Upload File":
    uploaded_file = st.file_uploader("Choose file (xlsx, csv)", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            col_periode = dapatkan_kolom_cocok(df_raw.columns, ['periode', 'minggu', 'p', 'period', 'week'])
            col_gr = dapatkan_kolom_cocok(df_raw.columns, ['gr', 'grossrequirement', 'kebutuhankotor', 'grossrequirements'])
            col_sr = dapatkan_kolom_cocok(df_raw.columns, ['sr', 'scheduledreceipt', 'penerimaanterjadwal', 'scheduledreceipts'])
            df_kerja = pd.DataFrame()
            df_kerja['Period'] = df_raw[col_periode].astype(str) if col_periode else [f"P{i+1}" for i in range(len(df_raw))]
            df_kerja['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int) if col_gr else 0
            df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int) if col_sr else 0
        except:
            st.error("Error reading file. Please check the format.")

elif input_method == "Manual Input":
    num_periods_input = st.number_input("Number of Periods:", min_value=1, max_value=52, value=8)
    init_data = {
        'Period': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': [0] * num_periods_input,
        'Scheduled Receipts': [0] * num_periods_input,
    }
    df_kerja = st.data_editor(pd.DataFrame(init_data), use_container_width=True, hide_index=True)

else:
    df_kerja = pd.DataFrame({
        'Period': [f"P{i}" for i in range(1, 9)],
        'Gross Requirements': [30, 40, 20, 70, 40, 10, 30, 60],
        'Scheduled Receipts': [0, 10, 0, 0, 20, 0, 0, 0],
    })

# ==========================================
# 4. CALCULATION ENGINES (ALGORITHM PROTECTED)
# ==========================================
if df_kerja is not None:
    gross_req = df_kerja['Gross Requirements'].tolist()
    sched_rec = df_kerja['Scheduled Receipts'].tolist()
    period_labels = df_kerja['Period'].tolist()
    num_periods = len(gross_req)
    net_req = calculate_net_requirements(gross_req, sched_rec, initial_inventory, safety_stock)

    st.markdown("##### Input Matrix Overview")
    st.dataframe(
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec}, index=period_labels).T,
        use_container_width=True
    )

    # L4L Engine Execution
    l4l_rec = list(net_req)
    l4l_poh, l4l_rel = generate_poh_and_release(l4l_rec, gross_req, sched_rec, initial_inventory, lead_time)
    total_l4l = (sum(1 for x in l4l_rec if x > 0) * setup_cost) + (sum(l4l_poh) * holding_cost)

    # LUC Engine Execution
    luc_rec = [0] * num_periods
    all_luc_iterations = []
    i = 0
    while i < num_periods:
        if net_req[i] <= 0:
            i += 1
            continue

        best_lot, prev_unit_cost = None, None

        for j in range(i, num_periods):
            nr_slice = net_req[i:j + 1]
            current_lot = sum(nr_slice)
            h_cost = compute_luc_holding_cost(nr_slice)
            total_c = setup_cost + h_cost
            unit_cost = total_c / current_lot if current_lot > 0 else float('inf')
            is_higher = (prev_unit_cost is not None and unit_cost > prev_unit_cost)

            range_label = f"P{i+1}" if i == j else ", ".join(f"P{x}" for x in range(i + 1, j + 2))
            display_label = f"⚠️ {range_label}" if is_higher else range_label

            all_luc_iterations.append({
                "Period": display_label,
                "Lot Size": int(current_lot),
                "Total Cost": format_lokal_id(total_c),
                "Unit Cost": format_lokal_id(round(unit_cost, 2), is_decimal=True),
                "Is_Higher_Internal": is_higher,
            })

            if not is_higher:
                best_lot = {"Lot Size": current_lot, "End_Idx": j}
                prev_unit_cost = unit_cost
            else:
                break

        if best_lot:
            luc_rec[i] = best_lot["Lot Size"]
            i = best_lot["End_Idx"] + 1
        else:
            i += 1

    luc_poh, luc_rel = generate_poh_and_release(luc_rec, gross_req, sched_rec, initial_inventory, lead_time)
    total_luc = (sum(1 for x in luc_rec if x > 0) * setup_cost) + (sum(luc_poh) * holding_cost)

    # EOQ Engine Execution
    avg_d = np.mean(gross_req)
    if holding_cost > 0 and avg_d > 0:
        eoq_size = math.ceil(math.sqrt((2 * avg_d * setup_cost) / holding_cost))
    else:
        eoq_size = int(sum(gross_req))

    eoq_rec, rem_stok = [0] * num_periods, 0
    for idx in range(num_periods):
        if net_req[idx] > 0:
            if rem_stok < net_req[idx]:
                needed = net_req[idx] - rem_stok
                lots = math.ceil(needed / eoq_size) if eoq_size > 0 else 1
                eoq_rec[idx] = lots * eoq_size
                rem_stok = (eoq_rec[idx] + rem_stok) - net_req[idx]
            else:
                rem_stok -= net_req[idx]

    eoq_poh, eoq_rel = generate_poh_and_release(eoq_rec, gross_req, sched_rec, initial_inventory, lead_time)
    total_eoq = (sum(1 for x in eoq_rec if x > 0) * setup_cost) + (sum(eoq_poh) * holding_cost)

    # PPB Engine Execution
    ppb_rec = [0] * num_periods
    all_ppb_iterations = []
    epp_limit = setup_cost / holding_cost if holding_cost > 0 else float('inf')
    
    idx_p = 0
    while idx_p < num_periods:
        if net_req[idx_p] <= 0:
            idx_p += 1
            continue
            
        best_k = idx_p
        cum_part_period = 0
        accumulated_d = 0
        t_log = []
        
        for k in range(idx_p, num_periods):
            part_period_k = net_req[k] * (k - idx_p)
            new_cum_part_period = cum_part_period + part_period_k
            
            range_label = f"P{idx_p+1}" if idx_p == k else ", ".join(f"P{x}" for x in range(idx_p + 1, k + 2))
            
            if new_cum_part_period <= epp_limit:
                accumulated_d += net_req[k]
                cum_part_period = new_cum_part_period
                best_k = k
                t_log.append({
                    'Period': range_label,
                    'Accumulated Unit': int(accumulated_d),
                    'EPP Limit': round(epp_limit, 2),
                    'Cumulative Part-Period': round(cum_part_period, 2),
                    'Status': 'Feasible',
                    'Is_Stop_Internal': False
                })
            else:
                distance_before = abs(cum_part_period - epp_limit)
                distance_after = abs(new_cum_part_period - epp_limit)
                
                if distance_after < distance_before:
                    accumulated_d += net_req[k]
                    cum_part_period = new_cum_part_period
                    best_k = k
                    t_log.append({
                        'Period': f"⚠️ {range_label}",
                        'Accumulated Unit': int(accumulated_d),
                        'EPP Limit': round(epp_limit, 2),
                        'Cumulative Part-Period': round(cum_part_period, 2),
                        'Status': 'Closer (Overshoot Chosen)',
                        'Is_Stop_Internal': True
                    })
                else:
                    t_log.append({
                        'Period': f"⚠️ {range_label}",
                        'Accumulated Unit': int(accumulated_d + net_req[k]),
                        'EPP Limit': round(epp_limit, 2),
                        'Cumulative Part-Period': round(new_cum_part_period, 2),
                        'Status': 'Stop (Previous Closer)',
                        'Is_Stop_Internal': True
                    })
                break
                
        all_ppb_iterations.append(pd.DataFrame(t_log))
        ppb_rec[idx_p] = sum(net_req[idx_p:best_k+1])
        idx_p = best_k + 1
        
    ppb_poh, ppb_rel = generate_poh_and_release(ppb_rec, gross_req, sched_rec, initial_inventory, lead_time)
    total_ppb = (sum(1 for x in ppb_rec if x > 0) * setup_cost) + (sum(ppb_poh) * holding_cost)

    # ==========================================
    # 5. DETAILED ANALYTICS VIEWPORTS (TABS)
    # ==========================================
    st.markdown("---")
    st.subheader("📊 Lot-Sizing Framework Matrices")
    t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["Lot-for-Lot (L4L)", "Least Unit Cost (LUC)", "Economic Order Quantity (EOQ)", "Part Period Balancing (PPB)"])

    def render_mrp(poh, rec, rel):
        df = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': poh,
            'Net Requirements': net_req,
            'Planned Order Receipts': rec,
            'Planned Order Releases': rel,
        }, index=period_labels).T
        st.dataframe(df, use_container_width=True)

    with t_l4l:
        st.markdown("##### Material Balance Table — Lot-for-Lot")
        render_mrp(l4l_poh, l4l_rec, l4l_rel)
        st.markdown(f"**Total Cost Realization (L4L):** `${format_lokal_id(total_l4l)}`")

    with t_luc:
        st.markdown("##### Unit Cost Optimization Iteration Trace")
        df_luc_view = pd.DataFrame(all_luc_iterations)
        st.dataframe(
            df_luc_view.style.apply(highlight_luc_warning, axis=1),
            use_container_width=True,
            hide_index=True,
            column_order=["Period", "Lot Size", "Total Cost", "Unit Cost"],
        )
        st.markdown("##### Material Balance Table — Least Unit Cost")
        render_mrp(luc_poh, luc_rec, luc_rel)
        st.markdown(f"**Total Cost Realization (LUC):** `${format_lokal_id(total_luc)}`")

    with t_eoq:
        st.markdown("##### System Constants")
        st.markdown(f"* Average Gross Demand: `{avg_d:.2f}` units/period | Calculated Fixed Economic Order Quantity Size: **{eoq_size} units**")
        st.markdown("##### Material Balance Table — Economic Order Quantity")
        render_mrp(eoq_poh, eoq_rec, eoq_rel)
        st.markdown(f"**Total Cost Realization (EOQ):** `${format_lokal_id(total_eoq)}`")

    with t_ppb:
        st.markdown("##### Part Period Balancing System Step-Logs")
        for idx, df_iter in enumerate(all_ppb_iterations):
            with st.expander(f"Order Window Evaluation Strategy {idx+1}"):
                st.dataframe(
                    df_iter.style.apply(highlight_ppb_stop, axis=1),
                    use_container_width=True,
                    hide_index=True,
                    column_order=["Period", "Accumulated Unit", "EPP Limit", "Cumulative Part-Period", "Status"]
                )
        st.markdown("##### Material Balance Table — Part Period Balancing")
        render_mrp(ppb_poh, ppb_rec, ppb_rel)
        st.markdown(f"**Total Cost Realization (PPB):** `${format_lokal_id(total_ppb)}`")

    # ==========================================
    # 6. PERFORMANCE METRICS COMPARISON
    # ==========================================
    st.markdown("---")
    st.subheader("📈 Efficiency Metrics Comparison")
    biaya_dict = {'L4L': total_l4l, 'LUC': total_luc, 'EOQ': total_eoq, 'PPB': total_ppb}
    best_m = min(biaya_dict, key=biaya_dict.get)
    cols = st.columns(4)
    for idx, (name, val) in enumerate(biaya_dict.items()):
        cols[idx].metric(
            f"Total Strategy Cost: {name}",
            f"${format_lokal_id(val)}",
            delta="Optimal Strategy" if name == best_m else None,
        )

    # ==========================================
    # 7. EXPORT DATA LAYER
    # ==========================================
    st.markdown("---")
    st.subheader("💾 Management Reporting")
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        pd.DataFrame(
            {'GR': gross_req, 'Net': net_req}, index=period_labels
        ).T.to_excel(writer, sheet_name="Base_Demand")
        pd.DataFrame(
            {'L4L': l4l_rec, 'LUC': luc_rec, 'EOQ': eoq_rec, 'PPB': ppb_rec}, index=period_labels
        ).T.to_excel(writer, sheet_name="Calculated_Lotting_Strategy")
    
    st.download_button(
        label="Download Analytical Performance Report (Excel)",
        data=excel_buffer.getvalue(),
        file_name="MRP_Strategy_Report.xlsx",
    )
