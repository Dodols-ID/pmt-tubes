from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

# 1. Setup Browser Chrome Otomatis (Headless)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Berjalan di latar belakang tanpa pop-up browser
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 2. Kamus Pemetaan MBTI ke Biner Lengkap (16 Tipe)
mbti_mapping = {
    # The Analysts (NT)
    'INTJ': {'E_I': 0, 'N_S': 1, 'T_F': 0, 'J_P': 1},
    'INTP': {'E_I': 0, 'N_S': 1, 'T_F': 0, 'J_P': 0},
    'ENTJ': {'E_I': 1, 'N_S': 1, 'T_F': 0, 'J_P': 1},
    'ENTP': {'E_I': 1, 'N_S': 1, 'T_F': 0, 'J_P': 0},
    
    # The Diplomats (NF)
    'INFJ': {'E_I': 0, 'N_S': 1, 'T_F': 1, 'J_P': 1},
    'INFP': {'E_I': 0, 'N_S': 1, 'T_F': 1, 'J_P': 0},
    'ENFJ': {'E_I': 1, 'N_S': 1, 'T_F': 1, 'J_P': 1},
    'ENFP': {'E_I': 1, 'N_S': 1, 'T_F': 1, 'J_P': 0},
    
    # The Sentinels (SJ)
    'ISTJ': {'E_I': 0, 'N_S': 0, 'T_F': 0, 'J_P': 1},
    'ISFJ': {'E_I': 0, 'N_S': 0, 'T_F': 1, 'J_P': 1},
    'ESTJ': {'E_I': 1, 'N_S': 0, 'T_F': 0, 'J_P': 1},
    'ESFJ': {'E_I': 1, 'N_S': 0, 'T_F': 1, 'J_P': 1},
    
    # The Explorers (SP)
    'ISTP': {'E_I': 0, 'N_S': 0, 'T_F': 0, 'J_P': 0},
    'ISFP': {'E_I': 0, 'N_S': 0, 'T_F': 1, 'J_P': 0},
    'ESTP': {'E_I': 1, 'N_S': 0, 'T_F': 0, 'J_P': 0},
    'ESFP': {'E_I': 1, 'N_S': 0, 'T_F': 1, 'J_P': 0},
}

# 3. Daftar Target Playlist (Silakan isi ID playlist yang sudah dibersihkan buntutnya)
target_playlists = {
    'INFJ': '6eKkAqd6nrZfoTC8QZUt7w',
    'INFP': '7jcLRVhhQtpZpMVBnffYU3',
    'ENFJ': '1eVgLeDoHD123LB6VldjGY',
    'ENFP': '4qvyBmM6lQ6uwIyDfZ4Oq3',
    'INTJ': '650poOgnPqhCG2uu3lJta2',
    'INTP': '54YCS9D2dr1AisRScAx8gl',
    'ENTJ': '2sMGWHpGRVt6z8BsMfGbHd',
    'ENTP': '0alz3ht2DfCz8GsDEFYSvg',
    'ISTJ': '1aGR6X8kdHWWy5M2nNFoWy',
    'ISFJ': '0lYllEZHsSAuVE0bBsYTvA',
    'ESTJ': '1s59H8zfMEUPQx0Wvk5TI9',
    'ESFJ': '6PsawaiOyvzoNX6h6B8DUE',
    'ISTP': '2jIk3SeeRy45h3XJY8yOSE',
    'ISFP': '6FdFbQ8QI8KO8mCwgekYY7',
    'ESTP': '65r8dT97EcHxBl2pW0jhzx',
    'ESFP': '1irl5I1VRnwSJeiDQGVxRq',
}

all_songs = []

from selenium.webdriver.common.keys import Keys # <--- PASTIKAN UNTUK IMPORT INI DI ATAS

# 4. Loop Otomatisasi dengan Dinamis Real-Time Extraction (Menyapu Semua Lagu)
for mbti_type, playlist_id in target_playlists.items():
    if playlist_id.startswith('ISI_ID_'):
        print(f"Skipping {mbti_type} karena ID playlist belum diisi.")
        continue
        
    url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"\nMemuat halaman Spotify untuk tipe: {mbti_type}...")
    driver.get(url)
    time.sleep(7) # Beri waktu ekstra render awal halaman
    
    unique_titles = []
    scroll_attempts = 0
    max_attempts = 15 # Batas toleransi stagnansi gulir sebelum dianggap "habis"
    
    print(f"Memulai pemindaian total untuk seluruh isi playlist {mbti_type}...")
    
    while scroll_attempts < max_attempts:
        # HARD GUARDRAIL: Kunci target hanya pada baris ber-atribut aria-rowindex (Playlist Resmi)
        track_elements = driver.find_elements(By.XPATH, "//*[@aria-rowindex]//a[contains(@href, '/track/')]")
        
        new_songs_found = 0
        for el in track_elements:
            try:
                title_text = el.text
                if title_text != "" and title_text not in unique_titles:
                    unique_titles.append(title_text)
                    new_songs_found += 1
            except Exception:
                continue
        
        print(f"-> Terkumpul: {len(unique_titles)} lagu...")
        
        # Simulasi gulir halus menggunakan ARROW_DOWN agar DOM merender baris demi baris
        if track_elements:
            try:
                last_visible_element = track_elements[-1]
                for _ in range(8): # Dinaikkan ke 8 kali panah bawah agar pergeseran konstan
                    last_visible_element.send_keys(Keys.ARROW_DOWN)
                time.sleep(1.5)
            except Exception:
                try:
                    for _ in range(8):
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_DOWN)
                    time.sleep(1.5)
                except Exception:
                    pass
        
        # LOGIKA DINAMIS: Jika tidak ada lagu baru yang terdeteksi, naikkan angka counter stagnansi
        if new_songs_found == 0:
            scroll_attempts += 1
        else:
            scroll_attempts = 0 # Reset ke 0 jika angka total lagu masih sukses mendobrak maju

    print(f"[SUKSES] Seluruh playlist selesai disapu! Total final didapat: {len(unique_titles)} lagu resmi untuk {mbti_type}")
    
    # Loop pengemasan data seluruh lagu tanpa dipotong slice (Murni dinamis)
    for title in unique_titles:
        song_data = {
            'Track Name': title,
            'MBTI': mbti_type,
            'E_I': mbti_mapping[mbti_type]['E_I'],
            'N_S': mbti_mapping[mbti_type]['N_S'],
            'T_F': mbti_mapping[mbti_type]['T_F'],
            'J_P': mbti_mapping[mbti_type]['J_P']
        }
        all_songs.append(song_data)
        
# 5. Tutup Browser dan Simpan ke CSV tunggal
driver.quit()

if all_songs:
    df = pd.DataFrame(all_songs)
    df.to_csv('dataset_mbti_musik.csv', index=False)
    print(f"\n[SUKSES] File 'dataset_mbti_musik.csv' berhasil dibuat dengan total {len(df)} lagu!")
else:
    print("\n[GAGAL] Tidak ada data lagu yang berhasil dikumpulkan.")