import numpy as np
from scipy.io import wavfile
import soundfile as sf
import matplotlib.pyplot as plt

def load_audio(file_path):
    """Loads WAV, OGG, or FLAC files and normalizes to float32 [-1.0, 1.0]"""
    # soundfile natively handles .ogg and auto-normalizes to float32
    data, sr = sf.read(file_path, dtype='float32')
    
    if data.ndim > 1:  # Convert stereo to mono
        data = data.mean(axis=1)
        
    return np.ascontiguousarray(data), sr

def audio_to_frames(signal, frame_size, hop_size, window_fn):
    """Splits the continuous signal into overlapping, windowed frames."""
    signal_len = len(signal)
    # Calculate total number of frames
    num_frames = int(np.floor((signal_len - frame_size) / hop_size) + 1)
    
    # Extract frames using indexing strides
    shape = (num_frames, frame_size)
    strides = (signal.strides[0] * hop_size, signal.strides[0])
    frames = np.lib.stride_tricks.as_strided(signal, shape=shape, strides=strides)
    
    # Apply window function (e.g., Hann window) to prevent spectral leakage
    window = window_fn(frame_size)
    return frames * window

def hz_to_mel(hz):
    """Converts Frequency in Hz to Mel scale"""
    return 2595 * np.log10(1 + hz / 700.0)

def mel_to_hz(mel):
    """Converts Mel scale back to Frequency in Hz"""
    return 700 * (10**(mel / 2595.0) - 1)

def create_mel_filterbank(sr, n_fft, n_mels, fmin=0, fmax=None):
    """Generates triangular Mel filterbank matrix."""
    if fmax is None:
        fmax = sr / 2
        
    # 1. Map Hz range to Mel range
    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    
    # 2. Space points linearly in Mel scale, then convert back to Hz
    mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_pts = mel_to_hz(mel_pts)
    
    # 3. Bin frequencies to FFT bin indices
    bins = np.floor((n_fft + 1) * hz_pts / sr).astype(int)
    
    # 4. Construct the triangular filters
    filters = np.zeros((n_mels, int(n_fft // 2 + 1)))
    for m in range(1, n_mels + 1):
        for k in range(bins[m - 1], bins[m]):
            filters[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
        for k in range(bins[m], bins[m + 1]):
            filters[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])
            
    return filters

def custom_mel_spectrogram(audio_path, n_mels=128, frame_size=2048, hop_size=512):
    # 1. Load Audio
    signal, sr = load_audio(audio_path)
    
    # 2. Framing & Windowing (Hann Window)
    hann_window = lambda N: 0.5 * (1 - np.cos(2 * np.pi * np.arange(N) / (N - 1)))
    frames = audio_to_frames(signal, frame_size, hop_size, hann_window)
    
    # 3. Fast Fourier Transform (FFT) & Power Spectrum
    # Perform rfft (Real FFT) across each frame
    stft_matrix = np.fft.rfft(frames, n=frame_size, axis=-1)
    power_spectrum = (np.abs(stft_matrix) ** 2) / frame_size
    
    # 4. Apply Mel Filterbank
    # Matrix multiplication transforms Linear frequency spacing into Mel frequency spacing
    mel_filters = create_mel_filterbank(sr, n_fft=frame_size, n_mels=n_mels)
    mel_spec = np.dot(power_spectrum, mel_filters.T)
    
    # Transpose so rows = Mel bins, columns = Time frames (matching Librosa style)
    mel_spec = mel_spec.T
    
    # 5. Log Scaling (convert to Decibels)
    # Clip to avoid log(0)
    mel_spec_db = 10 * np.log10(np.maximum(mel_spec, 1e-10))
    # Normalize relative to peak power
    mel_spec_db -= np.max(mel_spec_db)
    
    return mel_spec_db

# --- Execution & Plotting ---
mel_matrix = custom_mel_spectrogram('C:/Users/loren/Desktop/mus_snowy.ogg')
plt.imshow(mel_matrix, aspect='auto', origin='lower', cmap='viridis')
plt.axis('off')
plt.savefig('scratch_mel.png', bbox_inches='tight', pad_inches=0)