import requests
from bs4 import BeautifulSoup
import json
import pandas as pd

url = "https://open.spotify.com/playlist/6eKkAqd6nrZfoTC8QZUt7w"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Cari tag script yang berisi data awal aplikasi Spotify
script_tag = soup.find("script", id="initial-state")

if script_tag:
    try:
        # Load teks di dalam script menjadi objek JSON / Dictionary Python
        json_data = json.loads(script_tag.string)
        
        # Menggali struktur JSON internal Spotify (Strukturnya bisa sangat dalam)
        # Catatan: Struktur ini bisa berubah sewaktu-waktu tergantung update Spotify
        print("Data JSON berhasil ditemukan! Memproses lagu...")
        
        # Di sini kita melakukan pengecekan isi JSON secara kasar dulu
        # Jika berhasil, kita bisa memetakan judul dan artisnya langsung.
        print(str(json_data)[:500]) # Print 500 karakter pertama buat ngecek isi
        
    except Exception as e:
        print(f"Gagal membaca struktur JSON: {e}")
else:
    print("Tag data awal tidak ditemukan. Spotify memblokir request biasa.")