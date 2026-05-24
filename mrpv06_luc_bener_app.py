import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(page_title="MRP Calculator - Multi-Metode Premium DSS", layout="wide")
st.title("📦 Aplikasi Perencanaan Kebutuhan Material (MRP) - Multi-Metode")
st.caption("Edisi DSS Lengkap: Perbandingan L4L, LUC, EOQ, dan Part Period Balancing (PPB) dengan UI Premium")
st.markdown("---")

# ==========================================
# 2. SIDEBAR - INPUT PARAMETER
# ==========================================
st.sidebar.header("🛠️ Parameter Input")

setup_cost = st.sidebar.number_input("Ordering / Setup Cost (Rp)", min_value=0.0, value=100000.0, step=5000.0)
holding_cost = st.sidebar.number_input("Holding Cost (Rp / unit / periode)", min_value=0.0, value=2000.0, step=500.0)
initial_inv = st.sidebar.number_input("Persediaan Awal (Initial Inventory)", min_value=0, value=0, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=1, step=1)
lead_time = st.sidebar.number_input("Lead Time (Periode)", min_value=0, value=1, step=1)

# Constraint Kapasitas Gudang
st.sidebar.markdown("---")
st.sidebar.header("🏬 Batasan Operasional")
max_capacity = st.sidebar.number_input("Kapasitas Maksimum Gudang (Unit)", min_value=1, value=100, step=10)

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
            return ['background-color: #ffe6cc; color: #cc6600; font-weight: bold;' if val > max_cap else '' for val in row]
        return [''] * len(row)
    return df_mrp_transposed.style.apply(highlight_row_capacity, axis=1)

def highlight_stop(row):
    return ['background-color: #ffcccc; color: black; font-weight: bold;' if row['Status'] == 'Stop! Biaya Naik' or row['Status'] == 'Stop! Melebihi Batas' else '' for _ in row]

# ==========================================
# 3. AREA DATA INPUT
# ==========================================
st.subheader("📊 Data Kebutuhan Kotor & Penerimaan Terjadwal")

input_method = st.radio(
    "Pilih Metode Input Data:", 
    ["Upload File (Excel / CSV)", "Input Manual Langsung di Aplikasi", "Gunakan Data Contoh (Template)"]
)

df_kerja = None

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file Anda di sini (Format file didukung: .xlsx, .xls, .csv)", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            col_periode = dapatkan_kolom_cocok(df_raw.columns, ['periode', 'mingguke', 'p', 'minggu'])
            col_gr = dapatkan_kolom_cocok(df_raw.columns, ['gr', 'grossrequirement', 'grossrequirements', 'kebutuhankotor'])
            col_sr = dapatkan_kolom_cocok(df_raw.columns, ['sr', 'scheduledreceipt', 'scheduledreceipts', 'penerimaanterjadwal'])
            
            df_kerja = pd.DataFrame()
            
            if col_periode and col_periode in df_raw.columns:
                df_kerja['Periode'] = df_raw[col_periode].astype(str)
            else:
                df_kerja['Periode'] = [f"P{i+1}" for i in range(len(df_raw))]
                
            if col_gr and col_gr in df_raw.columns:
                df_kerja['Gross Requirements'] = df_raw[col_gr].fillna(0).astype(int)
            else:
                st.error("❌ Kolom Kebutuhan Kotor (GR) tidak terdeteksi otomatis.")
                
            if col_sr and col_sr in df_raw.columns:
                df_kerja['Scheduled Receipts'] = df_raw[col_sr].fillna(0).astype(int)
            else:
                df_kerja['Scheduled Receipts'] = 0
                
        except Exception as e:
            st.error(f"Gagal membaca file. Error: {e}")
            
elif input_method == "Input Manual Langsung di Aplikasi":
    num_periods_input = st.number_input("Tentukan Jumlah Periode Perencanaan:", min_value=1, max_value=52, value=8, step=1)
    init_data = {
        'Periode': [f"P{i+1}" for i in range(num_periods_input)],
        'Gross Requirements': [0] * num_periods_input,
        'Scheduled Receipts': [0] * num_periods_input
    }
    df_empty = pd.DataFrame(init_data)
    df_kerja = st.data_editor(df_empty, use_container_width=True, hide_index=True)

else:
    default_data = {
        'Periode': [f"P{i}" for i in range(1, 9)],
        'Gross Requirements': [30, 40, 20, 70, 40, 10, 30, 60],
        'Scheduled Receipts': [0, 10, 0, 0, 20, 0, 0, 0]
    }
    df_kerja = pd.DataFrame(default_data)

if df_kerja is not None and not df_kerja.empty:
    gross_req = df_kerja['Gross Requirements'].fillna(0).astype(int).tolist()
    sched_rec = df_kerja['Scheduled Receipts'].fillna(0).astype(int).tolist()
    period_labels = df_kerja['Periode'].astype(str).tolist()
    
    st.markdown("##### 🔍 Preview Ringkasan Data Input Aktif")
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
        
        # --- HITUNG KEBUTUHAN BERSIH (NET REQUIREMENTS) ---
        net_req = []
        prev_inv = init_inv
        for i in range(n):
            net_val = demands[i] + ss - prev_inv - s_receipts[i]
            if net_val > 0:
                net_req.append(net_val)
                prev_inv = ss
            else:
                net_req.append(0)
                prev_inv = prev_inv + s_receipts[i] - demands[i]

        # HELPER UNTUK POH & RELEASE
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

        # 1. METODE LOT-FOR-LOT (L4L)
        l4l_rec = list(net_req)
        l4l_poh, l4l_rel = generate_poh_and_release(l4l_rec)
        c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        c_l4l_hold = sum(l4l_poh) * hold

        # 2. METODE LEAST UNIT COST (LUC)
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
                    status = "Terpilih (Min)"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                else:
                    status = "Stop! Biaya Naik"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                    break
            luc_iters.append(pd.DataFrame(t_log))
            luc_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
        luc_poh, luc_rel = generate_poh_and_release(luc_rec)
        c_luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        c_luc_hold = sum(luc_poh) * hold

        # 3. METODE ECONOMIC ORDER QUANTITY (EOQ)
        avg_demand = np.mean(net_req)
        eoq_size = math.ceil(math.sqrt((2 * avg_demand * setup) / hold)) if hold > 0 else 0
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
        eoq_poh, eoq_rel = generate_poh_and_release(eoq_rec)
        c_eoq_setup = sum(1 for x in eoq_rec if x > 0) * setup
        c_eoq_hold = sum(eoq_poh) * hold

        # 4. METODE PART PERIOD BALANCING (PPB)
        ppb_rec = [0] * n
        ppb_iters = []
        idx = 0
        while idx < n:
            if net_req[idx] == 0:
                idx += 1
                continue
            best_k = idx
            min_diff = float('inf')
            acc_d, acc_h = 0, 0
            t_log = []
            for k in range(idx, n):
                acc_d += net_req[k]
                acc_h += net_req[k] * hold * (k - idx)
                diff = abs(setup - acc_h)
                
                if acc_h <= setup:
                    best_k = k
                    status = "Mendekati Imbang"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Selisih |S-H|': diff, 'Status': status})
                else:
                    status = "Stop! Melebihi Batas"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Selisih |S-H|': diff, 'Status': status})
                    break
            ppb_iters.append(pd.DataFrame(t_log))
            ppb_rec[idx] = sum(net_req[idx:best_k+1])
            idx = best_k + 1
        ppb_poh, ppb_rel = generate_poh_and_release(ppb_rec)
        c_ppb_setup = sum(1 for x in ppb_rec if x > 0) * setup
        c_ppb_hold = sum(ppb_poh) * hold

        return {
            'net_req': net_req,
            'l4l': {'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
            'luc': {'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_iters},
            'eoq': {'poh': eoq_poh, 'rec': eoq_rec, 'rel': eoq_rel, 'setup': c_eoq_setup, 'hold': c_eoq_hold, 'total': c_eoq_setup + c_eoq_hold, 'size': eoq_size},
            'ppb': {'poh': ppb_poh, 'rec': ppb_rec, 'rel': ppb_rel, 'setup': c_ppb_setup, 'hold': c_ppb_hold, 'total': c_ppb_setup + c_ppb_hold, 'iters': ppb_iters}
        }

    # JALANKAN KALKULATOR
    res = calculate_multi_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    # ==========================================
    # 5. HALAMAN UTAMA - DASHBOARD SUMMARY MATRIX PREMIUM
    # ==========================================
    st.markdown("---")
    st.header("🏁 Hasil Komparasi Performa Multi-Metode")
    
    biaya_dict = {
        'Lot-for-Lot (L4L)': res['l4l']['total'], 
        'Least Unit Cost (LUC)': res['luc']['total'], 
        'Economic Order Quantity (EOQ)': res['eoq']['total'], 
        'Part Period Balancing (PPB)': res['ppb']['total']
    }
    best_method = min(biaya_dict, key=biaya_dict.get)
    max_cost = max(biaya_dict.values())
    
    # Render HTML Premium Metrics Card
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        diff_l4l = res['l4l']['total'] - biaya_dict[best_method]
        l4l_sub = f"<div style='color: #d9534f; font-size: 14px; font-weight: bold; margin-top: 4px;'>↓ Rp {diff_l4l:,.0f} Lebih Boros</div>" if diff_l4l > 0 else "<div style='color: #5cb85c; font-size: 14px; font-weight: bold; margin-top: 4px;'>🏆 Paling Optimal</div>"
        st.markdown(f"""<div style='background-color: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 5px solid #FF6B6B;'>
                        <div style='color: #666; font-size: 13px; font-weight: 500;'>Total Biaya L4L</div>
                        <div style='font-size: 24px; font-weight: bold; color: #111; margin-top: 4px;'>Rp {res['l4l']['total']:,.0f}</div>
                        {l4l_sub}</div>""", unsafe_allow_html=True)
    with m2:
        diff_luc = res['luc']['total'] - biaya_dict[best_method]
        luc_sub = f"<div style='color: #d9534f; font-size: 14px; font-weight: bold; margin-top: 4px;'>↓ Rp {diff_luc:,.0f} Lebih Boros</div>" if diff_luc > 0 else "<div style='color: #5cb85c; font-size: 14px; font-weight: bold; margin-top: 4px;'>🏆 Paling Optimal</div>"
        st.markdown(f"""<div style='background-color: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 5px solid #4D96FF;'>
                        <div style='color: #666; font-size: 13px; font-weight: 500;'>Total Biaya LUC</div>
                        <div style='font-size: 24px; font-weight: bold; color: #111; margin-top: 4px;'>Rp {res['luc']['total']:,.0f}</div>
                        {luc_sub}</div>""", unsafe_allow_html=True)
    with m3:
        diff_eoq = res['eoq']['total'] - biaya_dict[best_method]
        eoq_sub = f"<div style='color: #d9534f; font-size: 14px; font-weight: bold; margin-top: 4px;'>↓ Rp {diff_eoq:,.0f} Lebih Boros</div>" if diff_eoq > 0 else "<div style='color: #5cb85c; font-size: 14px; font-weight: bold; margin-top: 4px;'>🏆 Paling Optimal</div>"
        st.markdown(f"""<div style='background-color: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 5px solid #6BCB77;'>
                        <div style='color: #666; font-size: 13px; font-weight: 500;'>Total Biaya EOQ (Size: {res['eoq']['size']})</div>
                        <div style='font-size: 24px; font-weight: bold; color: #111; margin-top: 4px;'>Rp {res['eoq']['total']:,.0f}</div>
                        {eoq_sub}</div>""", unsafe_allow_html=True)
    with m4:
        diff_ppb = res['ppb']['total'] - biaya_dict[best_method]
        ppb_sub = f"<div style='color: #d9534f; font-size: 14px; font-weight: bold; margin-top: 4px;'>↓ Rp {diff_ppb:,.0f} Lebih Boros</div>" if diff_ppb > 0 else "<div style='color: #5cb85c; font-size: 14px; font-weight: bold; margin-top: 4px;'>🏆 Paling Optimal</div>"
        st.markdown(f"""<div style='background-color: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 5px solid #f9d949;'>
                        <div style='color: #666; font-size: 13px; font-weight: 500;'>Total Biaya PPB</div>
                        <div style='font-size: 24px; font-weight: bold; color: #111; margin-top: 4px;'>Rp {res['ppb']['total']:,.0f}</div>
                        {ppb_sub}</div>""", unsafe_allow_html=True)

    st.success(f"🏆 **Rekomendasi Keputusan:** Metode **{best_method}** menghasilkan efisiensi tata kelola logistik paling tinggi di antara seluruh opsi heuristik.")

    # ==========================================
    # 6. TABS DETAIL VIEW
    # ==========================================
    tab_grafik, t_l4l, t_luc, t_eoq, t_ppb = st.tabs(["📉 Grafik & Sensitivitas", "📋 Lot-for-Lot (L4L)", "🔍 Least Unit Cost (LUC)", "🎯 Economic Order Quantity (EOQ)", "⚖️ Part Period Balancing (PPB)"])

    with tab_grafik:
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("### Komparasi Total Biaya (Rp)")
            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.bar(biaya_dict.keys(), biaya_dict.values(), color=['#FF6B6B', '#4D96FF', '#6BCB77', '#f9d949'])
            plt.xticks(rotation=20, ha='right')
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            st.pyplot(fig)
        with cg2:
            st.markdown("### Analisis Sensitivitas Perubahan Demand")
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
            ax2.plot(labels_pct, s_l4l, marker='o', label='L4L', color='#FF6B6B')
            ax2.plot(labels_pct, s_luc, marker='s', label='LUC', color='#4D96FF')
            ax2.plot(labels_pct, s_eoq, marker='^', label='EOQ', color='#6BCB77')
            ax2.plot(labels_pct, s_ppb, marker='x', label='PPB', color='#f9d949')
            ax2.set_ylabel('Total Biaya (Rp)')
            ax2.grid(True, linestyle=':', alpha=0.6)
            ax2.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig2)

    # REUSABLE MRP RENDERER
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
            st.error(f"⚠️ **Kapasitas Terlampaui Kritis:** Stok pengaman + keputusan akumulasi lot pada {nama_metode} melanggar kapasitas limit gudang ({max_cap} unit).")

    with t_l4l:
        st.subheader("Tabel Hasil Analisis MRP - Lot-for-Lot")
        tampilkan_tabel_mrp("L4L", res['l4l'], max_capacity)

    with t_luc:
        st.subheader("Proses & Tabel Analisis MRP - Least Unit Cost")
        with st.expander("🔬 KLIK DI SINI UNTUK MELIHAT LOG ITERASI PERHITUNGAN DETAIL (LUC)"):
            format_luc = {
                'Biaya Pesan': '{:.4f}', 'Biaya Simpan': '{:.4f}', 'Total Biaya': '{:.4f}', 'LUC (Cost/Unit)': '{:.4f}'
            }
            for idx, df_iter in enumerate(res['luc']['iters']):
                st.markdown(f"**Langkah Pembentukan Lot Ke-{idx+1}:**")
                styled_df = df_iter.style.apply(highlight_stop, axis=1).format(format_luc)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                st.markdown("---")
        tampilkan_tabel_mrp("LUC", res['luc'], max_capacity)

    with t_eoq:
        st.subheader("Tabel Hasil Analisis MRP - Economic Order Quantity")
        st.info(f"💡 **Informasi Rumus:** Ukuran lot tetap (Fixed Order Quantity) EOQ dihitung bernilai **{res['eoq']['size']} unit** per pesanan.")
        tampilkan_tabel_mrp("EOQ", res['eoq'], max_capacity)

    with t_ppb:
        st.subheader("Proses & Tabel Analisis MRP - Part Period Balancing")
        with st.expander("🔬 KLIK DI SINI UNTUK MELIHAT LOG ITERASI KESEIMBANGAN PART PERIOD (PPB)"):
            format_ppb = {
                'Biaya Pesan': '{:.4f}', 'Biaya Simpan': '{:.4f}', 'Selisih |S-H|': '{:.4f}'
            }
            for idx, df_iter in enumerate(res['ppb']['iters']):
                st.markdown(f"**Langkah Pembentukan Lot Ke-{idx+1}:**")
                styled_df = df_iter.style.apply(highlight_stop, axis=1).format(format_ppb)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                st.markdown("---")
        tampilkan_tabel_mrp("PPB", res['ppb'], max_capacity)

    # --- EXPORT TO EXCEL ---
    st.markdown("---")
    st.subheader("💾 Ekspor Laporan Multi-Metode")
    with pd.ExcelWriter("Laporan_MRP_Lengkap.xlsx", engine='openpyxl') as writer:
        pd.DataFrame({'Gross Requirements': gross_req, 'Scheduled Receipts': sched_rec, 'Net Requirements': res['net_req']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Data Kebutuhan Dasar")
        pd.DataFrame({'Projected On Hand': res['l4l']['poh'], 'Planned Order Receipts': res['l4l']['rec'], 'Planned Order Releases': res['l4l']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Metode L4L")
        pd.DataFrame({'Projected On Hand': res['luc']['poh'], 'Planned Order Receipts': res['luc']['rec'], 'Planned Order Releases': res['luc']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Metode LUC")
        pd.DataFrame({'Projected On Hand': res['eoq']['poh'], 'Planned Order Receipts': res['eoq']['rec'], 'Planned Order Releases': res['eoq']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Metode EOQ")
        pd.DataFrame({'Projected On Hand': res['ppb']['poh'], 'Planned Order Receipts': res['ppb']['rec'], 'Planned Order Releases': res['ppb']['rel']}, index=[f"P{i+1}" for i in range(num_periods)]).T.to_excel(writer, sheet_name="Metode PPB")
        
    with open("Laporan_MRP_Lengkap.xlsx", "rb") as file:
        st.download_button(label="📥 Download Hasil Perhitungan 4 Metode (Excel)", data=file, file_name="Laporan_MRP_MultiMetode.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("💡 Hubungkan atau masukkan data kebutuhan di atas terlebih dahulu untuk memulai perhitungan otomasi MRP.")
