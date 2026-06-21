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
    # 'INFP': 'ISI_ID_PLAYLIST_INFP',
    # 'ENFJ': 'ISI_ID_PLAYLIST_ENFJ',
    # 'ENFP': 'ISI_ID_PLAYLIST_ENFP',
    # 'INTJ': 'ISI_ID_PLAYLIST_INTJ',
    'INTP': '54YCS9D2dr1AisRScAx8gl',
    'ENTJ': '2sMGWHpGRVt6z8BsMfGbHd',
    'ENTP': '0alz3ht2DfCz8GsDEFYSvg',
    # 'ISTJ': 'ISI_ID_PLAYLIST_ISTJ',
    # 'ISFJ': 'ISI_ID_PLAYLIST_ISFJ',
    # 'ESTJ': 'ISI_ID_PLAYLIST_ESTJ',
    # 'ESFJ': 'ISI_ID_PLAYLIST_ESFJ',
    # 'ISTP': 'ISI_ID_PLAYLIST_ISTP',
    # 'ISFP': 'ISI_ID_PLAYLIST_ISFP',
    # 'ESTP': 'ISI_ID_PLAYLIST_ESTP',
    # 'ESFP': 'ISI_ID_PLAYLIST_ESFP',
}

all_songs = []

# 4. Loop Otomatisasi untuk 16 Playlist
for mbti_type, playlist_id in target_playlists.items():
    if playlist_id.startswith('ISI_ID_'):
        print(f"Skipping {mbti_type} karena ID playlist belum diisi.")
        continue
        
    url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"\nMemuat halaman Spotify untuk tipe: {mbti_type}...")
    driver.get(url)
    
    # Beri waktu 7 detik agar JavaScript merender daftar lagu
    time.sleep(7)
    
    try:
        # Ekstrak elemen teks lagu yang mengarah ke link /track/
        track_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/track/')]")
        titles = [el.text for el in track_elements if el.text != ""]
        
        # Bersihkan data ganda jika Selenium menangkap elemen double
        unique_titles = list(dict.fromkeys(titles))
        
        # Ambil maksimal 13 lagu agar data seimbang (balance)
        sliced_titles = unique_titles[:13]
        print(f"-> Berhasil mendapatkan {len(sliced_titles)} lagu untuk {mbti_type}")
        
        for title in sliced_titles:
            # Otomatis mapping biner berdasarkan kamus mbti_mapping
            song_data = {
                'Track Name': title,
                'MBTI': mbti_type,
                'E_I': mbti_mapping[mbti_type]['E_I'],
                'N_S': mbti_mapping[mbti_type]['N_S'],
                'T_F': mbti_mapping[mbti_type]['T_F'],
                'J_P': mbti_mapping[mbti_type]['J_P']
            }
            all_songs.append(song_data)
            
    except Exception as e:
        print(f"Gagal mengekstrak playlist {mbti_type}: {e}")

# 5. Tutup Browser dan Simpan ke CSV tunggal
driver.quit()

if all_songs:
    df = pd.DataFrame(all_songs)
    df.to_csv('dataset_mbti_musik.csv', index=False)
    print(f"\n[SUKSES] File 'dataset_mbti_musik.csv' berhasil dibuat dengan total {len(df)} lagu!")
else:
    print("\n[GAGAL] Tidak ada data lagu yang berhasil dikumpulkan.")