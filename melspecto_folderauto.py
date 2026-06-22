import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
from multiprocessing import Pool, cpu_count

def load_audio_to_numpy(file_path, target_sr=22050):
    """Loads an MP3 or OGG file using pydub, downsamples, and converts to mono float32."""
    # Ambil ekstensi file (misal: '.mp3' atau '.ogg')
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Deteksi format dan load secara spesifik
    if file_ext == '.mp3':
        audio = AudioSegment.from_mp3(file_path)
    elif file_ext == '.ogg':
        audio = AudioSegment.from_ogg(file_path)
    else:
        raise ValueError(f"Format file {file_ext} tidak didukung oleh fungsi ini.")
    
    # 2. Optimasi: Downsample & Ubah ke Mono langsung saat loading
    audio = audio.set_frame_rate(target_sr).set_channels(1)
    
    # 3. Konversi ke numpy array dan normalisasi ke float32 [-1.0, 1.0]
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    max_val = 2 ** (8 * audio.sample_width - 1)
    samples /= max_val
    
    return np.ascontiguousarray(samples), target_sr

def audio_to_frames(signal, frame_size, hop_size, window_fn):
    signal_len = len(signal)
    num_frames = int(np.floor((signal_len - frame_size) / hop_size) + 1)
    
    shape = (num_frames, frame_size)
    strides = (signal.strides[0] * hop_size, signal.strides[0])
    frames = np.lib.stride_tricks.as_strided(signal, shape=shape, strides=strides)
    
    window = window_fn(frame_size)
    return frames * window

def hz_to_mel(hz):
    return 2595 * np.log10(1 + hz / 700.0)

def mel_to_hz(mel):
    return 700 * (10**(mel / 2595.0) - 1)

def create_mel_filterbank(sr, n_fft, n_mels, fmin=0, fmax=None):
    if fmax is None:
        fmax = sr / 2
    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    
    mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_pts = mel_to_hz(mel_pts)
    
    bins = np.floor((n_fft + 1) * hz_pts / sr).astype(int)
    
    filters = np.zeros((n_mels, int(n_fft // 2 + 1)))
    for m in range(1, n_mels + 1):
        for k in range(bins[m - 1], bins[m]):
            filters[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
        for k in range(bins[m], bins[m + 1]):
            filters[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])
            
    return filters

def process_single_audio(args):
    """Worker function untuk memproses satu audio (Bagian dari Multiprocessing)"""
    file_path, output_dir, n_mels, frame_size, hop_size = args
    try:
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        output_path = os.path.join(output_dir, f"{base_name}.png")
        
        # 1. Load MP3 (Menggantikan load_audio lamamu)
        signal, sr = load_audio_to_numpy(file_path, target_sr=22050)
        
        # 2. Framing & Windowing
        hann_window = lambda N: 0.5 * (1 - np.cos(2 * np.pi * np.arange(N) / (N - 1)))
        frames = audio_to_frames(signal, frame_size, hop_size, hann_window)
        
        # 3. FFT & Power Spectrum
        stft_matrix = np.fft.rfft(frames, n=frame_size, axis=-1)
        power_spectrum = (np.abs(stft_matrix) ** 2) / frame_size
        
        # 4. Mel Filterbank
        mel_filters = create_mel_filterbank(sr, n_fft=frame_size, n_mels=n_mels)
        mel_spec = np.dot(power_spectrum, mel_filters.T).T
        
        # 5. Log Scaling (dB)
        mel_spec_db = 10 * np.log10(np.maximum(mel_spec, 1e-10))
        mel_spec_db -= np.max(mel_spec_db)
        
        # 6. Save Plot secara bersih tanpa axis
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.imshow(mel_spec_db, aspect='auto', origin='lower', cmap='viridis')
        ax.axis('off')
        
        # Simpan Gambar
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close(fig) # Bebaskan memori matplotlib biar gak kebocoran RAM
        
        return f"[SUKSES] {file_name} -> Terkonversi."
    except Exception as e:
        return f"[GAGAL] {os.path.basename(file_path)}: {str(e)}"

def batch_generate_melspectrogram(target_folder_path, n_mels=128, frame_size=2048, hop_size=512):
    # Bersihkan path dari slash penutup
    target_folder_path = os.path.normpath(target_folder_path)
    folder_name = os.path.basename(target_folder_path)
    
    # Buat nama folder output sesuai request: "[audio target folder name]-melspect"
    parent_dir = os.path.dirname(target_folder_path)
    output_dir = os.path.join(parent_dir, f"{folder_name}-melspect")
    os.makedirs(output_dir, exist_ok=True)
    
    # =========================================================================
    # 1. DEBUG & CARI FILE (Menggunakan os.listdir agar aman dengan tanda dash)
    # =========================================================================
    audio_files = []
    
    try:
        # Mengintip langsung apa yang dilihat oleh Python di dalam folder tersebut
        all_items = os.listdir(target_folder_path)
        
        print("\n================== DEBUG BROWSER PYTHON ==================")
        print(f"Target Path  : {target_folder_path}")
        print(f"Total Item   : {len(all_items)} ditemukan di dalam folder.")
        print(f"Isi File Fisik Terbaca: {all_items}")
        print("==========================================================\n")
        
        for file in all_items:
            # Mengubah semua nama file menjadi lowercase agar pengecekan ekstensi tidak sensitif
            if file.lower().endswith('.mp3') or file.lower().endswith('.ogg'):
                full_path = os.path.join(target_folder_path, file)
                audio_files.append(full_path)
                
    except Exception as e:
        print(f"[ERROR] Gagal mengakses atau membaca folder: {e}")
        return
    
    # --- TAMBAHKAN PEMBATASAN DI SINI ---
    LIMIT_FILE = 49  # Ganti angka ini sesuai jumlah maksimal lagu yang mau kamu proses
    audio_files = audio_files[:LIMIT_FILE]  # Mengambil file dari indeks 0 sampai LIMIT_FILE
    # ------------------------------------
    
    total_files = len(audio_files)
    
    # Validasi pembatas
    if total_files == 0:
        print(f"Tidak ada file MP3 atau OGG valid yang lolos filter di: {target_folder_path}")
        return
    # PERBAIKAN: Ubah teks log agar informatif sesuai data asli
    print(f"Menemukan {total_files} lagu (MP3/OGG) di folder '{folder_name}'.")
    print(f"Folder output disiapkan di: {output_dir}")
    print(f"Memulai konversi paralel menggunakan {cpu_count()} CPU Core...")

    # 2. Siapkan argumen (PASTIKAN menggunakan audio_files, bukan mp3_files lama!)
    task_args = [(f, output_dir, n_mels, frame_size, hop_size) for f in audio_files]
    
    # 3. Eksekusi Multiprocessing secara paralel (Tetap sama)
    with Pool(processes=cpu_count()) as pool:
        for result in pool.imap_unordered(process_single_audio, task_args):
            print(result)

    print(f"\n[SELESAI] Semua spectrogram untuk folder {folder_name} berhasil disimpan.")
    
# --- Eksekusi Batch Per Folder MBTI ---
if __name__ == '__main__':
    # Contoh penggunaan: Arahkan ke folder salah satu MBTI kamu yang berisi MP3
    folder_mbti_kamu = "C:/Users/loren/Desktop/pmt-tubes/pmt-tubes/ENTP-audio-folder"
    batch_generate_melspectrogram(folder_mbti_kamu)