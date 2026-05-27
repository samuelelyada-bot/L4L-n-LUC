import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import math
import io

# ==========================================
# 1. KONFIGURASI HALAMAN & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="MRP Planner · Multi-Metode",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Reset & Base */
    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .stApp {
        background-color: #0f1117;
        color: #e8eaf0;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161b27 !important;
        border-right: 1px solid #252d3d;
    }
    section[data-testid="stSidebar"] * {
        color: #c8cfe0 !important;
    }
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stSelectbox label {
        color: #8892a4 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }
    
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #1a2236 0%, #0f1117 60%);
        border: 1px solid #252d3d;
        border-radius: 16px;
        padding: 32px 40px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(99,179,237,0.06) 0%, transparent 70%);
        pointer-events: none;
    }
    .main-header h1 {
        font-size: 28px;
        font-weight: 700;
        color: #e8eaf0;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
    }
    .main-header p {
        font-size: 14px;
        color: #5c6b82;
        margin: 0;
        font-weight: 400;
    }
    .header-badge {
        display: inline-block;
        background: rgba(99,179,237,0.1);
        color: #63b3ed;
        border: 1px solid rgba(99,179,237,0.25);
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    
    /* Section headers */
    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #5c6b82;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e2535;
    }
    
    /* Metric cards */
    .metric-card {
        background: #161b27;
        border: 1px solid #252d3d;
        border-radius: 12px;
        padding: 20px;
        transition: border-color 0.2s;
    }
    .metric-card:hover {
        border-color: #3a4a66;
    }
    .metric-card.winner {
        border-color: rgba(72,187,120,0.4);
        background: linear-gradient(135deg, #161b27 0%, #0d1f18 100%);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        color: #5c6b82;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-method {
        font-size: 13px;
        font-weight: 500;
        color: #8892a4;
        margin-bottom: 4px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 500;
        color: #e8eaf0;
        letter-spacing: -0.02em;
    }
    .metric-badge-win {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(72,187,120,0.12);
        color: #48bb78;
        border: 1px solid rgba(72,187,120,0.25);
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
        margin-top: 8px;
    }
    .metric-badge-diff {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(245,101,101,0.08);
        color: #fc8181;
        border: 1px solid rgba(245,101,101,0.2);
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
        margin-top: 8px;
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Recommendation banner */
    .rec-banner {
        background: linear-gradient(135deg, rgba(72,187,120,0.08) 0%, rgba(99,179,237,0.05) 100%);
        border: 1px solid rgba(72,187,120,0.2);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .rec-banner-icon { font-size: 20px; }
    .rec-banner-text {
        font-size: 14px;
        color: #a0aec0;
        line-height: 1.5;
    }
    .rec-banner-text strong { color: #48bb78; }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Info / alert boxes */
    .info-box {
        background: rgba(99,179,237,0.07);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 10px;
        padding: 14px 18px;
        font-size: 13px;
        color: #90cdf4;
        margin: 12px 0;
    }
    .warn-box {
        background: rgba(245,101,101,0.07);
        border: 1px solid rgba(245,101,101,0.2);
        border-radius: 10px;
        padding: 14px 18px;
        font-size: 13px;
        color: #fc8181;
        margin: 12px 0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #161b27;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #252d3d;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        color: #5c6b82;
        font-size: 13px;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #1e2535 !important;
        color: #e8eaf0 !important;
    }
    
    /* Divider */
    hr {
        border-color: #1e2535;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #161b27 !important;
        border: 1px solid #252d3d !important;
        border-radius: 8px !important;
        color: #8892a4 !important;
        font-size: 13px !important;
    }
    
    /* Iteration table header */
    .iter-header {
        font-size: 12px;
        font-weight: 600;
        color: #5c6b82;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 8px 0;
        border-bottom: 1px solid #1e2535;
        margin-bottom: 12px;
    }

    /* EOQ formula display */
    .formula-box {
        background: #161b27;
        border: 1px solid #252d3d;
        border-radius: 10px;
        padding: 20px 24px;
        margin: 12px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        color: #90cdf4;
        line-height: 2;
    }
    .formula-step {
        color: #5c6b82;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-family: 'Space Grotesk', sans-serif;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. HEADER
# ==========================================
st.markdown("""
<div class="main-header">
    <div class="header-badge">DSS · Decision Support System</div>
    <h1>📦 MRP Planner · Multi-Metode</h1>
    <p>Perencanaan Kebutuhan Material — Lot-for-Lot · Least Unit Cost · EOQ · Part Period Balancing</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 3. SIDEBAR - INPUT PARAMETER
# ==========================================
st.sidebar.markdown("""
<div style='padding: 4px 0 16px 0;'>
    <div style='font-size:16px; font-weight:700; color:#e8eaf0; letter-spacing:-0.01em;'>Parameter MRP</div>
    <div style='font-size:11px; color:#3a4a66; margin-top:2px;'>Konfigurasi biaya & operasional</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("**💰 Biaya**")
setup_cost   = st.sidebar.number_input("Ordering / Setup Cost (Rp)", min_value=0.0, value=100000.0, step=500.0)
holding_cost = st.sidebar.number_input("Holding Cost (Rp/unit/periode)", min_value=0.0, value=2000.0, step=100.0)

st.sidebar.markdown("---")
st.sidebar.markdown("**📦 Inventori**")
initial_inv  = st.sidebar.number_input("Persediaan Awal (unit)", min_value=0, value=35, step=5)
safety_stock = st.sidebar.number_input("Safety Stock (unit)", min_value=0, value=0, step=1)
lead_time    = st.sidebar.number_input("Lead Time (periode)", min_value=0, value=1, step=1)

st.sidebar.markdown("---")
st.sidebar.markdown("**🏬 Kapasitas Gudang**")
max_capacity = st.sidebar.number_input("Kapasitas Maks. Gudang (unit)", min_value=1, value=500, step=10)


# ==========================================
# 4. INPUT DATA
# ==========================================
st.markdown('<div class="section-title">Data Permintaan & Penerimaan Terjadwal</div>', unsafe_allow_html=True)

input_method = st.radio(
    "Sumber data:",
    ["Upload File (Excel / CSV)", "Input Manual", "Gunakan Data Contoh"],
    horizontal=True
)

df_kerja = None

def dapatkan_kolom_cocok(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_","").replace(" ","")
        if col_clean in targets:
            return col
    return None

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file (.xlsx / .xls / .csv)", type=["csv","xlsx","xls"])
    if uploaded_file is not None:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            col_periode = dapatkan_kolom_cocok(df_raw.columns, ['periode','mingguke','p','minggu'])
            col_gr = dapatkan_kolom_cocok(df_raw.columns, ['gr','grossrequirement','grossrequirements','kebutuhankotor'])
            col_sr = dapatkan_kolom_cocok(df_raw.columns, ['sr','scheduledreceipt','scheduledreceipts','penerimaanterjadwal'])
            df_kerja = pd.DataFrame()
            df_kerja['Periode'] = df_raw[col_periode].astype(str) if col_periode else [f"P{i+1}" for i in range(len(df_raw))]
            if col_gr:
                df_kerja['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int)
            else:
                st.error("❌ Kolom Gross Requirements tidak terdeteksi.")
            df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int) if col_sr else 0
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

elif input_method == "Input Manual":
    num_p = st.number_input("Jumlah Periode:", min_value=1, max_value=52, value=10, step=1)
    default_gr = [35, 30, 40, 0, 10, 40, 30, 0, 30, 55]
    init_data = {
        'Periode':             [f"P{i+1}" for i in range(num_p)],
        'Gross Requirements':  default_gr[:num_p] if num_p <= 10 else default_gr + [0]*(num_p-10),
        'Scheduled Receipts':  [0]*num_p
    }
    df_kerja = st.data_editor(pd.DataFrame(init_data), use_container_width=True, hide_index=True)

else:
    df_kerja = pd.DataFrame({
        'Periode':            [f"P{i}" for i in range(1,11)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55],
        'Scheduled Receipts': [0]*10
    })

# ==========================================
# 5. CORE LOGIC
# ==========================================
if df_kerja is not None and not df_kerja.empty:
    gross_req    = df_kerja['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec    = df_kerja['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_kerja['Periode'].astype(str).tolist()

    st.markdown("---")
    st.markdown('<div class="section-title">Preview Data Aktif</div>', unsafe_allow_html=True)
    df_preview = pd.DataFrame({
        'Gross Requirements': gross_req,
        'Scheduled Receipts': sched_rec
    }, index=period_labels).T
    df_edited = st.data_editor(df_preview, use_container_width=True)
    gross_req = df_edited.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edited.loc['Scheduled Receipts'].astype(int).tolist()
    n = len(gross_req)

    # ============================================================
    # ALGORITMA MRP — FIXED & VALIDATED
    # ============================================================
    def calculate_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)

        # ── NET REQUIREMENTS (FIX: carry over on-hand correctly) ──────────
        net_req = []
        on_hand = init_inv
        for i in range(n):
            available = on_hand + s_receipts[i]
            nir = demands[i] + ss - available
            if nir > 0:
                net_req.append(nir)
                on_hand = ss        # after receiving planned order
            else:
                net_req.append(0)
                on_hand = available - demands[i]

        # ── POH & PLANNED RELEASE HELPER ──────────────────────────────────
        def build_schedule(planned_receipts):
            """Compute Projected On-Hand and Planned Order Releases."""
            poh = []
            inv = init_inv
            for i in range(n):
                inv = inv + s_receipts[i] + planned_receipts[i] - demands[i]
                poh.append(inv)

            releases = [0] * n
            for i in range(n):
                if planned_receipts[i] > 0:
                    release_period = i - lt
                    if release_period >= 0:
                        releases[release_period] += planned_receipts[i]
                    else:
                        # Period before planning horizon — add to P1 with note
                        releases[0] += planned_receipts[i]
            return poh, releases

        # ── 1. LOT-FOR-LOT (L4L) ──────────────────────────────────────────
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = build_schedule(l4l_rec)
        l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        l4l_hold  = sum(max(0, p) for p in l4l_poh) * hold

        # ── 2. LEAST UNIT COST (LUC) ──────────────────────────────────────
        luc_rec   = [0] * n
        luc_iters = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue

            best_k     = idx
            min_uc     = float('inf')
            acc_demand = 0
            acc_hold   = 0
            t_log      = []

            for k in range(idx, n):
                acc_demand += net_req[k]
                # Holding cost: units carried forward from period idx to k
                acc_hold   += net_req[k] * hold * (k - idx)
                total_cost  = setup + acc_hold
                uc          = total_cost / acc_demand if acc_demand > 0 else float('inf')

                if uc <= min_uc:
                    min_uc = uc
                    best_k = k
                    status = "Terpilih"
                    t_log.append({
                        'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}",
                        'Total Unit': acc_demand, 'Biaya Pesan': setup,
                        'Biaya Simpan': acc_hold, 'Total Biaya': total_cost,
                        'LUC (Rp/unit)': round(uc, 4), 'Status': status
                    })
                else:
                    status = "Stop! Biaya Naik"
                    t_log.append({
                        'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}",
                        'Total Unit': acc_demand, 'Biaya Pesan': setup,
                        'Biaya Simpan': acc_hold, 'Total Biaya': total_cost,
                        'LUC (Rp/unit)': round(uc, 4), 'Status': status
                    })
                    break

            luc_iters.append(pd.DataFrame(t_log))
            luc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1

        luc_poh, luc_rel = build_schedule(luc_rec)
        luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        luc_hold  = sum(max(0, p) for p in luc_poh) * hold

        # ── 3. ECONOMIC ORDER QUANTITY (EOQ) ──────────────────────────────
        # D = average gross requirement per period
        avg_demand = np.mean(demands) if len(demands) > 0 else 0
        if hold > 0 and avg_demand > 0:
            eoq_raw  = math.sqrt((2 * avg_demand * setup) / hold)
            eoq_size = max(1, math.ceil(eoq_raw))
        else:
            eoq_raw  = 0
            eoq_size = 1

        eoq_rec = [0] * n
        surplus = 0   # carry-over surplus from previous lot

        for i in range(n):
            if net_req[i] > 0:
                shortfall = net_req[i] - surplus
                if shortfall > 0:
                    # Order enough multiples of EOQ to cover shortfall
                    lots        = math.ceil(shortfall / eoq_size)
                    eoq_rec[i]  = lots * eoq_size
                    surplus     = eoq_rec[i] - shortfall   # new surplus after meeting demand
                else:
                    # existing surplus covers this period's net req
                    surplus    -= net_req[i]
            # if net_req[i] == 0, surplus stays as-is

        eoq_poh, eoq_rel = build_schedule(eoq_rec)
        eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        eoq_hold  = sum(max(0, p) for p in eoq_poh) * hold

        # ── 4. PART PERIOD BALANCING (PPB) ────────────────────────────────
        # EPP = Setup Cost / Holding Cost  (the Economic Part Period threshold)
        epp     = setup / hold if hold > 0 else float('inf')
        ppb_rec   = [0] * n
        ppb_iters = []

        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue

            best_k   = idx
            cum_pp   = 0.0          # cumulative part-periods
            prev_pp  = 0.0
            acc_d    = 0
            t_log    = []

            for k in range(idx, n):
                acc_d   += net_req[k]
                delta_pp = net_req[k] * (k - idx)   # part-periods added this period
                new_cum  = cum_pp + delta_pp

                t_log.append({
                    'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}",
                    'Total Unit': acc_d,
                    'EPP Batas': round(epp, 4),
                    'Part-Period Kumulatif': round(new_cum, 4),
                    'Status': ''
                })

                if new_cum <= epp:
                    best_k  = k
                    cum_pp  = new_cum
                    t_log[-1]['Status'] = "Mendekati Imbang"
                else:
                    # Check which side is closer to EPP
                    if abs(new_cum - epp) < abs(cum_pp - epp):
                        best_k = k
                    t_log[-1]['Status'] = "Stop! Melewati EPP"
                    break

            ppb_iters.append(pd.DataFrame(t_log))
            ppb_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1

        ppb_poh, ppb_rel = build_schedule(ppb_rec)
        ppb_setup = sum(1 for x in ppb_rec if x > 0) * setup
        ppb_hold  = sum(max(0, p) for p in ppb_poh) * hold

        return {
            'net_req': net_req,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel,
                    'setup': l4l_setup, 'hold': l4l_hold, 'total': l4l_setup + l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel,
                    'setup': luc_setup, 'hold': luc_hold, 'total': luc_setup + luc_hold,
                    'iters': luc_iters},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel,
                    'setup': eoq_setup, 'hold': eoq_hold, 'total': eoq_setup + eoq_hold,
                    'size': eoq_size, 'eoq_raw': eoq_raw, 'avg_demand': avg_demand},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel,
                    'setup': ppb_setup, 'hold': ppb_hold, 'total': ppb_setup + ppb_hold,
                    'iters': ppb_iters, 'epp': epp},
        }

    res = calculate_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)

    # ==========================================
    # 6. SUMMARY DASHBOARD
    # ==========================================
    st.markdown("---")
    st.markdown('<div class="section-title">Ringkasan Komparasi Biaya</div>', unsafe_allow_html=True)

    costs = {
        'l4l':  ('Lot-for-Lot',          res['l4l']['total'],  '#63b3ed'),
        'luc':  ('Least Unit Cost',       res['luc']['total'],  '#b794f4'),
        'eoq':  ('Economic Order Qty',    res['eoq']['total'],  '#68d391'),
        'ppb':  ('Part Period Balancing', res['ppb']['total'],  '#f6ad55'),
    }
    best_key  = min(costs, key=lambda k: costs[k][1])
    best_cost = costs[best_key][1]

    cols = st.columns(4)
    keys = ['l4l', 'luc', 'eoq', 'ppb']
    for i, key in enumerate(keys):
        name, total, color = costs[key]
        diff = total - best_cost
        is_best = (key == best_key)
        badge = '<span class="metric-badge-win">🏆 Paling Optimal</span>' if is_best else f'<span class="metric-badge-diff">+Rp {diff:,.0f}</span>'
        card_class = "metric-card winner" if is_best else "metric-card"
        with cols[i]:
            st.markdown(f"""
            <div class="{card_class}">
                <div class="metric-label" style="color:{color};">{name}</div>
                <div class="metric-value">Rp {total:,.0f}</div>
                <div style="display:flex; gap:12px; margin-top:10px; font-size:11px; color:#5c6b82; font-family:'JetBrains Mono',monospace;">
                    <span>⚙ {res[key]['setup']:,.0f}</span>
                    <span>🏷 {res[key]['hold']:,.0f}</span>
                </div>
                {badge}
            </div>
            """, unsafe_allow_html=True)

    best_name = costs[best_key][0]
    st.markdown(f"""
    <div class="rec-banner">
        <div class="rec-banner-icon">🎯</div>
        <div class="rec-banner-text">
            Rekomendasi sistem: gunakan metode <strong>{best_name}</strong> — 
            menghasilkan total biaya inventori paling rendah dari keempat opsi heuristik lot-sizing yang dianalisis.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 7. TABS DETAIL
    # ==========================================
    tab_chart, t_l4l, t_luc, t_eoq, t_ppb = st.tabs([
        "📊 Grafik & Sensitivitas",
        "L4L · Lot-for-Lot",
        "LUC · Least Unit Cost",
        "EOQ · Economic Order Qty",
        "PPB · Part Period Balancing"
    ])

    # ── HELPER: render MRP table ──────────────────────────────────────────
    def render_mrp_table(method_name, data, cap):
        periods = [f"P{i+1}" for i in range(n)]
        df = pd.DataFrame({
            'Gross Requirements':     gross_req,
            'Scheduled Receipts':     sched_rec,
            'Net Requirements':       res['net_req'],
            'Planned Order Receipts': data['rec'],
            'Projected On Hand':      data['poh'],
            'Planned Order Releases': data['rel'],
        }, index=periods).T

        # Highlight overstock rows
        def highlight_cap(row):
            if row.name == 'Projected On Hand':
                return ['background-color: rgba(245,101,101,0.15); color: #fc8181;'
                        if v > cap else '' for v in row]
            return ['']*len(row)

        st.dataframe(df.style.apply(highlight_cap, axis=1), use_container_width=True)

        violated = [p for p, v in zip(periods, data['poh']) if v > cap]
        if violated:
            st.markdown(f"""<div class="warn-box">
                ⚠️ <strong>Kapasitas Gudang Terlampaui</strong> — Stok proyeksi melebihi 
                batas {cap:,} unit pada periode: {', '.join(violated)}
            </div>""", unsafe_allow_html=True)

        # Cost breakdown
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Biaya Setup / Pesan", f"Rp {data['setup']:,.0f}")
        with c2:
            st.metric("Biaya Simpan", f"Rp {data['hold']:,.0f}")
        with c3:
            st.metric("Total Biaya", f"Rp {data['total']:,.0f}",
                      delta=f"+Rp {data['total']-best_cost:,.0f}" if data['total'] > best_cost else "Optimal",
                      delta_color="inverse" if data['total'] > best_cost else "off")

    # ── HIGHLIGHT for iteration tables ───────────────────────────────────
    def hl_stop(row):
        is_stop = 'Stop' in str(row.get('Status', ''))
        return ['background-color: rgba(245,101,101,0.1); color:#fc8181;'
                if is_stop else '' for _ in row]

    # ── TAB: CHARTS ───────────────────────────────────────────────────────
    with tab_chart:
        rcParams['font.family'] = 'monospace'
        FIG_BG   = '#0f1117'
        AXES_BG  = '#161b27'
        GRID_CLR = '#252d3d'
        TEXT_CLR = '#8892a4'

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">Total Biaya per Metode (Rp)</div>', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(6, 3.5))
            fig.patch.set_facecolor(FIG_BG)
            ax.set_facecolor(AXES_BG)
            labels_b = ['L4L', 'LUC', 'EOQ', 'PPB']
            vals_b   = [res['l4l']['total'], res['luc']['total'], res['eoq']['total'], res['ppb']['total']]
            colors_b = ['#63b3ed', '#b794f4', '#68d391', '#f6ad55']
            bars = ax.bar(labels_b, vals_b, color=colors_b, width=0.5, zorder=2)
            # Highlight winner
            best_idx = vals_b.index(min(vals_b))
            bars[best_idx].set_edgecolor('#ffffff')
            bars[best_idx].set_linewidth(1.5)
            ax.set_ylabel('Total Biaya (Rp)', color=TEXT_CLR, fontsize=9)
            ax.tick_params(colors=TEXT_CLR, labelsize=9)
            ax.yaxis.set_tick_params(labelcolor=TEXT_CLR)
            ax.xaxis.set_tick_params(labelcolor='#e8eaf0')
            ax.grid(axis='y', color=GRID_CLR, linewidth=0.8, zorder=0)
            ax.spines['bottom'].set_color(GRID_CLR)
            ax.spines['left'].set_color(GRID_CLR)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for bar, val in zip(bars, vals_b):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals_b)*0.01,
                        f'{val:,.0f}', ha='center', va='bottom', color=TEXT_CLR, fontsize=7)
            fig.tight_layout()
            st.pyplot(fig)

        with c2:
            st.markdown('<div class="section-title">Sensitivitas Demand (±30%)</div>', unsafe_allow_html=True)
            scale_factors = np.arange(0.70, 1.35, 0.05)
            s = {'l4l':[], 'luc':[], 'eoq':[], 'ppb':[]}
            labels_s = []
            for f in scale_factors:
                sim_d = [max(1, int(d*f)) for d in gross_req]
                sr    = calculate_mrp(sim_d, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
                for k in s: s[k].append(sr[k]['total'])
                labels_s.append(f"{int(round((f-1)*100)):+}%")

            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
            fig2.patch.set_facecolor(FIG_BG)
            ax2.set_facecolor(AXES_BG)
            for key, clr, lbl in [('l4l','#63b3ed','L4L'), ('luc','#b794f4','LUC'),
                                    ('eoq','#68d391','EOQ'), ('ppb','#f6ad55','PPB')]:
                ax2.plot(labels_s, s[key], color=clr, linewidth=1.8, label=lbl, marker='o', markersize=3)
            ax2.set_ylabel('Total Biaya (Rp)', color=TEXT_CLR, fontsize=9)
            ax2.tick_params(colors=TEXT_CLR, labelsize=8)
            ax2.yaxis.set_tick_params(labelcolor=TEXT_CLR)
            ax2.xaxis.set_tick_params(labelcolor=TEXT_CLR)
            ax2.grid(color=GRID_CLR, linewidth=0.6, linestyle=':')
            ax2.spines['bottom'].set_color(GRID_CLR)
            ax2.spines['left'].set_color(GRID_CLR)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            legend = ax2.legend(fontsize=8, framealpha=0.3, facecolor=AXES_BG, labelcolor=TEXT_CLR,
                                 edgecolor=GRID_CLR)
            plt.xticks(rotation=45)
            fig2.tight_layout()
            st.pyplot(fig2)

        # Demand chart
        st.markdown('<div class="section-title">Profil Permintaan & Penerimaan Terjadwal</div>', unsafe_allow_html=True)
        fig3, ax3 = plt.subplots(figsize=(12, 3))
        fig3.patch.set_facecolor(FIG_BG)
        ax3.set_facecolor(AXES_BG)
        x_pos = range(n)
        ax3.bar(x_pos, gross_req, color='#63b3ed', alpha=0.7, label='Gross Requirements', zorder=2)
        ax3.bar(x_pos, sched_rec, color='#68d391', alpha=0.7, bottom=gross_req, label='Scheduled Receipts', zorder=2)
        ax3.plot(x_pos, res['net_req'], color='#fc8181', linewidth=2, marker='o', markersize=4, label='Net Requirements')
        ax3.set_xticks(list(x_pos))
        ax3.set_xticklabels(period_labels, color='#e8eaf0', fontsize=9)
        ax3.tick_params(colors=TEXT_CLR, labelsize=9)
        ax3.yaxis.set_tick_params(labelcolor=TEXT_CLR)
        ax3.grid(axis='y', color=GRID_CLR, linewidth=0.6, linestyle=':', zorder=0)
        ax3.spines['bottom'].set_color(GRID_CLR)
        ax3.spines['left'].set_color(GRID_CLR)
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.legend(fontsize=8, framealpha=0.3, facecolor=AXES_BG, labelcolor=TEXT_CLR, edgecolor=GRID_CLR)
        fig3.tight_layout()
        st.pyplot(fig3)

    # ── TAB: L4L ──────────────────────────────────────────────────────────
    with t_l4l:
        st.markdown('<div class="section-title">Lot-for-Lot (L4L) — Pesan Sejumlah Net Requirement</div>', unsafe_allow_html=True)
        st.markdown("""<div class="info-box">
            L4L memesan persis sejumlah kebutuhan bersih setiap periode — tidak ada kelebihan stok, 
            namun frekuensi pemesanan paling tinggi.
        </div>""", unsafe_allow_html=True)
        render_mrp_table("L4L", res['l4l'], max_capacity)

    # ── TAB: LUC ──────────────────────────────────────────────────────────
    with t_luc:
        st.markdown('<div class="section-title">Least Unit Cost (LUC) — Minimasi Biaya per Unit</div>', unsafe_allow_html=True)
        st.markdown("""<div class="info-box">
            LUC menggabungkan kebutuhan beberapa periode selama biaya per unit (setup+holding) terus 
            menurun. Lot baru dimulai saat LUC mulai naik.
        </div>""", unsafe_allow_html=True)

        with st.expander("🔬 Log Iterasi Pembentukan Lot LUC"):
            fmt_luc = {'Biaya Pesan':'{:,.2f}', 'Biaya Simpan':'{:,.2f}',
                       'Total Biaya':'{:,.2f}', 'LUC (Rp/unit)':'{:.4f}'}
            for idx, df_it in enumerate(res['luc']['iters']):
                st.markdown(f'<div class="iter-header">Lot Ke-{idx+1}</div>', unsafe_allow_html=True)
                st.dataframe(df_it.style.apply(hl_stop, axis=1).format(fmt_luc),
                             hide_index=True, use_container_width=True)

        render_mrp_table("LUC", res['luc'], max_capacity)

    # ── TAB: EOQ ──────────────────────────────────────────────────────────
    with t_eoq:
        st.markdown('<div class="section-title">Economic Order Quantity (EOQ) — Ukuran Lot Tetap Optimal</div>', unsafe_allow_html=True)

        avg_d   = res['eoq']['avg_demand']
        eoq_raw = res['eoq']['eoq_raw']
        eoq_sz  = res['eoq']['size']
        num_val = 2 * avg_d * setup_cost
        den_val = holding_cost

        st.markdown(f"""<div class="info-box">
            EOQ menghitung ukuran lot tetap yang menyeimbangkan biaya pesan dan biaya simpan.
            Setiap pesanan = <strong>{eoq_sz} unit</strong> (atau kelipatannya).
        </div>""", unsafe_allow_html=True)

        with st.expander("📐 Detail Perhitungan Formula EOQ"):
            st.markdown(f"""<div class="formula-box">
<div class="formula-step">1 · Data Gross Requirements</div>
  Nilai per periode : {gross_req}
  Total             : {sum(gross_req)} unit
  Jumlah periode    : {n}

<div class="formula-step">2 · Rata-rata Demand (D)</div>
  D = {sum(gross_req)} / {n} = <strong>{avg_d:.4f} unit/periode</strong>

<div class="formula-step">3 · Rumus EOQ</div>
  EOQ = √( 2 × D × S / H )
      = √( 2 × {avg_d:.4f} × {setup_cost:,.2f} / {holding_cost:,.2f} )
      = √( {num_val:,.4f} / {den_val:,.2f} )
      = √( {num_val/den_val:,.4f} )
      = {eoq_raw:.4f}

<div class="formula-step">4 · Pembulatan (ceiling)</div>
  EOQ final = ⌈{eoq_raw:.4f}⌉ = <strong>{eoq_sz} unit</strong>
</div>""", unsafe_allow_html=True)

        render_mrp_table("EOQ", res['eoq'], max_capacity)

    # ── TAB: PPB ──────────────────────────────────────────────────────────
    with t_ppb:
        epp_val = res['ppb']['epp']
        st.markdown('<div class="section-title">Part Period Balancing (PPB) — Keseimbangan Part-Period</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="info-box">
            PPB menggabungkan periode selama kumulatif <em>part-period</em> belum melewati 
            <strong>EPP = Setup/Holding = {epp_val:,.2f}</strong>. 
            Lot berhenti di titik terdekat dengan EPP.
        </div>""", unsafe_allow_html=True)

        with st.expander("🔬 Log Iterasi Pembentukan Lot PPB"):
            fmt_ppb = {'EPP Batas':'{:.4f}', 'Part-Period Kumulatif':'{:.4f}'}
            for idx, df_it in enumerate(res['ppb']['iters']):
                st.markdown(f'<div class="iter-header">Lot Ke-{idx+1}</div>', unsafe_allow_html=True)
                st.dataframe(df_it.style.apply(hl_stop, axis=1).format(fmt_ppb),
                             hide_index=True, use_container_width=True)

        render_mrp_table("PPB", res['ppb'], max_capacity)

    # ==========================================
    # 8. EXPORT EXCEL
    # ==========================================
    st.markdown("---")
    st.markdown('<div class="section-title">Ekspor Laporan</div>', unsafe_allow_html=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        periods_idx = [f"P{i+1}" for i in range(n)]

        pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Net Requirements':   res['net_req']
        }, index=periods_idx).T.to_excel(writer, sheet_name="Data Dasar")

        summary = pd.DataFrame({
            'Metode':        ['L4L', 'LUC', 'EOQ', 'PPB'],
            'Biaya Setup':   [res['l4l']['setup'], res['luc']['setup'], res['eoq']['setup'], res['ppb']['setup']],
            'Biaya Simpan':  [res['l4l']['hold'],  res['luc']['hold'],  res['eoq']['hold'],  res['ppb']['hold']],
            'Total Biaya':   [res['l4l']['total'], res['luc']['total'], res['eoq']['total'], res['ppb']['total']],
        })
        summary.to_excel(writer, sheet_name="Ringkasan Biaya", index=False)

        for key, name in [('l4l','L4L'), ('luc','LUC'), ('eoq','EOQ'), ('ppb','PPB')]:
            pd.DataFrame({
                'Projected On Hand':      res[key]['poh'],
                'Planned Order Receipts': res[key]['rec'],
                'Planned Order Releases': res[key]['rel'],
            }, index=periods_idx).T.to_excel(writer, sheet_name=f"Metode {name}")

    output.seek(0)
    st.download_button(
        label="📥 Download Laporan 4 Metode (.xlsx)",
        data=output,
        file_name="MRP_MultiMetode_Laporan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.markdown("""<div class="info-box">
        💡 Masukkan data permintaan di atas untuk memulai kalkulasi MRP.
    </div>""", unsafe_allow_html=True)
