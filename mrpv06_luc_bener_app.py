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

# FITUR IMPROVEMENT 2: Constraint Kapasitas Gudang
st.sidebar.markdown("---")
st.sidebar.header("🏬 Batasan Operasional")
max_capacity = st.sidebar.number_input("Kapasitas Maksimum Gudang (Unit)", min_value=1, value=100, step=10)

# ==========================================
# 3. AREA DATA INPUT (MANUAL ATAU UPLOAD)
# ==========================================
st.subheader("📊 Data Kebutuhan Kotor (Gross Requirements)")

input_method = st.radio("Pilih Metode Input Data:", ["Upload File (Excel / CSV)", "Gunakan Data Contoh (Template)"])

gross_req = []

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file Anda di sini (Format kolom bisa bernama: gr, GR, atau Gross_Requirement)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
            
            st.success("File berhasil di-upload!")
            st.dataframe(df_input, use_container_width=True)
            
            kolom_dicari = None
            for col in df_input.columns:
                col_clean = str(col).strip().lower().replace("_", "").replace(" ", "")
                if col_clean in ['gr', 'grossrequirement']:
                    kolom_dicari = col
                    break
            
            if kolom_dicari is not None:
                gross_req = df_input[kolom_dicari].astype(int).tolist()
            else:
                st.error("❌ Kolom Kebutuhan Kotor tidak ditemukan! Pastikan nama kolom di file Anda adalah 'gr' atau 'Gross_Requirement'.")
                
        except Exception as e:
            st.error(f"Gagal membaca file. Error: {e}")
    else:
        st.warning("Menunggu file di-upload... Silakan unggah file atau pilih opsi 'Data Contoh'.")

else:
    default_data = {
        'Periode': [f"Minggu {i}" for i in range(1, 9)],
        'gr': [30, 40, 20, 70, 40, 10, 30, 60]
    }
    df_input = pd.DataFrame(default_data)
    st.write("Menggunakan data simulasi (8 Periode):")
    st.dataframe(df_input.T, use_container_width=True)
    gross_req = df_input['gr'].tolist()

# ==========================================
# FUNCTION UNTUK PERHITUNGAN MRP (REUSABLE FOR SENSITIVITY)
# ==========================================
def calculate_mrp(demands, setup, hold, init_inv, ss, lt):
    n = len(demands)
    
    # 1. Lot-for-Lot
    l4l_net = []
    l4l_poh = []
    l4l_rec = []
    l4l_rel = [0] * n
    
    prev_inv = init_inv
    for i in range(n):
        net_val = demands[i] + ss - prev_inv
        if net_val > 0:
            l4l_net.append(net_val)
            l4l_rec.append(net_val)
            curr_poh = prev_inv + net_val - demands[i]
        else:
            l4l_net.append(0)
            l4l_rec.append(0)
            curr_poh = prev_inv - demands[i]
        l4l_poh.append(curr_poh)
        prev_inv = curr_poh
        
    for i in range(n):
        if l4l_rec[i] > 0:
            target = i - lt
            if target >= 0:
                l4l_rel[target] = l4l_rec[i]
            else:
                l4l_rel[0] += l4l_rec[i]
                
    c_l4l_setup = sum(1 for x in l4l_rec if x > 0) * setup
    c_l4l_hold = sum(l4l_poh) * hold
    
    # 2. Least Unit Cost
    luc_net = []
    prev_inv = init_inv
    for i in range(n):
        net_val = demands[i] + ss - prev_inv
        if net_val > 0:
            luc_net.append(net_val)
            prev_inv = ss
        else:
            luc_net.append(0)
            prev_inv = prev_inv - demands[i]
            
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
                t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': round(uc, 2), 'Status': status})
            else:
                status = "Stop! Biaya Naik"
                t_log.append({'Iterasi Dari': f"P{idx+1}", 'Hingga': f"P{k+1}", 'Total Unit': acc_d, 'Biaya Pesan': setup, 'Biaya Simpan': acc_h, 'Total Biaya': t_cost, 'LUC (Cost/Unit)': round(uc, 2), 'Status': status})
                break
        luc_iters.append(pd.DataFrame(t_log))
        lot_size = sum(luc_net[idx:best_k+1])
        luc_rec[idx] = lot_size
        
        target = idx - lt
        if target >= 0:
            luc_rel[target] = lot_size
        else:
            luc_rel[0] += lot_size
        idx = best_k + 1
        
    luc_poh = []
    r_inv_luc = init_inv
    for i in range(n):
        r_inv_luc += luc_rec[i] - demands[i]
        luc_poh.append(r_inv_luc)
        
    c_luc_setup = sum(1 for x in luc_rec if x > 0) * setup
    c_luc_hold = sum(luc_poh) * hold
    
    return {
        'l4l': {'net': l4l_net, 'poh': l4l_poh, 'rec': l4l_rec, 'rel': l4l_rel, 'setup': c_l4l_setup, 'hold': c_l4l_hold, 'total': c_l4l_setup + c_l4l_hold},
        'luc': {'net': luc_net, 'poh': luc_poh, 'rec': luc_rec, 'rel': luc_rel, 'setup': c_luc_setup, 'hold': c_luc_hold, 'total': c_luc_setup + c_luc_hold, 'iters': luc_iters}
    }

# ==========================================
# 4. EKSEKUSI ALGORITMA UTAMA
# ==========================================
if len(gross_req) > 0:
    res = calculate_mrp(gross_req, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
    num_periods = len(gross_req)

    # ==========================================
    # 5. DISPLAY DASHBOARD OUTPUT
    # ==========================================
    st.markdown("---")
    st.header("🏁 Hasil Komparasi Performa")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Total Biaya Lot-for-Lot (L4L)", value=f"Rp {res['l4l']['total']:,.0f}", delta="Metode Basis", delta_color="off")
    with c2:
        cost_diff = res['l4l']['total'] - res['luc']['total']
        delta_label = f"-Rp {cost_diff:,.0f} Lebih Hemat" if cost_diff >= 0 else f"+Rp {abs(cost_diff):,.0f} Lebih Mahal"
        st.metric(label="Total Biaya Least Unit Cost (LUC)", value=f"Rp {res['luc']['total']:,.0f}", delta=delta_label, delta_color="normal" if cost_diff >= 0 else "inverse")
    with c3:
        efficiency = (cost_diff / res['l4l']['total']) * 100 if res['l4l']['total'] > 0 else 0
        st.metric(label="Efisiensi Anggaran (LUC vs L4L)", value=f"{efficiency:.2f} %")

    st.markdown(" ")
    if res['luc']['total'] < res['l4l']['total']:
        st.success(f"💡 **Rekomendasi Sistem:** Struktur biaya menunjukkan metode **Least Unit Cost (LUC)** lebih optimal dengan penghematan **Rp {cost_diff:,.0f}**.")
    elif res['luc']['total'] > res['l4l']['total']:
        st.info(f"💡 **Rekomendasi Sistem:** Metode **Lot-for-Lot (L4L)** lebih ekonomis sebesar **Rp {abs(cost_diff):,.0f}**.")
    else:
        st.warning("💡 **Rekomendasi Sistem:** Kedua metode menghasilkan biaya yang setara.")

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
                sim_res = calculate_mrp(sim_demand, setup_cost, holding_cost, initial_inv, safety_stock, lead_time)
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

    # Fungsi pewarnaan tabel untuk mendeteksi Overcapacity Gudang (Mendukung Pandas versi baru dengan .map)
    def style_mrp_table(df):
        def color_poh(val):
            return 'background-color: #ffe6cc; color: #cc6600; font-weight: bold;' if val > max_capacity else ''
        
        # Menggunakan .map() jika tersedia (Pandas >= 2.1.0), jika tidak fallback ke .applymap()
        if hasattr(df.style, 'map'):
            return df.style.map(color_poh, subset=['Projected On Hand'])
        else:
            return df.style.applymap(color_poh, subset=['Projected On Hand'])

    with tab2:
        st.subheader("Tabel Hasil Analisis MRP - Lot-for-Lot")
        df_l4l_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Projected On Hand': res['l4l']['poh'],
            'Net Requirements': res['l4l']['net'],
            'Planned Order Receipts': res['l4l']['rec'],
            'Planned Order Releases': res['l4l']['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        
        st.dataframe(style_mrp_table(df_l4l_mrp), use_container_width=True)
        
        if max(res['l4l']['poh']) > max_capacity:
            st.warning(f"⚠️ **Peringatan Kapasitas:** Persediaan pada metode L4L melebihi kapasitas maksimum gudang ({max_capacity} Unit) di beberapa periode (Ditandai warna Orange).")

    with tab3:
        st.subheader("Proses & Tabel Analisis MRP - Least Unit Cost")
        
        with st.expander("🔬 KLIK DI SINI UNTUK MELIHAT LOG ITERASI PERHITUNGAN DETAIL (LUC)"):
            st.markdown("Sistem melakukan akumulasi periode demi periode. Jika biaya per unit naik, status menjadi **Stop! Biaya Naik** (Ditandai warna Merah):")
            
            def highlight_stop(row):
                return ['background-color: #ffcccc; color: black' if row['Status'] == 'Stop! Biaya Naik' else '' for _ in row]

            for idx, df_iter in enumerate(res['luc']['iters']):
                st.markdown(f"**Langkah Pembentukan Lot Ke-{idx+1}:**")
                styled_df = df_iter.style.apply(highlight_stop, axis=1)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                st.markdown("---")

        st.markdown("### Hasil Akhir Tabel MRP (LUC)")
        df_luc_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Projected On Hand': res['luc']['poh'],
            'Net Requirements': res['luc']['net'],
            'Planned Order Receipts': res['luc']['rec'],
            'Planned Order Releases': res['luc']['rel']
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        
        st.dataframe(style_mrp_table(df_luc_mrp), use_container_width=True)
        
        if max(res['luc']['poh']) > max_capacity:
            st.error(f"⚠️ **Peringatan Kapasitas Kritis:** Metode LUC mengakumulasikan lot pesanan hingga melampaui daya tampung maksimum gudang ({max_capacity} Unit). Anda mungkin memerlukan ruang tambahan atau memperkecil parameter lotting.")

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
