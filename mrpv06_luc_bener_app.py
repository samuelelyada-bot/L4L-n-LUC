import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(page_title="MRP Calculator - L4L vs LUC", layout="wide")
st.title("📦 Aplikasi Perencanaan Kebutuhan Material (MRP)")
st.caption("Pendekatan Metode Lot-for-Lot (L4L) dan Least Unit Cost (LUC) - Teknik Industri")
st.markdown("---")

# ==========================================
# 2. SIDEBAR - INPUT PARAMETER
# ==========================================
st.sidebar.header("🛠️ Parameter Input")

setup_cost = st.sidebar.number_input("Ordering / Setup Cost (Rp)", min_value=0.0, value=100000.0, step=5000.0)
holding_cost = st.sidebar.number_input("Holding Cost (Rp / unit / periode)", min_value=0.0, value=2000.0, step=500.0)
initial_inv = st.sidebar.number_input("Persediaan Awal (Initial Inventory)", min_value=0, value=50, step=5)
safety_stock = st.sidebar.number_input("Safety Stock", min_value=0, value=10, step=5)
lead_time = st.sidebar.number_input("Lead Time (Periode)", min_value=0, value=1, step=1)

# ==========================================
# 3. AREA DATA INPUT (MANUAL ATAU UPLOAD)
# ==========================================
st.subheader("📊 Data Kebutuhan Kotor (Gross Requirements)")

# Opsi metode input data
input_method = st.radio("Pilih Metode Input Data:", ["Upload File (Excel / CSV)", "Gunakan Data Contoh (Template)"])

gross_req = []

if input_method == "Upload File (Excel / CSV)":
    uploaded_file = st.file_uploader("Upload file Anda di sini (Pastikan ada kolom 'Periode' dan 'Gross_Requirement')", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
            
            st.success("File berhasil di-upload!")
            st.dataframe(df_input, use_container_width=True)
            gross_req = df_input['Gross_Requirement'].tolist()
        except Exception as e:
            st.error(f"Gagal membaca file. Pastikan format kolom sesuai. Error: {e}")
    else:
        st.warning("Menunggu file di-upload... Silakan unggah file atau pilih opsi 'Data Contoh'.")

else:
    # Data default untuk contoh/brainstorming
    default_data = {
        'Periode': [f"Minggu {i}" for i in range(1, 9)],
        'Gross_Requirement': [30, 40, 20, 70, 40, 10, 30, 60]
    }
    df_input = pd.DataFrame(default_data)
    st.write("Menggunakan data simulasi (8 Periode):")
    st.dataframe(df_input.T, use_container_width=True)
    gross_req = df_input['Gross_Requirement'].tolist()

# ==========================================
# 4. LOGIKA & ALGORITMA MRP
# ==========================================
if len(gross_req) > 0:
    num_periods = len(gross_req)
    
    # --- PROSES AWAL: Hitung Net Requirements ---
    net_req = []
    projected_on_hand = []
    
    current_inv = initial_inv
    for i in range(num_periods):
        # Proyeksi persediaan sebelum dikurangi kebutuhan periode ini
        # Kebutuhan bersih muncul jika inventory dikurangi safety stock tidak cukup memenuhi gross req
        needed = gross_req[i] + safety_stock - current_inv
        if needed > 0:
            net_amt = gross_req[i] - max(0, current_inv - safety_stock)
            net_req.append(net_amt)
            current_inv = safety_stock # Inventory tersisa di level safety stock setelah dipenuhi kelak
        else:
            net_req.append(0)
            current_inv = current_inv - gross_req[i]
        projected_on_hand.append(current_inv)

    # --- METODE 1: LOT-FOR-LOT (L4L) ---
    l4l_rec = net_req.copy()
    l4l_rel = [0] * num_periods
    for i in range(num_periods):
        if l4l_rec[i] > 0 and (i - lead_time) >= 0:
            l4l_rel[i - lead_time] = l4l_rec[i]
            
    # Hitung inventory riil & biaya untuk L4L
    l4l_on_hand = []
    inv_l4l = initial_inv
    total_l4l_setup = 0
    total_l4l_hold = 0
    
    for i in range(num_periods):
        inv_l4l += l4l_rec[i] - gross_req[i]
        l4l_on_hand.append(inv_l4l)
        if l4l_rec[i] > 0:
            total_l4l_setup += setup_cost
        total_l4l_hold += (inv_l4l * holding_cost)
        
    total_cost_l4l = total_l4l_setup + total_l4l_hold

    # --- METODE 2: LEAST UNIT COST (LUC) ---
    luc_rec = [0] * num_periods
    luc_rel = [0] * num_periods
    luc_iterations = [] # Untuk menampung log langkah iterasi
    
    i = 0
    while i < num_periods:
        if net_req[i] == 0:
            i += 1
            continue
            
        # Mulai iterasi pencarian unit cost terkecil
        best_k = i
        min_unit_cost = float('inf')
        accum_demand = 0
        accum_holding = 0
        
        temp_iter_log = []
        
        for k in range(i, num_periods):
            accum_demand += net_req[k]
            # Biaya simpan dihitung berdasarkan jarak periode dari titik pemesanan (i)
            accum_holding += net_req[k] * holding_cost * (k - i)
            total_temp_cost = setup_cost + accum_holding
            
            if accum_demand > 0:
                unit_cost = total_temp_cost / accum_demand
            else:
                unit_cost = float('inf')
                
            status = "Lanjut"
            if unit_cost < min_unit_cost:
                min_unit_cost = unit_cost
                best_k = k
                status = "Terpilih (Min)"
            elif unit_cost > min_unit_cost:
                status = "Stop! Biaya Naik"
                temp_iter_log.append({
                    'Iterasi Dari': f"P{i+1}", 'Hingga': f"P{k+1}", 'Total Unit': accum_demand,
                    'Biaya Pesan': setup_cost, 'Biaya Simpan': accum_holding, 
                    'Total Biaya': total_temp_cost, 'LUC (Cost/Unit)': round(unit_cost, 2), 'Status': status
                })
                break
                
            temp_iter_log.append({
                'Iterasi Dari': f"P{i+1}", 'Hingga': f"P{k+1}", 'Total Unit': accum_demand,
                'Biaya Pesan': setup_cost, 'Biaya Simpan': accum_holding, 
                'Total Biaya': total_temp_cost, 'LUC (Cost/Unit)': round(unit_cost, 2), 'Status': status
            })
            
        luc_iterations.append(pd.DataFrame(temp_iter_log))
        
        # Eksekusi lot size optimal yang terpilih
        lot_size = sum(net_req[i:best_k+1])
        luc_rec[i] = lot_size
        if (i - lead_time) >= 0:
            luc_rel[i - lead_time] = lot_size
            
        # Lompat ke periode setelah blok yang digabungkan tadi
        i = best_k + 1

    # Hitung inventory riil & biaya untuk LUC
    luc_on_hand = []
    inv_luc = initial_inv
    total_luc_setup = 0
    total_luc_hold = 0
    
    for i in range(num_periods):
        inv_luc += luc_rec[i] - gross_req[i]
        luc_on_hand.append(inv_luc)
        if luc_rec[i] > 0:
            total_luc_setup += setup_cost
        total_luc_hold += (inv_luc * holding_cost)
        
    total_cost_luc = total_luc_setup + total_luc_hold

    # ==========================================
    # 5. DISPLAY 3 PILAR UTAMA (DASHBOARD OUTPUT)
    # ==========================================
    st.markdown("---")
    st.header("🏁 Hasil Komparasi Performa")
    
    # PILAR 3: Dasbor Total Biaya (Cost Summary) via Metric Columns
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Total Biaya Lot-for-Lot (L4L)", 
                  value=f"Rp {total_cost_l4l:,.0f}", 
                  delta="Metode Basis", delta_color="off")
    with c2:
        cost_diff = total_cost_l4l - total_cost_luc
        delta_label = f"-Rp {cost_diff:,.0f} Lebih Hemat" if cost_diff >= 0 else f"+Rp {abs(cost_diff):,.0f} Lebih Mahal"
        st.metric(label="Total Biaya Least Unit Cost (LUC)", 
                  value=f"Rp {total_cost_luc:,.0f}", 
                  delta=delta_label, delta_color="normal" if cost_diff >= 0 else "inverse")
    with c3:
        efficiency = (cost_diff / total_cost_l4l) * 100 if total_cost_l4l > 0 else 0
        st.metric(label="Efisiensi Anggaran (LUC vs L4L)", value=f"{efficiency:.2f} %")

    # Rekomendasi Pintar Operasional
    st.markdown(" ")
    if total_cost_luc < total_cost_l4l:
        st.success(f"💡 **Rekomendasi Sistem:** Struktur biaya Anda menunjukkan bahwa metode **Least Unit Cost (LUC)** lebih optimal dengan penghematan sebesar **Rp {cost_diff:,.0f}**.")
    elif total_cost_luc > total_cost_l4l:
        st.info(f"💡 **Rekomendasi Sistem:** Metode **Lot-for-Lot (L4L)** terbukti lebih ekonomis untuk pola *demand* ini sebesar **Rp {abs(cost_diff):,.0f}**.")
    else:
        st.warning("💡 **Rekomendasi Sistem:** Kedua metode menghasilkan total biaya operasional yang sama persis.")

    # Tampilan Detail Menggunakan Kombinasi Tabs
    tab1, tab2, tab3 = st.tabs(["📉 Grafik Tren Finansial", "📋 Metode Lot-for-Lot (L4L)", "🔍 Metode Least Unit Cost (LUC)"])

    with tab1:
        st.subheader("Perbandingan Akumulasi Struktur Biaya")
        fig, ax = plt.subplots(figsize=(10, 4))
        categories = ['Biaya Pesan (Setup)', 'Biaya Simpan (Holding)', 'Total Biaya']
        
        l4l_costs = [total_l4l_setup, total_l4l_hold, total_cost_l4l]
        luc_costs = [total_luc_setup, total_luc_hold, total_cost_luc]
        
        x = np.arange(len(categories))
        width = 0.35
        
        ax.bar(x - width/2, l4l_costs, width, label='L4L', color='#FF6B6B')
        ax.bar(x + width/2, luc_costs, width, label='LUC', color='#4D96FF')
        
        ax.set_ylabel('Rupiah (Rp)')
        ax.set_title('Komparasi Komponen Biaya Eksplisit')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        
        st.pyplot(fig)

    with tab2:
        st.subheader("Tabel Hasil Analisis MRP - Lot-for-Lot")
        df_l4l_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Projected On Hand': l4l_on_hand,
            'Net Requirements': net_req,
            'Planned Order Receipts': l4l_rec,
            'Planned Order Releases': l4l_rel
        }, index=[f"P{i+1}" for i in range(num_periods)]).T
        st.dataframe(df_l4l_mrp, use_container_width=True)

    with tab3:
        # PINTU TUNTUTAN USER: Tampilkan tabel iterasi LUC terlebih dahulu di dalam Expander
        st.subheader("Proses & Tabel Analisis MRP - Least Unit Cost")
        
        with st.expander("🔬 KLIK DI SINI UNTUK MELIHAT LOG ITERASI PERHITUNGAN DETAIL (LUC)"):
            st.markdown("Sistem melakukan perhitungan penambahan periode kumulatif untuk mencari ongkos per unit paling minimal:")
            for idx, df_iter in enumerate(luc_iterations):
                st.markdown(f"**Langkah Pembentukan Lot Ke-{idx+1}:**")
                st.dataframe(df_iter, hide_index=True, use_container_width=True)
                st.markdown("---")

        # Tabel Utama MRP LUC di bawah log iterasi
        st.markdown("### Hasil Akhir Tabel MRP (LUC)")
df_luc_mrp = pd.DataFrame({
            'Gross Requirements': gross_req,
            'Projected On Hand': luc_on_hand,  # <--- Sudah diganti langsung ke variabelnya
            'Net Requirements': net_req,
            'Planned Order Receipts': luc_rec,
            'Planned Order Releases': luc_rel
        }, index=[f"P{i+1}" for i in range(num_periods)]).T

# --- FITUR DOWNLOAD REPORT ---
    st.markdown(" ")
    st.subheader("💾 Ekspor Hasil Perhitungan")
    
    # Membuat file excel di memory ram untuk langsung di-download
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
