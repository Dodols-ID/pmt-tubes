import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd

# 1. Setup API Credentials Spotify (Nanti didapat dari dashboard Spotify Developer)
client_id = '019543ecbf9d4462beebed76d884b66d'
client_secret = '4602143ed72d4e27857f50dd1d74608f'
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

# 2. Kamus Pemetaan MBTI ke Biner (Ground Truth)
mbti_mapping = {
    'INFJ': {'E_I': 0, 'N_S': 1, 'T_F': 1, 'J_P': 1},
    'INFP': {'E_I': 0, 'N_S': 1, 'T_F': 1, 'J_P': 0},
    'ENTP': {'E_I': 1, 'N_S': 1, 'T_F': 0, 'J_P': 0},
    'ESTP': {'E_I': 1, 'N_S': 0, 'T_F': 0, 'J_P': 0},
    # ... tinggal dilengkapi sampai 16 kepribadian
}

# 3. Daftar Target Playlist yang Mau Di-scrap (Contoh isi ID Playlist Spotify)
# Kamu tinggal cari playlist MBTI di Spotify, lalu copy ID di URL-nya
target_playlists = {
    'INFJ': '6eKkAqd6nrZfoTC8QZUt7w',
    # 'ENTP': 'ID_PLAYLIST_ENTP_DI_SPOTIFY',
    # 'ESTP': 'ID_PLAYLIST_ESTP_DI_SPOTIFY',
    # masukkan semua list sesuai target kuota kita
}

all_songs = []

# 4. Proses Loop Otomatisasi Scraping & Labeling
for mbti_type, playlist_id in target_playlists.items():
    # Ambil data track dari Spotify API (Batasi 13 lagu per playlist agar balance)
    results = sp.playlist_tracks(playlist_id, limit=13)
    tracks = results['items']
    
    for item in tracks:
        track = item['track']
        if track is not None:
            song_data = {
                'Track Name': track['name'],
                'Artist': track['artists'][0]['name'],
                'MBTI': mbti_type,
                'E_I': mbti_mapping[mbti_type]['E_I'],
                'N_S': mbti_mapping[mbti_type]['N_S'],
                'T_F': mbti_mapping[mbti_type]['T_F'],
                'J_P': mbti_mapping[mbti_type]['J_P']
            }
            all_songs.append(song_data)

# 5. Konversi ke DataFrame dan simpan ke CSV
df = pd.DataFrame(all_songs)
df.to_csv('dataset_mbti_musik.csv', index=False)
print(f"Selesai! Berhasil mengumpulkan {len(df)} lagu secara otomatis.")