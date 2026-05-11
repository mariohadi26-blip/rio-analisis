# =============================================================================
# KALKULATOR STAT (v4.0 - Robust)
# Disesuaikan untuk bekerja bersama main.py v4.0
#
# Daftar Perbaikan:
# [FIX-K01] Tambah fungsi uji_t_smart() → dipanggil main.py menu B tapi belum ada
# [FIX-K02] Tambah fungsi uji_mann_whitney() → dipanggil main.py menu B tapi belum ada
# [FIX-K03] uji_t_independent() lama → dipertahankan untuk kompatibilitas mundur
# [FIX-K04] baca_file_eksternal() → tambah guard jika ekstensi tidak dikenal
# [FIX-K05] uji_multikolinearitas() → tambah guard jika VIF tidak bisa dihitung
#           (misal hanya 1 variabel yang dimasukkan)
# =============================================================================

import pandas as pd
import numpy as np
from scipy import stats
from semopy import Model, calc_stats
import pingouin as pg
from statsmodels.stats.outliers_influence import variance_inflation_factor


# =============================================================================
# FUNGSI PEMBERSIH — Dipakai oleh semua fungsi di bawah
# =============================================================================

def bersihkan_ke_angka(data):
    """Memastikan data hanya berisi angka, membuang teks dan data kosong."""
    return pd.to_numeric(data, errors='coerce').dropna()


# =============================================================================
# FUNGSI FILE
# =============================================================================

def baca_file_eksternal(nama_file):
    """
    Membaca file Excel atau CSV.
    [FIX-K04] Tambah ValueError jika ekstensi tidak dikenal agar error
    tertangkap dengan pesan yang jelas di main.py.
    """
    if nama_file.endswith('.csv'):
        return pd.read_csv(nama_file)
    elif nama_file.endswith(('.xlsx', '.xls')):
        return pd.read_excel(nama_file, engine='openpyxl')
    else:
        raise ValueError(
            f"Format file '{nama_file}' tidak didukung. "
            "Gunakan file .csv atau .xlsx"
        )


# =============================================================================
# FUNGSI DESKRIPTIF
# =============================================================================

def hitung_deskriptif_lengkap(data):
    """
    Menghitung statistik deskriptif lengkap.
    Menggunakan ddof=1 (standar sampel) agar konsisten dengan JASP.
    """
    data_bersih = bersihkan_ke_angka(data)
    n_valid   = len(data_bersih)
    n_missing = len(data) - n_valid

    if n_valid == 0:
        return n_valid, n_missing, 0, 0, 0, 0, 0, 0, 0

    mean    = np.mean(data_bersih)
    median  = np.median(data_bersih)
    mode    = data_bersih.mode()[0] if not data_bersih.mode().empty else 0
    std     = np.std(data_bersih, ddof=1)   # Standar sampel
    minimum = np.min(data_bersih)
    maximum = np.max(data_bersih)
    rentang = maximum - minimum

    return n_valid, n_missing, mode, median, mean, std, rentang, minimum, maximum


# =============================================================================
# FUNGSI NORMALITAS
# =============================================================================

def uji_normalitas_shapiro(data):
    """
    Menguji normalitas data dengan Shapiro-Wilk.
    Mengembalikan (n, statistik_W, p_value).
    """
    data_bersih = bersihkan_ke_angka(data)
    n = len(data_bersih)
    if n < 3:
        return n, 0.0, 0.0
    stat, p_val = stats.shapiro(data_bersih)
    return n, stat, p_val


# =============================================================================
# FUNGSI UJI PERBEDAAN
# =============================================================================

def uji_t_independent(data1, data2):
    """
    [FIX-K03] Dipertahankan untuk kompatibilitas mundur.
    Untuk penggunaan baru, gunakan uji_t_smart().
    Menjalankan Independent Samples T-Test (Student's).
    Mengembalikan (n1, n2, t_stat, p_val).
    """
    d1 = bersihkan_ke_angka(data1)
    d2 = bersihkan_ke_angka(data2)
    t_stat, p_val = stats.ttest_ind(d1, d2, equal_var=True)
    return len(d1), len(d2), t_stat, p_val


def uji_t_smart(data1, data2):
    """
    [FIX-K01] FUNGSI BARU — Dipanggil oleh main.py Menu B jalur parametrik.

    Secara otomatis memilih antara:
    - Student's T-Test  → jika varians homogen (Levene p > 0.05)
    - Welch's T-Test    → jika varians tidak homogen (Levene p <= 0.05)

    Mengembalikan: (n1, n2, t_stat, p_val, nama_metode, p_levene)
    """
    d1 = bersihkan_ke_angka(data1)
    d2 = bersihkan_ke_angka(data2)

    # Cek homogenitas dulu
    levene_stat, p_levene = stats.levene(d1, d2)

    if p_levene > 0.05:
        # Varians homogen → Student's T-Test (equal_var=True)
        t_stat, p_val = stats.ttest_ind(d1, d2, equal_var=True)
        nama_metode = "Independent Student's T-Test (Parametrik, Varians Homogen)"
    else:
        # Varians tidak homogen → Welch's T-Test (equal_var=False)
        t_stat, p_val = stats.ttest_ind(d1, d2, equal_var=False)
        nama_metode = "Welch's T-Test (Parametrik, Varians Tidak Homogen)"

    return len(d1), len(d2), t_stat, p_val, nama_metode, p_levene


def uji_mann_whitney(data1, data2):
    """
    [FIX-K02] FUNGSI BARU — Dipanggil oleh main.py Menu B jalur non-parametrik.

    Alternatif non-parametrik untuk Uji-T ketika asumsi normalitas tidak terpenuhi.
    Mengembalikan: (n1, n2, u_stat, p_val)
    """
    d1 = bersihkan_ke_angka(data1)
    d2 = bersihkan_ke_angka(data2)
    u_stat, p_val = stats.mannwhitneyu(d1, d2, alternative='two-sided')
    return len(d1), len(d2), u_stat, p_val


# =============================================================================
# FUNGSI KORELASI
# =============================================================================

def hitung_korelasi(data1, data2, metode='pearson'):
    """
    Menghitung korelasi Pearson atau Spearman.
    Data dibersihkan secara berpasangan agar baris tetap sinkron.
    Mengembalikan: (n, r, p_val)
    """
    df_temp = pd.DataFrame({'v1': data1, 'v2': data2})
    df_temp = df_temp.apply(pd.to_numeric, errors='coerce').dropna()

    if len(df_temp) < 2:
        return len(df_temp), 0.0, 0.0

    if metode == 'spearman':
        r, p = stats.spearmanr(df_temp['v1'], df_temp['v2'])
    else:
        r, p = stats.pearsonr(df_temp['v1'], df_temp['v2'])

    return len(df_temp), r, p


# =============================================================================
# FUNGSI CFA
# =============================================================================

def jalankan_cfa(df, syntax_model):
    """
    Menjalankan Confirmatory Factor Analysis (CFA) menggunakan semopy.
    Mengembalikan: (tabel_estimasi, tabel_fit) atau (pesan_error, None)
    """
    # Bersihkan semua kolom yang relevan ke numerik
    data_cfa = df.apply(pd.to_numeric, errors='coerce').dropna()
    try:
        mod = Model(syntax_model)
        mod.fit(data_cfa)
        return mod.inspect(), calc_stats(mod)
    except Exception as e:
        return f"Error CFA: {e}", None


# =============================================================================
# FUNGSI RELIABILITAS
# =============================================================================

def hitung_reliabilitas(df, list_item):
    """
    Menghitung Cronbach's Alpha untuk sekumpulan item.
    Mengembalikan: (alpha, n_sampel) atau (None, pesan_error)
    """
    try:
        data_rel = df[list_item].apply(pd.to_numeric, errors='coerce').dropna()

        if data_rel.empty:
            return None, "Data kosong setelah dibersihkan."

        if len(list_item) < 2:
            return None, "Cronbach's Alpha membutuhkan minimal 2 item."

        alpha_res = pg.cronbach_alpha(data=data_rel)
        # alpha_res mengembalikan tuple (alpha, confidence_interval)
        return alpha_res[0], len(data_rel)

    except Exception as e:
        return None, str(e)


# =============================================================================
# FUNGSI UJI ASUMSI
# =============================================================================

def uji_homogenitas_levene(*args):
    """
    Menguji apakah varians antar kelompok sama (Levene's Test).
    Input: data dari kelompok-kelompok yang dibandingkan (bisa lebih dari 2).
    Mengembalikan: (stat, p_val)
    """
    clean_groups = [bersihkan_ke_angka(g) for g in args]
    stat, p_val = stats.levene(*clean_groups)
    return stat, p_val


def uji_linearitas(data_x, data_y):
    """
    Mengecek linearitas melalui p-value regresi linear sederhana.
    Jika p < .05 → ada hubungan linear yang signifikan.
    Mengembalikan: p_val (float) atau None jika data tidak cukup/error.
    """
    df_temp = pd.DataFrame({'x': data_x, 'y': data_y})
    df_temp = df_temp.apply(pd.to_numeric, errors='coerce').dropna()

    if len(df_temp) < 3:
        return None

    try:
        slope, intercept, r_val, p_val, std_err = stats.linregress(
            df_temp['x'], df_temp['y']
        )
        return p_val
    except Exception:
        return None


def uji_multikolinearitas(df, list_variabel):
    """
    Menghitung VIF (Variance Inflation Factor) untuk mengecek multikolinearitas.
    VIF > 10 mengindikasikan multikolinearitas yang bermasalah.

    [FIX-K05] Tambah guard:
    - Minimal 2 variabel (VIF tidak bermakna untuk 1 variabel)
    - Data tidak boleh kosong setelah dibersihkan
    Mengembalikan: DataFrame VIF atau None jika gagal.
    """
    if len(list_variabel) < 2:
        raise ValueError("VIF membutuhkan minimal 2 variabel.")

    db = df[list_variabel].apply(pd.to_numeric, errors='coerce').dropna()

    if db.empty:
        raise ValueError("Data kosong setelah dibersihkan. Periksa kolom yang dipilih.")

    vif_data = pd.DataFrame()
    vif_data["Variabel"] = db.columns
    vif_data["VIF"]      = [
        variance_inflation_factor(db.values, i)
        for i in range(len(db.columns))
    ]

    # Tambah kolom interpretasi otomatis
    vif_data["Status"] = vif_data["VIF"].apply(
        lambda v: "Bermasalah ✗" if v > 10 else ("Perlu Perhatian" if v > 5 else "Aman ✓")
    )

    return vif_data