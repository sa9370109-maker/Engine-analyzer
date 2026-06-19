import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Web Page Styling ---
st.set_page_config(page_title="IC Engine P-V Analyzer", page_icon="⚙️", layout="wide")
st.title("⚙️ IC Engine Performance & P-V Diagram Analyzer")
st.markdown("Upload your Rigol Oscilloscope CSV files to generate absolute SI Unit ($Pa$ vs $m^3$) thermodynamic loops.")

# --- Sidebar Inputs ---
st.sidebar.header("1. Global Engine Parameters")
engine_type = st.sidebar.selectbox("Engine Cycle:", ["Spark Ignition (SI / Otto)", "Compression Ignition (CI / Diesel)"])
cr = st.sidebar.number_input("Compression Ratio (r_c):", min_value=1.0, value=16.5, step=0.1)
bore = st.sidebar.number_input("Bore Diameter (meters):", min_value=0.01, value=0.080, step=0.001)
stroke = st.sidebar.number_input("Stroke Length (meters):", min_value=0.01, value=0.085, step=0.001)

st.sidebar.header("2. Oscilloscope Calibration Scales")
ch1_vdiv = st.sidebar.number_input("CH1 Scale (Volt/div):", min_value=0.01, value=0.5)
p_cal = st.sidebar.number_input("Pressure Calibration Factor (Pa/Volt):", value=1000000.0)

# --- Main Layout Tabs for Test Runs ---
st.subheader("2. Test Runs Ingestion & Configuration")
tab1, tab2, tab3 = st.tabs(["Reading 1 Data", "Reading 2 Data", "Reading 3 Data"])

run_configs = {}

# Set up inputs for each data tab dynamically
for i, tab in enumerate([tab1, tab2, tab3], start=1):
    with tab:
        col1, col2 = st.columns(2)
        with col1:
            rpm = st.number_input(f"Engine RPM (Run {i}):", value=2500 + (i * 50), key=f"rpm_{i}")
            torque = st.number_input(f"Brake Torque (Nm, Run {i}):", value=20.0 + i, key=f"trq_{i}")
        with col2:
            ch1_file = st.file_uploader(f"Upload CH1 (Pressure) CSV - Run {i}", type=["csv"], key=f"ch1_{i}")
            ch2_file = st.file_uploader(f"Upload CH2 (Volume Tracker) CSV - Run {i}", type=["csv"], key=f"ch2_{i}")
        
        run_configs[i] = {"rpm": rpm, "torque": torque, "ch1": ch1_file, "ch2": ch2_file}

# --- Visual Display & Math Calculations Button ---
if st.button("🚀 Generate P-V Diagrams", type="primary"):
    
    # Engine cylinder baseline volume math definitions
    v_stroke = (np.pi * (bore ** 2) / 4) * stroke
    v_clearance = v_stroke / (cr - 1)
    
    # Create an output container for charts
    st.subheader("📊 Output Generated Diagrams Workspace")
    out_tabs = st.tabs([f"Output Plot Run 1", f"Output Plot Run 2", f"Output Plot Run 3"])
    
    for i, tab in enumerate(out_tabs, start=1):
        with tab:
            ch1_f = run_configs[i]["ch1"]
            ch2_f = run_configs[i]["ch2"]
            
            if ch1_f and ch2_f:
                # CRITICAL RIGOL FIX: Skips exactly 10 lines of text metadata header lines
                df1 = pd.read_csv(ch1_f, skiprows=10, header=None).dropna()
                df2 = pd.read_csv(ch2_f, skiprows=10, header=None).dropna()
                
                # Align exact array lengths safely
                min_rows = min(len(df1), len(df2))
                if min_rows < 10:
                    st.error(f"Error reading file run {i}: Data format corrupted or empty matrices returned.")
                    continue
                
                time = df1.iloc[:min_rows, 1].values
                ch1_v = df1.iloc[:min_rows, 2].values
                ch2_v = df2.iloc[:min_rows, 2].values
                
                # Separate/Isolate single thermodynamic cycle loop via peak boundaries
                max_v = np.max(ch1_v)
                peaks = np.where(ch1_v > max_v * 0.70)[0]
                
                if len(peaks) >= 2:
                    clean_peaks = [peaks[0]]
                    for idx in peaks:
                        if idx - clean_peaks[-1] > 30:
                            clean_peaks.append(idx)
                    idx_start, idx_end = (clean_peaks[0], clean_peaks[1]) if len(clean_peaks) >= 2 else (0, min_rows)
                else:
                    idx_start, idx_end = 0, min_rows
                
                # Apply hardware transformation metrics
                pressure_pa = ch1_v[idx_start:idx_end] * ch1_vdiv * p_cal
                ch2_v_cycle = ch2_v[idx_start:idx_end]
                
                # Normalize trace scale over cylinder volumes bounds boundaries
                v_norm = (ch2_v_cycle - np.min(ch2_v_cycle)) / ((np.max(ch2_v_cycle) - np.min(ch2_v_cycle)) or 1)
                volume_m3 = v_clearance + (v_norm * v_stroke)
                
                # Render clean Matplotlib workspace engine plot canvas loop
                fig, ax = plt.subplots(figsize=(10, 4.5))
                ax.plot(volume_m3, pressure_pa, color='#e63946', linewidth=2.5, label="Oscilloscope Ingested Cycle Data")
                ax.set_title(f"CYLINDER GAS PRESSURE-VOLUME LOOP (READING RUN NO. {i})", fontsize=12, fontweight='bold')
                ax.set_xlabel("Absolute Cylinder Volume ($m^3$)", fontsize=10)
                ax.set_ylabel("Absolute Cylinder Pressure ($Pa$)", fontsize=10)
                ax.grid(True, linestyle="--", alpha=0.6)
                ax.legend()
                
                # Display output inside current browser window container panel
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.warning(f"Please drop both Channel 1 and Channel 2 CSV files into Reading {i} configuration tab section above.")