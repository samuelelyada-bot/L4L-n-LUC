import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(page_title="MRP Calculator - L4L vs LUC", layout="wide")
st.title("📦 Aplikasi Perencanaan Kebutuhan Material (MRP)")
st.caption("Pendekatan Metode Lot-for-Lot (L4L) dan Least Unit Cost (LUC) - Edisi Decision Support System")
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
# HELPER: FUNGSI DETEKSI PINTAR NAMA KOLOM
# ==========================================
def dapatkan_kolom_cocok(columns, targets):
    for col in columns:
        col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
        if col_clean in targets:
            return col
    return None

# ==========================================
# 3. AREA DATA INPUT (UPLOAD / MANUAL / TEMPLATE)
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
                st.error("❌ Kolom Kebutuhan Kotor (GR) tidak terdeteksi otomatis. Pastikan nama kolom berisi nama 'gr' atau 'Gross_Requirement'.")
                
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
    
    st.info("💡 **Petunjuk:** Silakan isi langsung data kebutuhan (Gross Requirements) dan penerimaan terjadwal (Scheduled Receipts) pada baris tabel di bawah ini.")
    df_kerja = st.data_editor(df_empty, use_container_width=True, hide_index=True)

else:
    default_data = {
        'Periode': [f"P{i+1}" for i in range(1, 9)],
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
    # FUNCTION PERHITUNGAN ALGORITMA MRP
    # ==========================================
    def calculate_mrp(demands, s_receipts, setup, hold, init_inv, ss, lt):
        n = len(demands)
        
        # 1. Lot-for-Lot (L4L)
        l4l_net = []
        l4l_poh = []
        l4l_rec = []
        l4l_rel = [0] * n
        
        prev_inv = init_inv
        for i in range(n):
            net_val = demands[i] + ss - prev_inv - s_receipts[i]
            if net_val > 0:
                l4l_net.append(net_val)
                l4l_rec.append(net_val)
                curr_poh = prev_inv + s_receipts[i] + net_val - demands[i]
            else:
                l4l_net.append(0)
                l4l_rec.append(0)
                curr_poh = prev_inv + s_receipts[i] - demands[i]
            l4l_poh.append(curr_poh)
            prev_inv = curr_poh
            
        for i in range(n):
            if l4l_rec[i] > 0:
                target = i - lt
                if target >= 0:
                    l4l_rel[target] += l4l_rec[i]
                else:
                    l4l_rel[0] += l4l_rec[i]
                    
        c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
        c_l4l_hold = sum(l4l_poh) * hold
        
        # 2. Least Unit Cost (LUC)
        luc_net = []
        prev_inv = init_inv
        for i in range(n):
            net_val = demands[i] + ss - prev_inv - s_receipts[i]
            if net_val > 0:
                luc_net.append(net_val)
                prev_inv = ss
            else:
                luc_net.append(0)
                prev_inv = prev_inv + s_receipts[i] - demands[i]
                
        luc_rec = [0] * n
        luc_rel = [0] * n
        luc_iters = []
        
        idx = 0
        while idx < n:
            if luc_net[idx] == 0:
                idx += 1
                continue
            best_k = idx
            min_uc = float('inf')
            acc_d = 0
            acc_h = 0
            t_log = []
            
            for k in range(idx, n):
                acc_d += luc_net[k]
                acc_h += luc_net[k] * hold * (k - idx)
                t_cost = setup + acc_h
                uc = t_cost / acc_d if acc_d > 0 else float('inf')
                
                status = "Lanjut"
                if uc <= min_uc:
                    min_uc = uc
                    best_k = k
                    status = "Terpilih (Min)"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                else:
                    status = "Stop! Biaya Naik"
                    t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': uc, 'Status': status})
                    break
            luc_iters.append(pd.DataFrame(t_log))
            lot_size = sum(luc_net[idx:best_k+1])
            luc_rec[idx] = lot_size
            idx = best_k + 1
            
        for i in range(n):
            if luc_rec[i] > 0:
                target = i - lt
                if target >= 0:
                    luc_rel[target] += luc_rec[i]
                else:
                    luc_rel[0] += luc_rec[i]
            
        luc_poh = []
        r_inv_luc = init_inv
        for i in range(n):
            r_inv_luc += s_receipts[i] + luc_rec[i] - demands[i]
            luc_poh.append(r_inv_luc)
            
        c_luc_setup = sum(1 for x in luc_rec if x > 0) * setup
        c_luc_hold = sum(luc_poh) * hold
        
        return {
            'l4l': {'net': l4l_net, 'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
            'luc': {'net': luc_net, 'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_iters}
        }

    # ==========================================
    # 4. EKSEKUSI PROGRAM JALAN
    # ==========================================
    res = calculate_mrp(gross_req, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    # ==========================================
    # 5. DISPLAY DASHBOARD OUTPUT (FIX LOGIKA PANAH & WARNA)
    # ==========================================
    st.markdown("---")
    st.header("🏁 Hasil Komparasi Performa")
    
    cost_diff = res['l4l']['total'] - res['luc']['total']
    abs_diff = abs(cost_diff)
    
    # Rekayasa nilai delta agar arah panah st.metric sinkron dengan logika industri
    # Menghemat = Biaya turun (minus), Memboros = Biaya naik (positif)
    if cost_diff > 0:
        # Kasus: LUC Lebih Hemat (L4L Lebih Boros)
        l4l_delta_val = abs_diff     # Positif -> Panah ke atas (Merah karena inverse)
        l4l_delta_txt = f"Rp {abs_diff:,.0f} Lebih Boros"
        l4l_color_mode = "inverse"   
        
        luc_delta_val = -abs_diff    # Negatif -> Panah ke bawah (Hijau karena inverse)
        luc_delta_txt = f"Rp {abs_diff:,.0f} Lebih Hemat"
        luc_color_mode = "inverse"   
        pemenang = "LUC"
    elif cost_diff < 0:
        # Kasus: L4L Lebih Hemat (LUC Lebih Boros)
        l4l_delta_val = -abs_diff    # Negatif -> Panah ke bawah (Hijau karena inverse)
        l4l_delta_txt = f"Rp {abs_diff:,.0f} Lebih Hemat"
        l4l_color_mode = "inverse"
        
        luc_delta_val = abs_diff     # Positif -> Panah ke atas (Merah karena inverse)
        luc_delta_txt = f"Rp {abs_diff:,.0f} Lebih Boros"
        luc_color_mode = "inverse"
        pemenang = "L4L"
    else:
        l4l_delta_val = 0
        l4l_delta_txt = "Biaya Setara"
        l4l_color_mode = "off"
        
        luc_delta_val = 0
        luc_delta_txt = "Biaya Setara"
        luc_color_mode = "off"
        pemenang = "Seimbang"

    efficiency = (abs_diff / max(res['l4l']['total'], 1)) * 100

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            label="Total Biaya Lot-for-Lot (L4L)",
            value=f"Rp {res['l4l']['total']:,.0f}",
            delta=l4l_delta_txt,
            delta_color=l4l_color_mode
        )
    with c2:
        st.metric(
            label="Total Biaya Least Unit Cost (LUC)",
            value=f"Rp {res['luc']['total']:,.0f}",
            delta=luc_delta_txt,
            delta_color=luc_color_mode
        )
    with c3:
        st.metric(
            label=f"Efisiensi Anggaran ({pemenang})",
            value=f"{efficiency:.2f} %",
            delta="Optimalisasi Biaya" if cost_diff != 0 else "Seimbang",
            delta_color="off"
        )

    st.markdown(" ")
    if cost_diff > 0:
        st.success(f"💡 **Rekomendasi Sistem:** Struktur biaya menunjukkan metode **Least Unit Cost (LUC)** lebih optimal dengan penghematan **Rp {abs_diff:,.0f}** dibanding L4L.")
    elif cost_diff < 0:
        st.info(f"💡 **Rekomendasi Sistem:** Metode **Lot-for-Lot (L4L)** justru lebih ekonomis sebesar **Rp {abs_diff:,.0f}** dibanding LUC.")
    else:
        st.warning("💡 **Rekomendasi Sistem:** Kedua metode menghasilkan struktur biaya yang sama persis.")

    tab1, tab2, tab3 = st.tabs(["📉 Analisis Finansial & Sensitivitas", "📋 Metode Lot-for-Lot (L4L)", "🔍 Metode Least Unit Cost (LUC)"])

    with tab1:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("### Perbandingan Komponen Biaya")
            fig, ax = plt.subplots(figsize=(6, 4))
            categories = ['Biaya Pesan', 'Biaya Simpan', 'Total Biaya']
            l4l_costs = [res['l4l']['setup'], res['l4l']['hold'], res['l4l']['total']]
            luc_costs = [res['luc']['setup'], res['luc']['hold'], res['luc']['total']]
            
            x = np.arange(len(categories))
            width = 0.35
            ax.bar(x - width/2, l4l_costs, width, label='L4L', color='#FF6B6B')
            ax.bar(x + width/2, luc_costs, width, label='LUC', color='#4D96FF')
            ax.set_ylabel('Rupiah (Rp)')
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            st.pyplot(fig)
            
        with col_g2:
            st.markdown("### Grafik Analisis Sensitivitas (Perubahan Demand)")
            scale_factors = np.arange(0.7, 1.35, 0.05)
            l4l_sens = []
            luc_sens = []
            percentages = []
            
            for f in scale_factors:
                sim_demand = [max(1, int(d * f)) for d in gross_req]
                sim_res = calculate_mrp(sim_demand, sched_rec, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
                l4l_sens.append(sim_res['l4l']['total'])
                luc_sens.append(sim_res['luc']['total'])
                percentages.append(f"{int((f-1)*100):+d}%")
                
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(percentages, l4l_sens, marker='o', label='Total Cost L4L', color='#FF6B6B', linewidth=2)
            ax2.plot(percentages, luc_sens, marker='s', label='Total Cost LUC', color='#4D96FF', linewidth=2)
            ax2.set_ylabel('Total Biaya (Rp)')
            ax2.set_xlabel('Fluktuasi Kebutuhan Kotor (Gross Demand)')
            ax2.grid(True, linestyle=':', alpha=0.6)
            ax2.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig2)

    # --- FUNGSI STYLING TABEL ---
    def get_styled_mrp_table(df_mrp_transposed):
        def highlight_row_capacity(row):
            if row.name == 'Projected On Hand':
                return ['background-color: #ffe6cc; color: #cc6600; font-weight: bold;' if val > max_capacity else '' for val in row]
            return [''] * len(row)
        return df_mrp_transposed.style.apply(highlight_row_capacity, axis=1)

    with tab2:
        st.subheader("Tabel Hasil Analisis MRP - Lot-for-Lot")
        df_l4l_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': res['l4l']['poh'],
            'Net Requirements': res['l4l']['net'],
            'Planned Order Receipts': res['l4l']['rec'],
            'Planned Order Releases': res['l4l']['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        
        st.dataframe(get_styled_mrp_table(df_l4l_mrp), use_container_width=True)
        
        if max(res['l4l']['poh']) > max_capacity:
            st.warning(f"⚠️ **Peringatan Kapasitas:** Persediaan pada metode L4L melebihi kapasitas maksimum gudang ({max_capacity} Unit).")

    with tab3:
        st.subheader("Proses & Tabel Analisis MRP - Least Unit Cost")
        
        with st.expander("🔬 KLIK DI SINI UNTUK MELIHAT LOG ITERASI PERHITUNGAN DETAIL (LUC)"):
            def highlight_stop(row):
                return ['background-color: #ffcccc; color: black' if row['Status'] == 'Stop! Biaya Naik' else '' for _ in row]

            # Mengatur formatter presisi desimal: 4 angka di belakang koma untuk kolom biaya
            format_dict = {
                'Biaya Pesan': '{:.4f}',
                'Biaya Simpan': '{:.4f}',
                'Total Biaya': '{:.4f}',
                'LUC (Cost/Unit)': '{:.4f}'
            }

            for idx, df_iter in enumerate(res['luc']['iters']):
                st.markdown(f"**Langkah Pembentukan Lot Ke-{idx+1}:**")
                # Gabungkan highlight baris merah dengan formatting presisi 4 desimal
                styled_df = df_iter.style.apply(highlight_stop, axis=1).format(format_dict)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                st.markdown("---")

        st.markdown("### Hasil Akhir Tabel MRP (LUC)")
        df_luc_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Scheduled Receipts': sched_rec,
            'Projected On Hand': res['luc']['poh'],
            'Net Requirements': res['luc']['net'],
            'Planned Order Receipts': res['luc']['rec'],
            'Planned Order Releases': res['luc']['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        
        st.dataframe(get_styled_mrp_table(df_luc_mrp), use_container_width=True)
        
        if max(res['luc']['poh']) > max_capacity:
            st.error(f"⚠️ **Peringatan Kapasitas Kritis:** Metode LUC mengakumulasikan lot pesanan hingga melampaui daya tampung gudang ({max_capacity} Unit).")

    # --- FITUR DOWNLOAD REPORT ---
    st.markdown(" ")
    st.subheader("💾 Ekspor Hasil Perhitungan")
    
    with pd.ExcelWriter("Hasil_MRP_Komparasi.xlsx", engine='openpyxl') as writer:
        df_l4l_mrp.to_excel(writer, sheet_name="Metode L4L")
        df_luc_mrp.to_excel(writer, sheet_name="Metode LUC")
        
    with open("Hasil_MRP_Komparasi.xlsx", "rb") as file:
        st.download_button(
            label="📥 Download Hasil Perhitungan Berformat Excel",
            data=file,
            file_name="Hasil_MRP_Komparasi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("💡 Hubungkan atau masukkan data kebutuhan di atas terlebih dahulu untuk memulai perhitungan otomasi MRP.")
