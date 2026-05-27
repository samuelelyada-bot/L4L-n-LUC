import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import math
import io

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="MRP Planner · Multi-Metode",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light theme CSS — minimal override, tidak konflik Streamlit komponen
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #f5f6fa !important;
}

/* ─── HEADER ─────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    border-radius: 16px;
    padding: 36px 40px;
    margin-bottom: 28px;
    color: white;
    position: relative;
    overflow: hidden;
}
.app-header::after {
    content: '📦';
    font-size: 120px;
    position: absolute;
    right: 32px;
    top: -10px;
    opacity: 0.08;
    line-height: 1;
}
.app-header .badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #bfdbfe;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.app-header h1 {
    font-size: 26px;
    font-weight: 800;
    color: #fff;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
}
.app-header p {
    font-size: 14px;
    color: #93c5fd;
    margin: 0;
}

/* ─── SECTION LABEL ──────────────────────── */
.sec-label {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 24px 0 12px 0;
    padding-left: 10px;
    border-left: 3px solid #2563eb;
}

/* ─── METRIC CARDS ───────────────────────── */
.mcard {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px 22px;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.mcard:hover { box-shadow: 0 4px 16px rgba(37,99,235,0.08); }
.mcard.best {
    border-color: #22c55e;
    background: linear-gradient(135deg, #f0fdf4, #ffffff);
    box-shadow: 0 4px 20px rgba(34,197,94,0.12);
}
.mcard .mc-label {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.mcard .mc-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 500;
    color: #1e293b;
    letter-spacing: -0.02em;
}
.mcard .mc-sub {
    font-size: 11px;
    color: #94a3b8;
    margin-top: 6px;
    font-family: 'JetBrains Mono', monospace;
}
.badge-win {
    display: inline-block;
    background: #dcfce7;
    color: #16a34a;
    border: 1px solid #86efac;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
    margin-top: 8px;
}
.badge-diff {
    display: inline-block;
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fca5a5;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
}

/* ─── RECOMMENDATION BANNER ──────────────── */
.rec-box {
    background: linear-gradient(135deg, #eff6ff, #f0fdf4);
    border: 1.5px solid #bbf7d0;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 20px 0 8px 0;
    font-size: 14px;
    color: #334155;
    line-height: 1.6;
}
.rec-box strong { color: #15803d; }

/* ─── INFO / WARN BOX ────────────────────── */
.info-box {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    font-size: 13px;
    color: #1e40af;
    margin: 12px 0 18px 0;
    line-height: 1.6;
}
.warn-box {
    background: #fef2f2;
    border-left: 4px solid #ef4444;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    font-size: 13px;
    color: #991b1b;
    margin: 10px 0;
    line-height: 1.6;
}

/* ─── FORMULA BOX ────────────────────────── */
.formula-box {
    background: #1e293b;
    border-radius: 12px;
    padding: 20px 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #7dd3fc;
    line-height: 2;
    white-space: pre-wrap;
    margin: 12px 0;
}
.formula-step {
    color: #475569;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
}

/* ─── ITER HEADER ────────────────────────── */
.iter-header {
    font-size: 12px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 6px 0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 10px;
}

/* ─── DIVIDER ─────────────────────────────── */
.divider { height: 1px; background: #e2e8f0; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. HEADER
# ==========================================
st.markdown("""
<div class="app-header">
    <div class="badge">DSS · Decision Support System</div>
    <h1>MRP Planner · Multi-Metode</h1>
    <p>Lot-for-Lot &nbsp;·&nbsp; Least Unit Cost &nbsp;·&nbsp; Economic Order Quantity &nbsp;·&nbsp; Part Period Balancing</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Parameter MRP")
    st.markdown("**Biaya**")
    setup_cost   = st.number_input("Ordering / Setup Cost (Rp)", min_value=0.0, value=100000.0, step=500.0)
    holding_cost = st.number_input("Holding Cost (Rp/unit/periode)", min_value=0.0, value=2000.0, step=100.0)
    st.markdown("---")
    st.markdown("**Inventori**")
    initial_inv  = st.number_input("Persediaan Awal (unit)", min_value=0, value=35, step=5)
    safety_stock = st.number_input("Safety Stock (unit)", min_value=0, value=0, step=1)
    lead_time    = st.number_input("Lead Time (periode)", min_value=0, value=1, step=1)
    st.markdown("---")
    st.markdown("**Gudang**")
    max_capacity = st.number_input("Kapasitas Maks. Gudang (unit)", min_value=1, value=500, step=10)


# ==========================================
# 4. DATA INPUT
# ==========================================
st.markdown('<div class="sec-label">Data Permintaan & Penerimaan Terjadwal</div>', unsafe_allow_html=True)

input_method = st.radio(
    "Sumber data:",
    ["Gunakan Data Contoh", "Input Manual", "Upload File (Excel / CSV)"],
    horizontal=True
)

def detect_col(columns, targets):
    for col in columns:
        c = str(col).strip().lower().replace("_","").replace(" ","")
        if c in targets:
            return col
    return None

df_kerja = None

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file (.xlsx / .xls / .csv)", type=["csv","xlsx","xls"])
    if uploaded_file:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            col_p  = detect_col(df_raw.columns, ['periode','mingguke','p','minggu'])
            col_gr = detect_col(df_raw.columns, ['gr','grossrequirement','grossrequirements','kebutuhankotor'])
            col_sr = detect_col(df_raw.columns, ['sr','scheduledreceipt','scheduledreceipts','penerimaanterjadwal'])
            df_kerja = pd.DataFrame()
            df_kerja['Periode']            = df_raw[col_p].astype(str) if col_p else [f"P{i+1}" for i in range(len(df_raw))]
            df_kerja['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int) if col_gr else 0
            df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int) if col_sr else 0
            if not col_gr:
                st.error("❌ Kolom Gross Requirements tidak terdeteksi.")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

elif input_method == "Input Manual":
    num_p = st.number_input("Jumlah Periode:", min_value=1, max_value=52, value=10, step=1)
    default_gr = [35, 30, 40, 0, 10, 40, 30, 0, 30, 55]
    init_data  = {
        'Periode':            [f"P{i+1}" for i in range(num_p)],
        'Gross Requirements': (default_gr + [0]*52)[:num_p],
        'Scheduled Receipts': [0]*num_p
    }
    df_kerja = st.data_editor(pd.DataFrame(init_data), use_container_width=True, hide_index=True)

else:
    df_kerja = pd.DataFrame({
        'Periode':            [f"P{i}" for i in range(1, 11)],
        'Gross Requirements': [35, 30, 40, 0, 10, 40, 30, 0, 30, 55],
        'Scheduled Receipts': [0]*10
    })
    st.dataframe(df_kerja, use_container_width=True, hide_index=True)


# ==========================================
# 5. PREVIEW & EDIT
# ==========================================
if df_kerja is not None and not df_kerja.empty:
    gross_req     = df_kerja['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec     = df_kerja['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_kerja['Periode'].astype(str).tolist()
    n             = len(gross_req)

    st.markdown('<div class="sec-label">Preview & Edit Data Aktif</div>', unsafe_allow_html=True)
    df_prev = pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec}, index=period_labels).T
    df_edit = st.data_editor(df_prev, use_container_width=True)
    gross_req = df_edit.loc['Gross Requirements'].astype(int).tolist()
    sched_rec = df_edit.loc['Scheduled Receipts'].astype(int).tolist()
    n = len(gross_req)

    # ==========================================
    # 6. ALGORITMA MRP
    # ==========================================
    def calculate_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)

        # NET REQUIREMENTS
        net_req  = []
        on_hand  = init_inv
        for i in range(n):
            available = on_hand + s_receipts[i]
            nir = demands[i] + ss - available
            if nir > 0:
                net_req.append(nir)
                on_hand = ss
            else:
                net_req.append(0)
                on_hand = available - demands[i]

        # PLANNED RECEIPTS → POH + RELEASES
        def build_schedule(planned_rec):
            poh = []
            inv = init_inv
            for i in range(n):
                inv = inv + s_receipts[i] + planned_rec[i] - demands[i]
                poh.append(inv)
            releases = [0] * n
            for i in range(n):
                if planned_rec[i] > 0:
                    rp = i - lt
                    releases[max(0, rp)] += planned_rec[i]
            return poh, releases

        # ── 1. L4L ──────────────────────────────────
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = build_schedule(l4l_rec)
        l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        l4l_hold  = sum(max(0, p) for p in l4l_poh) * hold

        # ── 2. LUC ──────────────────────────────────
        luc_rec   = [0] * n
        luc_iters = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1; continue
            best_k, min_uc, acc_d, acc_h, t_log = idx, float('inf'), 0, 0, []
            for k in range(idx, n):
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                tc    = setup + acc_h
                uc    = tc / acc_d if acc_d > 0 else float('inf')
                if uc <= min_uc:
                    min_uc, best_k = uc, k
                    t_log.append({'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d,
                                  'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': tc,
                                  'LUC (Rp/unit)': round(uc, 4), 'Status': 'Terpilih'})
                else:
                    t_log.append({'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d,
                                  'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': tc,
                                  'LUC (Rp/unit)': round(uc, 4), 'Status': 'Stop! Biaya Naik'})
                    break
            luc_iters.append(pd.DataFrame(t_log))
            luc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
        luc_poh, luc_rel = build_schedule(luc_rec)
        luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        luc_hold  = sum(max(0, p) for p in luc_poh) * hold

        # ── 3. EOQ ──────────────────────────────────
        avg_d = np.mean(demands) if len(demands) > 0 else 0
        if hold > 0 and avg_d > 0:
            eoq_raw  = math.sqrt((2 * avg_d * setup) / hold)
            eoq_size = max(1, math.ceil(eoq_raw))
        else:
            eoq_raw, eoq_size = 0, 1
        eoq_rec = [0] * n
        surplus = 0
        for i in range(n):
            if net_req[i] > 0:
                shortfall = net_req[i] - surplus
                if shortfall > 0:
                    lots = math.ceil(shortfall / eoq_size)
                    eoq_rec[i] = lots * eoq_size
                    surplus    = eoq_rec[i] - shortfall
                else:
                    surplus -= net_req[i]
        eoq_poh, eoq_rel = build_schedule(eoq_rec)
        eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        eoq_hold  = sum(max(0, p) for p in eoq_poh) * hold

        # ── 4. PPB ──────────────────────────────────
        epp     = setup / hold if hold > 0 else float('inf')
        ppb_rec = [0] * n
        ppb_iters = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1; continue
            best_k, cum_pp, acc_d, t_log = idx, 0.0, 0, []
            for k in range(idx, n):
                acc_d   += net_req[k]
                new_cum  = cum_pp + net_req[k] * (k - idx)
                if new_cum <= epp:
                    best_k = k
                    cum_pp = new_cum
                    t_log.append({'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d,
                                  'EPP Batas': round(epp, 4), 'Part-Period Kumulatif': round(new_cum, 4),
                                  'Status': 'Mendekati Imbang'})
                else:
                    if abs(new_cum - epp) < abs(cum_pp - epp):
                        best_k = k
                    t_log.append({'Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d,
                                  'EPP Batas': round(epp, 4), 'Part-Period Kumulatif': round(new_cum, 4),
                                  'Status': 'Stop! Melewati EPP'})
                    break
            ppb_iters.append(pd.DataFrame(t_log))
            ppb_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
        ppb_poh, ppb_rel = build_schedule(ppb_rec)
        ppb_setup = sum(1 for x in ppb_rec if x > 0) * setup
        ppb_hold  = sum(max(0, p) for p in ppb_poh) * hold

        return {
            'net_req': net_req,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': l4l_setup, 'hold': l4l_hold, 'total': l4l_setup + l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': luc_setup, 'hold': luc_hold, 'total': luc_setup + luc_hold, 'iters': luc_iters},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': eoq_setup, 'hold': eoq_hold, 'total': eoq_setup + eoq_hold, 'size': eoq_size, 'eoq_raw': eoq_raw, 'avg_demand': avg_d},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': ppb_setup, 'hold': ppb_hold, 'total': ppb_setup + ppb_hold, 'iters': ppb_iters, 'epp': epp},
        }

    res = calculate_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)

    # ==========================================
    # 7. SUMMARY CARDS
    # ==========================================
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-label">Ringkasan Komparasi Biaya</div>', unsafe_allow_html=True)

    method_info = {
        'l4l': ('L4L · Lot-for-Lot',          '#3b82f6'),
        'luc': ('LUC · Least Unit Cost',       '#8b5cf6'),
        'eoq': ('EOQ · Econ. Order Qty',       '#10b981'),
        'ppb': ('PPB · Part Period Balancing', '#f59e0b'),
    }
    best_key  = min(['l4l','luc','eoq','ppb'], key=lambda k: res[k]['total'])
    best_cost = res[best_key]['total']

    cols = st.columns(4)
    for i, key in enumerate(['l4l','luc','eoq','ppb']):
        name, color = method_info[key]
        total = res[key]['total']
        diff  = total - best_cost
        is_best = (key == best_key)
        badge = '<span class="badge-win">🏆 Paling Optimal</span>' if is_best else f'<span class="badge-diff">+Rp {diff:,.0f}</span>'
        with cols[i]:
            st.markdown(f"""
            <div class="mcard {'best' if is_best else ''}">
                <div class="mc-label" style="color:{color};">{name}</div>
                <div class="mc-value">Rp {total:,.0f}</div>
                <div class="mc-sub">⚙ {res[key]['setup']:,.0f} &nbsp;|&nbsp; 🏷 {res[key]['hold']:,.0f}</div>
                {badge}
            </div>
            """, unsafe_allow_html=True)

    best_name = method_info[best_key][0]
    st.markdown(f"""
    <div class="rec-box">
        🎯 &nbsp;<strong>Rekomendasi Sistem:</strong> Metode <strong>{best_name}</strong> menghasilkan 
        total biaya inventori paling rendah — Rp {best_cost:,.0f} — dari keempat opsi heuristik lot-sizing yang dianalisis.
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 8. MRP TABLE HELPER
    # ==========================================
    def render_mrp_table(key, data, cap):
        periods = [f"P{i+1}" for i in range(n)]
        df = pd.DataFrame({
            'Gross Requirements':     gross_req,
            'Scheduled Receipts':     sched_rec,
            'Net Requirements':       res['net_req'],
            'Planned Order Receipts': data['rec'],
            'Projected On Hand':      data['poh'],
            'Planned Order Releases': data['rel'],
        }, index=periods).T

        def hl_cap(row):
            if row.name == 'Projected On Hand':
                return ['background-color: #fef2f2; color: #dc2626;'
                        if v > cap else '' for v in row]
            return ['']*len(row)

        st.dataframe(df.style.apply(hl_cap, axis=1), use_container_width=True)

        violated = [p for p, v in zip(periods, data['poh']) if v > cap]
        if violated:
            st.markdown(f'<div class="warn-box">⚠️ <strong>Kapasitas Gudang Terlampaui</strong> — Stok proyeksi melebihi batas {cap:,} unit pada periode: {", ".join(violated)}</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Biaya Setup / Pesan", f"Rp {data['setup']:,.0f}")
        with c2: st.metric("Biaya Simpan", f"Rp {data['hold']:,.0f}")
        with c3:
            delta_val = data['total'] - best_cost
            st.metric("Total Biaya", f"Rp {data['total']:,.0f}",
                      delta=f"+Rp {delta_val:,.0f}" if delta_val > 0 else "Optimal ✓",
                      delta_color="inverse" if delta_val > 0 else "off")

    def hl_stop(row):
        is_stop = 'Stop' in str(row.get('Status', ''))
        return ['background-color: #fef2f2; color: #dc2626;' if is_stop else '' for _ in row]

    # ==========================================
    # 9. TABS
    # ==========================================
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    tab_chart, t_l4l, t_luc, t_eoq, t_ppb = st.tabs([
        "📊 Grafik & Sensitivitas",
        "L4L · Lot-for-Lot",
        "LUC · Least Unit Cost",
        "EOQ · Economic Order Qty",
        "PPB · Part Period Balancing",
    ])

    # ── GRAFIK ────────────────────────────────────────────────────────────
    with tab_chart:
        FIG_BG  = '#ffffff'
        AX_BG   = '#f8fafc'
        GR_CLR  = '#e2e8f0'
        TX_CLR  = '#64748b'

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-label">Total Biaya per Metode (Rp)</div>', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(6, 3.8))
            fig.patch.set_facecolor(FIG_BG)
            ax.set_facecolor(AX_BG)
            labels_b = ['L4L', 'LUC', 'EOQ', 'PPB']
            vals_b   = [res['l4l']['total'], res['luc']['total'], res['eoq']['total'], res['ppb']['total']]
            colors_b = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b']
            bars = ax.bar(labels_b, vals_b, color=colors_b, width=0.5, zorder=2, edgecolor='white', linewidth=1.5)
            bi   = vals_b.index(min(vals_b))
            bars[bi].set_edgecolor('#15803d')
            bars[bi].set_linewidth(2.5)
            ax.set_ylabel('Total Biaya (Rp)', color=TX_CLR, fontsize=9)
            ax.tick_params(labelcolor=TX_CLR, labelsize=9)
            ax.grid(axis='y', color=GR_CLR, linewidth=0.8, zorder=0)
            for sp in ['top','right']: ax.spines[sp].set_visible(False)
            for sp in ['bottom','left']: ax.spines[sp].set_color(GR_CLR)
            for bar, val in zip(bars, vals_b):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(vals_b)*0.01,
                        f'Rp {val:,.0f}', ha='center', va='bottom', color=TX_CLR, fontsize=7.5)
            fig.tight_layout()
            st.pyplot(fig)

        with c2:
            st.markdown('<div class="sec-label">Sensitivitas Demand (±30%)</div>', unsafe_allow_html=True)
            scale_factors = np.arange(0.70, 1.35, 0.05)
            s = {k: [] for k in ['l4l','luc','eoq','ppb']}
            labels_s = []
            for f in scale_factors:
                sim_d = [max(1, int(d*f)) for d in gross_req]
                sr    = calculate_mrp(sim_d, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
                for k in s: s[k].append(sr[k]['total'])
                labels_s.append(f"{int(round((f-1)*100)):+}%")
            fig2, ax2 = plt.subplots(figsize=(6, 3.8))
            fig2.patch.set_facecolor(FIG_BG)
            ax2.set_facecolor(AX_BG)
            for key, clr, lbl in [('l4l','#3b82f6','L4L'),('luc','#8b5cf6','LUC'),
                                   ('eoq','#10b981','EOQ'),('ppb','#f59e0b','PPB')]:
                ax2.plot(labels_s, s[key], color=clr, linewidth=2, label=lbl, marker='o', markersize=4)
            ax2.set_ylabel('Total Biaya (Rp)', color=TX_CLR, fontsize=9)
            ax2.tick_params(labelcolor=TX_CLR, labelsize=8)
            ax2.grid(color=GR_CLR, linewidth=0.6, linestyle=':')
            for sp in ['top','right']: ax2.spines[sp].set_visible(False)
            for sp in ['bottom','left']: ax2.spines[sp].set_color(GR_CLR)
            ax2.legend(fontsize=9, framealpha=0.8, edgecolor=GR_CLR)
            plt.xticks(rotation=45)
            fig2.tight_layout()
            st.pyplot(fig2)

        st.markdown('<div class="sec-label">Profil Permintaan per Periode</div>', unsafe_allow_html=True)
        fig3, ax3 = plt.subplots(figsize=(12, 3.2))
        fig3.patch.set_facecolor(FIG_BG)
        ax3.set_facecolor(AX_BG)
        xp = range(n)
        ax3.bar(xp, gross_req, color='#3b82f6', alpha=0.75, label='Gross Requirements', zorder=2)
        ax3.bar(xp, sched_rec, color='#10b981', alpha=0.75, bottom=gross_req, label='Scheduled Receipts', zorder=2)
        ax3.plot(xp, res['net_req'], color='#ef4444', linewidth=2, marker='o', markersize=5, label='Net Requirements', zorder=3)
        ax3.set_xticks(list(xp))
        ax3.set_xticklabels(period_labels, fontsize=9, color=TX_CLR)
        ax3.tick_params(labelcolor=TX_CLR, labelsize=9)
        ax3.grid(axis='y', color=GR_CLR, linewidth=0.6, linestyle=':', zorder=0)
        for sp in ['top','right']: ax3.spines[sp].set_visible(False)
        for sp in ['bottom','left']: ax3.spines[sp].set_color(GR_CLR)
        ax3.legend(fontsize=9, framealpha=0.8, edgecolor=GR_CLR)
        fig3.tight_layout()
        st.pyplot(fig3)

    # ── L4L ────────────────────────────────────────────────────────────────
    with t_l4l:
        st.markdown('<div class="sec-label">Lot-for-Lot — Pesan Sejumlah Net Requirement</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">L4L memesan persis sejumlah kebutuhan bersih setiap periode. Tidak ada kelebihan stok, namun frekuensi pemesanan paling tinggi sehingga total biaya setup cenderung besar.</div>', unsafe_allow_html=True)
        render_mrp_table('l4l', res['l4l'], max_capacity)

    # ── LUC ────────────────────────────────────────────────────────────────
    with t_luc:
        st.markdown('<div class="sec-label">Least Unit Cost — Minimasi Biaya per Unit</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">LUC menggabungkan kebutuhan beberapa periode selama biaya per unit (setup + holding) terus menurun. Lot baru dimulai ketika LUC mulai naik.</div>', unsafe_allow_html=True)
        with st.expander("🔬 Lihat Log Iterasi Pembentukan Lot LUC"):
            fmt_luc = {'Biaya Pesan':'{:,.2f}','Biaya Simpan':'{:,.2f}','Total Biaya':'{:,.2f}','LUC (Rp/unit)':'{:.4f}'}
            for i, df_it in enumerate(res['luc']['iters']):
                st.markdown(f'<div class="iter-header">Lot Ke-{i+1}</div>', unsafe_allow_html=True)
                st.dataframe(df_it.style.apply(hl_stop, axis=1).format(fmt_luc), hide_index=True, use_container_width=True)
        render_mrp_table('luc', res['luc'], max_capacity)

    # ── EOQ ────────────────────────────────────────────────────────────────
    with t_eoq:
        avg_d   = res['eoq']['avg_demand']
        eoq_raw = res['eoq']['eoq_raw']
        eoq_sz  = res['eoq']['size']
        st.markdown('<div class="sec-label">Economic Order Quantity — Ukuran Lot Tetap Optimal</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">EOQ menghitung ukuran lot tetap yang menyeimbangkan biaya pesan dan biaya simpan. Ukuran lot terpilih: <strong>{eoq_sz} unit</strong> per pesanan (atau kelipatan).</div>', unsafe_allow_html=True)
        with st.expander("📐 Lihat Detail Perhitungan Formula EOQ"):
            num_v = 2 * avg_d * setup_cost
            st.markdown(f"""<div class="formula-box"><div class="formula-step">1 · Gross Requirements</div>  Nilai : {gross_req}
  Total : {sum(gross_req)} unit  |  n = {n} periode

<div class="formula-step">2 · Rata-rata Demand (D)</div>  D = {sum(gross_req)} / {n} = {avg_d:.4f} unit/periode

<div class="formula-step">3 · Rumus EOQ = √( 2 × D × S / H )</div>  = √( 2 × {avg_d:.4f} × {setup_cost:,.2f} / {holding_cost:,.2f} )
  = √( {num_v:,.4f} / {holding_cost:,.2f} )
  = √( {num_v/holding_cost:,.4f} )
  = {eoq_raw:.4f} unit

<div class="formula-step">4 · Pembulatan Ceiling</div>  EOQ = ⌈{eoq_raw:.4f}⌉ = {eoq_sz} unit</div>""", unsafe_allow_html=True)
        render_mrp_table('eoq', res['eoq'], max_capacity)

    # ── PPB ────────────────────────────────────────────────────────────────
    with t_ppb:
        epp_val = res['ppb']['epp']
        st.markdown('<div class="sec-label">Part Period Balancing — Keseimbangan Part-Period</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">PPB menggabungkan periode selama kumulatif part-period belum melewati <strong>EPP = {epp_val:,.2f}</strong>. Lot berhenti di titik terdekat dengan nilai EPP.</div>', unsafe_allow_html=True)
        with st.expander("🔬 Lihat Log Iterasi Pembentukan Lot PPB"):
            fmt_ppb = {'EPP Batas':'{:.4f}','Part-Period Kumulatif':'{:.4f}'}
            for i, df_it in enumerate(res['ppb']['iters']):
                st.markdown(f'<div class="iter-header">Lot Ke-{i+1}</div>', unsafe_allow_html=True)
                st.dataframe(df_it.style.apply(hl_stop, axis=1).format(fmt_ppb), hide_index=True, use_container_width=True)
        render_mrp_table('ppb', res['ppb'], max_capacity)

    # ==========================================
    # 10. EXPORT
    # ==========================================
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-label">Ekspor Laporan Excel</div>', unsafe_allow_html=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        periods_idx = [f"P{i+1}" for i in range(n)]
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec,
                      'Net Requirements': res['net_req']}, index=periods_idx).T.to_excel(writer, sheet_name="Data Dasar")
        pd.DataFrame({'Metode': ['L4L','LUC','EOQ','PPB'],
                      'Biaya Setup':  [res[k]['setup'] for k in ['l4l','luc','eoq','ppb']],
                      'Biaya Simpan': [res[k]['hold']  for k in ['l4l','luc','eoq','ppb']],
                      'Total Biaya':  [res[k]['total'] for k in ['l4l','luc','eoq','ppb']]
                      }).to_excel(writer, sheet_name="Ringkasan Biaya", index=False)
        for key, name in [('l4l','L4L'),('luc','LUC'),('eoq','EOQ'),('ppb','PPB')]:
            pd.DataFrame({'Projected On Hand': res[key]['poh'],
                          'Planned Order Receipts': res[key]['rec'],
                          'Planned Order Releases': res[key]['rel']},
                         index=periods_idx).T.to_excel(writer, sheet_name=f"Metode {name}")
    output.seek(0)
    st.download_button("📥 Download Laporan 4 Metode (.xlsx)", data=output,
                       file_name="MRP_MultiMetode_Laporan.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("💡 Masukkan data permintaan di atas untuk memulai kalkulasi MRP.")
