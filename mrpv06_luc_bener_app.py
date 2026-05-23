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
    uploaded_file = st.file_uploader("Upload file Anda di sini (Format kolom bisa bernama: gr, GR, atau Gross_Requirement)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
            
            st.success("File berhasil di-upload!")
            st.dataframe(df_input, use_container_width=True)
            
            # --- LOGIKA DETEKSI KOLOM OTOMATIS (Bisa 'gr', 'GR', dll) ---
            # Mengubah semua nama kolom menjadi huruf kecil & hapus spasi/underscore biar fleksibel
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
    # Data default untuk contoh/brainstorming
    default_data = {
        'Periode': [f"Minggu {i}" for i in range(1, 9)],
        'gr': [30, 40, 20, 70, 40, 10, 30, 60]
    }
    df_input = pd.DataFrame(default_data)
    st.write("Menggunakan data simulasi (8 Periode):")
    st.dataframe(df_input.T, use_container_width=True)
    gross_req = df_input['gr'].tolist()

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
        needed = gross_req[i] + safety_stock - current_inv
        if needed > 0:
            net_amt = gross_req[i] - max(0, current_inv - safety_stock)
            net_req.append(net_amt)
            current_inv = safety_stock
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
    luc_iterations = []
    
    i = 0
    while i < num_periods:
        if net_req[i] == 0:
            i += 1
            continue
            
        best_k = i
        min_unit_cost = float('inf')
        accum_demand = 0
        accum_holding = 0
        
        temp_iter_log = []
        
        for k in range(i, num_periods):
            accum_demand += net_req[k]
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
        
        lot_size = sum(net_req[i:best_k+1])
        luc_rec[i] = lot_size
        if (i - lead_time) >= 0:
            luc_rel[i - lead_time] = lot_size
            
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
    # 5. DISPLAY DASHBOARD OUTPUT
    # ==========================================
    st.markdown("---")
    st.header("🏁 Hasil Komparasi Performa")
    
    c1, c2, c3 = st.columns(3)
    with c1:
