# =============================================================================
# SISTEM ANALISIS DATA RIO — Versi Web (Streamlit)
# Konversi dari main.py v4.0 ke antarmuka web
# =============================================================================

import streamlit as st
import pandas as pd
import kalkulator_stat as ks

# =============================================================================
# KONFIGURASI HALAMAN
# =============================================================================

st.set_page_config(
    page_title="Sistem Analisis Data RIO",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# JUDUL UTAMA
# =============================================================================

st.title("📊 Sistem Analisis Data RIO")
st.caption("Versi Web — Powered by Streamlit")
st.divider()

# =============================================================================
# FUNGSI BANTU — Google Drive
# =============================================================================

def konversi_link_drive(link):
    """
    Mengubah link Google Drive biasa menjadi link download langsung.
    Contoh input : https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    Contoh output: https://drive.google.com/uc?export=download&id=FILE_ID
    """
    import re
    # Coba ekstrak FILE_ID dari berbagai format link Drive
    pola = [
        r'/file/d/([a-zA-Z0-9_-]+)',   # format /file/d/ID/view
        r'id=([a-zA-Z0-9_-]+)',          # format ?id=ID
        r'/d/([a-zA-Z0-9_-]+)',          # format /d/ID
    ]
    for p in pola:
        cocok = re.search(p, link)
        if cocok:
            file_id = cocok.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return None


def baca_dari_drive(link):
    """Membaca file CSV atau Excel dari link Google Drive."""
    import requests
    from io import BytesIO

    url_download = konversi_link_drive(link)
    if url_download is None:
        raise ValueError("Format link Google Drive tidak dikenali. Pastikan link sudah benar.")

    resp = requests.get(url_download, timeout=15)

    if resp.status_code != 200:
        raise ValueError(f"Gagal mengunduh file (status {resp.status_code}). Pastikan file sudah di-share publik.")

    # Deteksi tipe file dari header atau coba keduanya
    content_type = resp.headers.get("Content-Type", "")
    data = BytesIO(resp.content)

    if "spreadsheetml" in content_type or link.endswith(".xlsx"):
        return pd.read_excel(data, engine="openpyxl")
    else:
        # Coba Excel dulu, fallback ke CSV
        try:
            return pd.read_excel(data, engine="openpyxl")
        except Exception:
            data.seek(0)
            return pd.read_csv(data)


# =============================================================================
# SIDEBAR — Upload File & Navigasi
# =============================================================================

with st.sidebar:
    st.header("📁 Import Data")

    # Pilihan sumber data
    sumber = st.radio(
        "Sumber Data",
        ["💻 Upload dari Komputer", "☁️ Google Drive"],
        help="Pilih dari mana data akan diambil"
    )

    file_upload  = None
    drive_link   = None

    if sumber == "💻 Upload dari Komputer":
        file_upload = st.file_uploader(
            "Upload file CSV atau Excel",
            type=["csv", "xlsx", "xls"],
            help="Format yang didukung: .csv, .xlsx, .xls"
        )

    else:
        st.markdown("**Cara pakai:**")
        st.markdown("""
        1. Buka file di Google Drive
        2. Klik kanan → **Share**
        3. Ubah akses ke **Anyone with the link**
        4. **Copy link** dan paste di bawah
        """)
        drive_link = st.text_input(
            "Paste link Google Drive di sini",
            placeholder="https://drive.google.com/file/d/..."
        )

    st.divider()
    st.header("🔍 Pilih Analisis")
    menu = st.radio(
        "Menu Analisis",
        options=[
            "A. Statistik Deskriptif",
            "B. Uji Perbedaan",
            "C. CFA (Validitas Konstruk)",
            "D. Uji Korelasi",
            "E. Uji Reliabilitas",
            "F. Diagnostik Asumsi",
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("💡 Sistem Analisis Data RIO v4.0")

# =============================================================================
# BACA FILE
# =============================================================================

df = None

# Jalur 1: Upload dari komputer
if sumber == "💻 Upload dari Komputer":
    if file_upload is None:
        st.info("👈 Silakan upload file CSV atau Excel terlebih dahulu di sidebar kiri.")
        st.stop()
    try:
        if file_upload.name.endswith('.csv'):
            df = pd.read_csv(file_upload)
        else:
            df = pd.read_excel(file_upload, engine='openpyxl')
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.stop()

# Jalur 2: Google Drive
else:
    if not drive_link:
        st.info("👈 Paste link Google Drive di sidebar kiri untuk memulai.")
        st.stop()
    try:
        with st.spinner("Mengunduh file dari Google Drive..."):
            df = baca_dari_drive(drive_link)
        st.success("✅ File berhasil diambil dari Google Drive!")
    except Exception as e:
        st.error(f"Gagal mengambil file dari Google Drive: {e}")
        st.markdown("""
        **Kemungkinan penyebab:**
        - File belum di-share publik (*Anyone with the link*)
        - Link tidak valid atau sudah kedaluwarsa
        - File bukan format CSV atau Excel
        """)
        st.stop()

# Tampilkan preview data
with st.expander(f"👁️ Preview Data: {file_upload.name}", expanded=True):
    st.dataframe(df.head(10), use_container_width=True)
    st.caption(f"Total baris: {len(df)} | Total kolom: {len(df.columns)}")

st.divider()

# Daftar kolom numerik dan kategorikal untuk dipakai di banyak menu
kolom_semua     = list(df.columns)
kolom_numerik   = df.select_dtypes(include='number').columns.tolist()
kolom_kategori  = df.select_dtypes(exclude='number').columns.tolist()


# =============================================================================
# FUNGSI BANTU — Interpretasi
# =============================================================================

def badge_normal(p):
    return "🟢 NORMAL" if p > 0.05 else "🔴 TIDAK NORMAL"

def badge_sig(p):
    return "🟢 SIGNIFIKAN" if p < 0.05 else "🔴 TIDAK SIGNIFIKAN"

def kekuatan_korelasi(r):
    a = abs(r)
    if a > 0.7:   return "Sangat Kuat"
    elif a > 0.5: return "Kuat"
    elif a > 0.3: return "Moderat"
    else:         return "Lemah"


# =============================================================================
# MENU A — STATISTIK DESKRIPTIF
# =============================================================================

if menu == "A. Statistik Deskriptif":
    st.subheader("📋 Statistik Deskriptif")

    tab1, tab2 = st.tabs(["📊 Descriptive Statistics", "📈 Frequency Table"])

    # ── Tab 1: Descriptive Statistics ─────────────────────────────────────────
    with tab1:
        kolom = st.selectbox("Pilih kolom numerik", kolom_numerik, key="desk_num")

        if st.button("Hitung", key="btn_desk"):
            data_raw = pd.to_numeric(df[kolom], errors='coerce').dropna()

            v, mis, mo, med, me, sd, rg, mi, ma = ks.hitung_deskriptif_lengkap(data_raw)
            n_norm, stat_sw, p_norm = ks.uji_normalitas_shapiro(data_raw)
            p_tampil = f"{p_norm:.3f}" if p_norm >= 0.001 else "< .001"

            # Tampilkan dalam dua kolom
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Statistik Dasar**")
                hasil_desk = pd.DataFrame({
                    "Statistik": ["Valid", "Missing", "Mean", "Median", "Mode",
                                  "Std. Deviation", "Range", "Minimum", "Maximum"],
                    "Nilai": [v, mis, f"{me:.2f}", f"{med:.2f}", f"{mo:.2f}",
                              f"{sd:.3f}", f"{rg:.2f}", f"{mi:.2f}", f"{ma:.2f}"]
                })
                st.dataframe(hasil_desk, hide_index=True, use_container_width=True)

            with col2:
                st.markdown("**Uji Normalitas Shapiro-Wilk**")
                hasil_norm = pd.DataFrame({
                    "": ["W Statistic", "P-value", "Status"],
                    "Hasil": [f"{stat_sw:.3f}", p_tampil, badge_normal(p_norm)]
                })
                st.dataframe(hasil_norm, hide_index=True, use_container_width=True)

                if p_norm > 0.05:
                    st.success("Data terdistribusi normal. Lanjutkan dengan uji parametrik.")
                else:
                    st.warning("Data tidak normal. Pertimbangkan uji non-parametrik.")

    # ── Tab 2: Frequency Table ─────────────────────────────────────────────────
    with tab2:
        kolom_freq = st.selectbox("Pilih kolom kategorikal", kolom_semua, key="freq_col")

        if st.button("Hitung Frekuensi", key="btn_freq"):
            seri          = df[kolom_freq].dropna()
            total_valid   = len(seri)
            total_missing = len(df[kolom_freq]) - total_valid

            freq      = seri.value_counts()
            persen    = seri.value_counts(normalize=True) * 100
            kumulatif = persen.cumsum()

            tabel_freq = pd.DataFrame({
                "Kategori"    : freq.index,
                "Frequency"   : freq.values,
                "Percent (%)" : persen.values.round(1),
                "Cumulative (%)": kumulatif.values.round(1)
            })

            st.dataframe(tabel_freq, hide_index=True, use_container_width=True)

            col1, col2 = st.columns(2)
            col1.metric("Total Valid", total_valid)
            col2.metric("Missing", total_missing)

            # Peringatan jika kolom ini sebetulnya numerik
            if pd.to_numeric(seri, errors='coerce').notna().all():
                st.info("💡 Kolom ini berisi angka. Untuk mean/SD gunakan tab Descriptive Statistics.")


# =============================================================================
# MENU B — UJI PERBEDAAN
# =============================================================================

elif menu == "B. Uji Perbedaan":
    st.subheader("⚖️ Uji Perbedaan (Smart T-Test / Mann-Whitney)")

    kol_kat  = st.selectbox("Kolom Kategori (Grup)", kolom_semua)
    kol_skor = st.selectbox("Kolom Skor (Numerik)", kolom_numerik)

    # Ambil daftar grup
    semua_grup = df[kol_kat].dropna().unique().tolist()

    if len(semua_grup) < 2:
        st.error("Kolom kategori harus memiliki minimal 2 grup.")
        st.stop()

    col1, col2 = st.columns(2)
    g1 = col1.selectbox("Grup 1", semua_grup, index=0)
    g2 = col2.selectbox("Grup 2", semua_grup, index=1)

    if st.button("Jalankan Uji Perbedaan"):
        if g1 == g2:
            st.error("Pilih dua grup yang berbeda.")
        else:
            data_g1 = pd.to_numeric(df[df[kol_kat] == g1][kol_skor], errors='coerce').dropna()
            data_g2 = pd.to_numeric(df[df[kol_kat] == g2][kol_skor], errors='coerce').dropna()

            # Cek normalitas otomatis
            _, _, p_n1 = ks.uji_normalitas_shapiro(data_g1)
            _, _, p_n2 = ks.uji_normalitas_shapiro(data_g2)

            st.markdown("**Pemeriksaan Prasyarat Otomatis**")
            pra_df = pd.DataFrame({
                "Grup"      : [g1, g2],
                "N"         : [len(data_g1), len(data_g2)],
                "P Shapiro" : [f"{p_n1:.3f}", f"{p_n2:.3f}"],
                "Normalitas": [badge_normal(p_n1), badge_normal(p_n2)]
            })
            st.dataframe(pra_df, hide_index=True, use_container_width=True)

            st.divider()
            st.markdown("**Hasil Uji Perbedaan**")

            if p_n1 > 0.05 and p_n2 > 0.05:
                # Parametrik
                n1, n2, t, p_val, metode, p_h = ks.uji_t_smart(data_g1, data_g2)
                hasil = pd.DataFrame({
                    "": ["Metode", "P-value Levene", "T-hitung", "P-value", "Kesimpulan"],
                    "Hasil": [metode, f"{p_h:.3f}", f"{t:.4f}", f"{p_val:.4f}", badge_sig(p_val)]
                })
            else:
                # Non-parametrik
                n1, n2, u, p_val = ks.uji_mann_whitney(data_g1, data_g2)
                hasil = pd.DataFrame({
                    "": ["Metode", "U-hitung", "P-value", "Kesimpulan"],
                    "Hasil": ["Mann-Whitney U (Non-Parametrik)", f"{u:.4f}",
                              f"{p_val:.4f}", badge_sig(p_val)]
                })

            st.dataframe(hasil, hide_index=True, use_container_width=True)

            if p_val < 0.05:
                st.success(f"Ada perbedaan signifikan antara {g1} dan {g2}.")
            else:
                st.info(f"Tidak ada perbedaan signifikan antara {g1} dan {g2}.")


# =============================================================================
# MENU C — CFA
# =============================================================================

elif menu == "C. CFA (Validitas Konstruk)":
    st.subheader("🔬 Confirmatory Factor Analysis (CFA)")

    nama_faktor = st.text_input("Nama Faktor", placeholder="contoh: Kecemasan")
    item_terpilih = st.multiselect("Pilih Item (kolom)", kolom_semua)

    if st.button("Jalankan CFA"):
        if not nama_faktor:
            st.error("Nama faktor tidak boleh kosong.")
        elif len(item_terpilih) < 2:
            st.error("Pilih minimal 2 item.")
        else:
            syntax = f"{nama_faktor} =~ {' + '.join(item_terpilih)}"
            st.code(f"Model: {syntax}", language="text")

            with st.spinner("Menjalankan CFA..."):
                est, fit = ks.jalankan_cfa(df, syntax)

            if fit is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Loading Factors**")
                    st.dataframe(
                        est[['lval', 'op', 'rval', 'Estimate', 'p-value']],
                        hide_index=True, use_container_width=True
                    )
                with col2:
                    st.markdown("**Goodness of Fit**")
                    rmsea = fit['RMSEA'].values[0]
                    cfi   = fit['CFI'].values[0]
                    tli   = fit['TLI'].values[0]
                    fit_df = pd.DataFrame({
                        "Indeks"  : ["RMSEA", "CFI", "TLI"],
                        "Nilai"   : [f"{rmsea:.3f}", f"{cfi:.3f}", f"{tli:.3f}"],
                        "Standar" : ["< 0.08", "> 0.90", "> 0.90"],
                        "Status"  : [
                            "✅ Fit" if rmsea < 0.08 else "❌ Tidak Fit",
                            "✅ Fit" if cfi   > 0.90 else "❌ Tidak Fit",
                            "✅ Fit" if tli   > 0.90 else "❌ Tidak Fit",
                        ]
                    })
                    st.dataframe(fit_df, hide_index=True, use_container_width=True)
            else:
                st.error(f"CFA gagal: {est}")


# =============================================================================
# MENU D — UJI KORELASI
# =============================================================================

elif menu == "D. Uji Korelasi":
    st.subheader("🔗 Uji Hubungan (Smart Correlation)")

    col1, col2 = st.columns(2)
    var1 = col1.selectbox("Variabel X", kolom_numerik, key="kor_x")
    var2 = col2.selectbox("Variabel Y", kolom_numerik, key="kor_y")

    if st.button("Jalankan Korelasi"):
        if var1 == var2:
            st.error("Pilih dua variabel yang berbeda.")
        else:
            d1 = pd.to_numeric(df[var1], errors='coerce').dropna()
            d2 = pd.to_numeric(df[var2], errors='coerce').dropna()

            _, _, p_n1 = ks.uji_normalitas_shapiro(d1)
            _, _, p_n2 = ks.uji_normalitas_shapiro(d2)
            p_lin      = ks.uji_linearitas(d1, d2)

            # Tampilkan prasyarat
            st.markdown("**Pemeriksaan Prasyarat Otomatis**")
            lin_status = "Linear ✅" if (p_lin is not None and p_lin < 0.05) else \
                         ("Tidak Linear ❌" if p_lin is not None else "Gagal dihitung ⚠️")
            pra = pd.DataFrame({
                "Prasyarat"  : [f"Normalitas {var1}", f"Normalitas {var2}", "Linearitas"],
                "P-value"    : [f"{p_n1:.3f}", f"{p_n2:.3f}",
                                f"{p_lin:.3f}" if p_lin is not None else "N/A"],
                "Status"     : [badge_normal(p_n1), badge_normal(p_n2), lin_status]
            })
            st.dataframe(pra, hide_index=True, use_container_width=True)

            # Pilih metode otomatis
            if p_n1 > 0.05 and p_n2 > 0.05 and p_lin is not None and p_lin < 0.05:
                metode = 'pearson'
                alasan = "Semua asumsi parametrik terpenuhi."
            else:
                metode = 'spearman'
                alasan = "Asumsi normalitas atau linearitas tidak terpenuhi."

            n, r, p = ks.hitung_korelasi(d1, d2, metode=metode)

            st.divider()
            st.markdown(f"**Hasil Korelasi {metode.capitalize()}**")
            st.caption(f"Alasan pemilihan metode: {alasan}")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("N", n)
            col2.metric("r", f"{r:.4f}")
            col3.metric("P-value", f"{p:.4f}")
            col4.metric("Kekuatan", kekuatan_korelasi(r))

            if p < 0.05:
                st.success(f"Korelasi SIGNIFIKAN — Ada hubungan {kekuatan_korelasi(r).lower()} antara {var1} dan {var2}.")
            else:
                st.info("Korelasi TIDAK SIGNIFIKAN.")


# =============================================================================
# MENU E — RELIABILITAS
# =============================================================================

elif menu == "E. Uji Reliabilitas":
    st.subheader("🎯 Uji Reliabilitas (Cronbach's Alpha)")

    item_terpilih = st.multiselect("Pilih item-item skala", kolom_semua)

    if st.button("Hitung Alpha"):
        if len(item_terpilih) < 2:
            st.error("Pilih minimal 2 item.")
        else:
            alpha, n_valid = ks.hitung_reliabilitas(df, item_terpilih)

            if alpha is not None:
                col1, col2, col3 = st.columns(3)
                col1.metric("Jumlah Item (k)", len(item_terpilih))
                col2.metric("Jumlah Sampel (N)", n_valid)
                col3.metric("Cronbach's Alpha", f"{alpha:.3f}")

                if alpha >= 0.7:
                    st.success("✅ RELIABEL — Alpha ≥ 0.70, skala layak digunakan.")
                elif alpha >= 0.6:
                    st.warning("⚠️ CUKUP RELIABEL — Alpha 0.60–0.69, pertimbangkan revisi item.")
                else:
                    st.error("❌ TIDAK RELIABEL — Alpha < 0.60, item perlu diperbaiki.")
            else:
                st.error(f"Gagal menghitung Alpha: {n_valid}")


# =============================================================================
# MENU F — DIAGNOSTIK ASUMSI
# =============================================================================

elif menu == "F. Diagnostik Asumsi":
    st.subheader("🔧 Diagnostik & Solusi Asumsi")

    tab_norm, tab_homo, tab_lin, tab_vif = st.tabs([
        "1️⃣ Normalitas",
        "2️⃣ Homogenitas",
        "3️⃣ Linearitas",
        "4️⃣ Multikolinearitas (VIF)"
    ])

    # ── Tab Normalitas ─────────────────────────────────────────────────────────
    with tab_norm:
        kolom_n = st.selectbox("Pilih kolom", kolom_semua, key="norm_col")
        if st.button("Cek Normalitas"):
            data_n = pd.to_numeric(df[kolom_n], errors='coerce').dropna()
            n, stat_w, p = ks.uji_normalitas_shapiro(data_n)

            col1, col2, col3 = st.columns(3)
            col1.metric("N Valid", n)
            col2.metric("Shapiro-Wilk W", f"{stat_w:.3f}")
            col3.metric("P-value", f"{p:.3f}" if p >= 0.001 else "< .001")

            if p > 0.05:
                st.success("✅ DATA NORMAL — Lanjutkan dengan statistik Parametrik (Uji-T, Pearson).")
            else:
                st.error("❌ DATA TIDAK NORMAL")
                st.markdown("""
                **Saran:**
                1. Gunakan statistik Non-Parametrik (Spearman / Mann-Whitney)
                2. Periksa kemungkinan adanya Outlier
                3. Pertimbangkan transformasi data (log, sqrt)
                """)

    # ── Tab Homogenitas ────────────────────────────────────────────────────────
    with tab_homo:
        kol_kat_h  = st.selectbox("Kolom Kategori", kolom_semua, key="homo_kat")
        kol_skor_h = st.selectbox("Kolom Skor", kolom_numerik, key="homo_skor")

        semua_grup_h = df[kol_kat_h].dropna().unique().tolist()
        if len(semua_grup_h) >= 2:
            col1, col2 = st.columns(2)
            gh1 = col1.selectbox("Grup 1", semua_grup_h, index=0, key="gh1")
            gh2 = col2.selectbox("Grup 2", semua_grup_h, index=1, key="gh2")

            if st.button("Cek Homogenitas"):
                dh1 = pd.to_numeric(df[df[kol_kat_h] == gh1][kol_skor_h], errors='coerce').dropna()
                dh2 = pd.to_numeric(df[df[kol_kat_h] == gh2][kol_skor_h], errors='coerce').dropna()
                stat_l, p_l = ks.uji_homogenitas_levene(dh1, dh2)

                col1, col2 = st.columns(2)
                col1.metric("Levene Statistic", f"{stat_l:.3f}")
                col2.metric("P-value", f"{p_l:.4f}")

                if p_l > 0.05:
                    st.success("✅ VARIANS HOMOGEN — Lanjutkan dengan Independent Student's T-Test.")
                else:
                    st.error("❌ DATA TIDAK HOMOGEN — Gunakan Welch's T-Test atau Mann-Whitney.")
        else:
            st.warning("Kolom kategori harus memiliki minimal 2 grup.")

    # ── Tab Linearitas ─────────────────────────────────────────────────────────
    with tab_lin:
        col1, col2 = st.columns(2)
        var_x_l = col1.selectbox("Variabel X", kolom_numerik, key="lin_x")
        var_y_l = col2.selectbox("Variabel Y", kolom_numerik, key="lin_y")

        if st.button("Cek Linearitas"):
            df_lin = df[[var_x_l, var_y_l]].copy()
            df_lin[var_x_l] = pd.to_numeric(df_lin[var_x_l], errors='coerce')
            df_lin[var_y_l] = pd.to_numeric(df_lin[var_y_l], errors='coerce')
            df_lin = df_lin.dropna()

            if len(df_lin) < 3:
                st.error("Data tidak cukup untuk uji linearitas (minimal 3 baris valid).")
            else:
                p_l = ks.uji_linearitas(df_lin[var_x_l], df_lin[var_y_l])
                if p_l is None:
                    st.error("Uji linearitas gagal dijalankan.")
                else:
                    st.metric("P-value Linearitas", f"{p_l:.4f}")
                    if p_l < 0.05:
                        st.success("✅ LINEAR — Asumsi linearitas terpenuhi untuk Pearson / Regresi.")
                    else:
                        st.error("❌ TIDAK LINEAR — Gunakan Spearman Rank atau transformasi data.")

    # ── Tab VIF ────────────────────────────────────────────────────────────────
    with tab_vif:
        var_vif = st.multiselect("Pilih variabel (min. 2)", kolom_numerik, key="vif_vars")

        if st.button("Hitung VIF"):
            if len(var_vif) < 2:
                st.error("Pilih minimal 2 variabel.")
            else:
                try:
                    vif_res = ks.uji_multikolinearitas(df, var_vif)
                    st.dataframe(vif_res, hide_index=True, use_container_width=True)
                    st.caption("Catatan: VIF > 10 = Bermasalah | VIF 5–10 = Perlu Perhatian | VIF < 5 = Aman")
                except Exception as e:
                    st.error(f"Error: {e}")
