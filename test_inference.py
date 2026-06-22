import os
import sys

# =========================================================================
# ABSOLUTE HARD GUARDRAIL: Bunuh paksa sub-proses ilegal penembus impor
# =========================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Deteksi mutakhir jika modul ini di-load oleh engine multiprocessing Windows di background
if not __name__ == '__main__':
    # Cek apakah ada parameter multiprocessing di sistem argumen Windows
    if any(arg in sys.argv for arg in ['--multiprocessing-fork', '-c']):
        # Paksa proses anak mati seketika secara damai sebelum merusak alur impor
        sys.exit(0)

# =========================================================================
# SEKARANG PROSES IMPOR DIJAMIN 100% STERIL & ADEM
# =========================================================================
import glob
import torch
import numpy as np
from PIL import Image

# Mengambil fungsi spectrogram dari melspecto_folderauto.py
from melspecto_folderauto import load_audio_to_numpy, audio_to_frames, create_mel_filterbank

# Mengambil blueprint arsitektur neural network dari train_crnn.py
try:
    from train_crnn import MusicCRNN
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Gagal meng-import arsitektur model! Pastikan nama file training kamu "
        "adalah 'train_crnn.py' dan berada di folder yang sama dengan skrip ini."
    )

# =========================================================================
# DATA PIPELINE: AUDIO MP3 DIRECTLY TO TENSOR (ON-THE-FLY)
# =========================================================================
def pipeline_audio_to_tensor(file_path, target_size=(128, 512)):
    """Memproses file audio langsung menjadi tensor input PyTorch [1, 1, 128, 512]"""
    # 1. Jalankan ekstraksi DSP dasar
    signal, sr = load_audio_to_numpy(file_path, target_sr=22050)
    hann_window = lambda N: 0.5 * (1 - np.cos(2 * np.pi * np.arange(N) / (N - 1)))
    frames = audio_to_frames(signal, 2048, 512, hann_window)
    
    # 2. Hitung Power Spectrum FFT
    stft_matrix = np.fft.rfft(frames, n=2048, axis=-1)
    power_spectrum = (np.abs(stft_matrix) ** 2) / 2048
    
    # 3. Buat Mel Filterbank (KUNCI n_mels wajib ditulis 128 secara eksplisit!)
    mel_filters = create_mel_filterbank(sr, n_fft=2048, n_mels=128)
    mel_spec = np.dot(power_spectrum, mel_filters.T).T
    
    # 4. Log Desibel Scaling
    mel_spec_db = 10 * np.log10(np.maximum(mel_spec, 1e-10))
    mel_spec_db -= np.max(mel_spec_db)
    
    # =========================================================================
    # FIX SINKRONISASI UKURAN GAMBAR (PENTING BIAR HASIL AKHIR CNN KONSISTEN 1024)
    # =========================================================================
    # Map ke rentang pixel 0-255
    spec_normalized = ((mel_spec_db + 80) * (255 / 80)).clip(0, 255).astype(np.uint8)
    
    # Ubah ke PIL Image
    img = Image.fromarray(spec_normalized)
    
    # KUNCI UTAMA: Pastikan target_size bernilai (Width, Height) = (512, 128) di PIL
    # Di PyTorch, ukuran ini akan dibaca terbalik menjadi [1, Tinggi (128), Lebar (512)]
    img = img.resize((512, 128), resample=Image.Resampling.BILINEAR)
    img_np = np.array(img, dtype=np.float32)
    
    # Normalisasi biner ulang dari scratch ke skala [-1.0, 1.0]
    img_tensor = torch.from_numpy(img_np)
    img_tensor = (img_tensor / 127.5) - 1.0
    
    # Tambahkan dimensi channel di depan agar menjadi bentuk [1, 128, 512]
    img_tensor = img_tensor.unsqueeze(0)
    
    # Tambahkan dimensi Batch agar pas masuk ke model: [1, 1, 128, 512]
    return img_tensor.unsqueeze(0)


# =========================================================================
# MAIN EVALUASI EXECUTION
# =========================================================================
def run_mbti_inference(test_folder_path, model_weights_path='model_mbti_crnn.pth'):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n[SYSTEM] Menggunakan Akselerasi Testing: {device}")
    
    model = MusicCRNN(num_classes=4)
    
    if os.path.exists(model_weights_path):
        model.load_state_dict(torch.load(model_weights_path, map_location=device))
        print(f"[SUKSES] Bobot model '{model_weights_path}' berhasil dimuat!")
    else:
        print(f"[WARNING] File bobot '{model_weights_path}' tidak ditemukan! Menggunakan bobot acak.")
    
    model.to(device)
    model.eval()
    
    test_folder_path = os.path.normpath(test_folder_path)
    audio_files = glob.glob(os.path.join(test_folder_path, "*.mp3"))
        
    print(f"[INFO] Menemukan {len(audio_files)} lagu .mp3 baru di folder testing.\n")
    if len(audio_files) == 0:
        print("[ERROR] Folder testing kosong atau jalur salah.")
        return

    print(f"{'JUDUL LAGU':<40} | {'E vs I':<12} | {'N vs S':<12} | {'T vs F':<12} | {'J vs P':<12}")
    print("-" * 95)

    with torch.no_grad():
        for file_path in audio_files:
            file_name = os.path.basename(file_path)
            try:
                input_tensor = pipeline_audio_to_tensor(file_path).to(device)
                probabilities = model(input_tensor).squeeze(0).cpu().numpy()
                
                prob_E = probabilities[0] * 100
                prob_N = probabilities[1] * 100
                prob_F = probabilities[2] * 100
                prob_J = probabilities[3] * 100
                
                str_E_I = f"E: {prob_E:.1f}%" if prob_E >= 50 else f"I: {(100-prob_E):.1f}%"
                str_N_S = f"N: {prob_N:.1f}%" if prob_N >= 50 else f"S: {(100-prob_N):.1f}%"
                str_T_F = f"F: {prob_F:.1f}%" if prob_F >= 50 else f"T: {(100-prob_F):.1f}%"
                str_J_P = f"J: {prob_J:.1f}%" if prob_J >= 50 else f"P: {(100-prob_J):.1f}%"
                
                truncated_name = file_name if len(file_name) <= 40 else file_name[:37] + "..."
                print(f"{truncated_name:<40} | {str_E_I:<12} | {str_N_S:<12} | {str_T_F:<12} | {str_J_P:<12}")
            except Exception as e:
                print(f"[ERR] Gagal memproses {file_name}: {e}")

if __name__ == '__main__':
    # Otomatis arahkan ke folder lokal test-audio-unseen
    folder_uji = os.path.join(current_dir, "test-audio-unseen")
    weights_file = os.path.join(current_dir, 'model_mbti_crnn.pth')
    
    run_mbti_inference(folder_uji, model_weights_path=weights_file)