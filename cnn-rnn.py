import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from PIL import Image

# =========================================================================
# 1. CUSTOM DATASET FROM SCRATCH (No high-level wrappers)
# =========================================================================
class MusicMBTI_Dataset(Dataset):
    def __init__(self, csv_file, melspect_root_dir, target_size=(128, 512)):
        self.annotations = pd.read_csv(csv_file)
        self.root_dir = os.path.normpath(melspect_root_dir)
        self.target_size = target_size

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, index):
        # Extract row meta
        track_name = self.annotations.iloc[index]['Track Name']
        mbti_type = self.annotations.iloc[index]['MBTI']
        
        # Pull 4-head multi-label ground truth
        labels = torch.tensor([
            self.annotations.iloc[index]['E_I'],
            self.annotations.iloc[index]['N_S'],
            self.annotations.iloc[index]['T_F'],
            self.annotations.iloc[index]['J_P']
        ], dtype=torch.float32)

        # Locate corresponding .png
        folder_name = f"{mbti_type}-melspect"
        img_path = os.path.join(self.root_dir, folder_name, f"{track_name}.png")

        try:
            # Load raw pixels to Grayscale matrix
            with Image.open(img_path) as img:
                img = img.convert('L')
                # Resize from scratch to force matrix uniformity
                img = img.resize(self.target_size)
                img_np = np.array(img, dtype=np.float32)
        except Exception:
            # Fallback guardrail if a file was corrupted or missing
            img_np = np.zeros(self.target_size, dtype=np.float32)

        # Normalization manually from scratch: map pixel values [0, 255] -> [-1.0, 1.0]
        img_tensor = torch.from_numpy(img_np)
        img_tensor = (img_tensor / 127.5) - 1.0
        
        # Add a channel dimension: resulting shape [1, 128, 512]
        img_tensor = img_tensor.unsqueeze(0)

        return img_tensor, labels


# =========================================================================
# 2. CRNN ARCHITECTURE FROM SCRATCH
# =========================================================================
class MusicCRNN(nn.Module):
    def __init__(self, num_classes=4):
        super(MusicCRNN, self).__init__()
        
        # CNN block extracts the structural visual timbre characteristics
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # Resolves to [16, 64, 256]
            
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # Resolves to [32, 32, 128]
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # Final feature map size: [64, 16, 64]
        )
        
        # Input size for RNN: Channel count * Remaining height (64 * 16 = 1024)
        self.rnn_input_size = 64 * 16 
        self.hidden_size = 128
        
        # Bidirectional GRU logs the temporal transitions of song progression
        self.rnn = nn.GRU(
            input_size=self.rnn_input_size, 
            hidden_size=self.hidden_size, 
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        
        # Final fully-connected layer mapped to multi-head Sigmoid percentages
        self.fc = nn.Linear(self.hidden_size * 2, num_classes)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # 1. Pass through visual layer
        x = self.cnn(x) 
        
        # 2. Reshape matrix for sequence modeling
        batch_size, channels, height, width = x.size()
        x = x.view(batch_size, channels * height, width) # Merges columns into vector features
        x = x.permute(0, 2, 1) # Translates format to [Batch, Time-steps (Width), Features]
        
        # 3. Parse sequence
        out, _ = self.rnn(x)
        
        # 4. Grab output state of the very last sequence time-step (song conclusion)
        out = out[:, -1, :] 
        
        # 5. Fire prediction probabilities
        return self.sigmoid(self.fc(out))


# =========================================================================
# 3. TRAINING LOOP EXECUTION BLOCK
# =========================================================================
if __name__ == '__main__':
    # 1. Tentukan device eksekusi (Otomatis deteksi CUDA/GPU)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Executing architecture on device: {device}")

    # 2. Ambil lokasi folder tempat skrip 'train_crnn.py' ini berada secara otomatis
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 3. TEMBAK PATH FILE MENGGUNAKAN RELATIVE PATH
    # Ini mengasumsikan file CSV dan folder dataset kamu berada satu atap dengan skrip ini
    csv_path = os.path.join(current_dir, "dataset_mbti_musik.csv")
    audio_root_dir = current_dir  # Folder utama yang menampung 'INFJ-melspect', 'ENTP-melspect', dsb.

    print(f"[INFO] Jalur CSV Terdeteksi : {csv_path}")
    print(f"[INFO] Jalur Root Audio     : {audio_root_dir}")

    # 4. Masukkan variabel path tersebut ke dalam Inisialisasi Dataset Custom kita
    dataset = MusicMBTI_Dataset(
        csv_file=csv_path, 
        melspect_root_dir=audio_root_dir
    )
    
    # 5. Siapkan DataLoader (Flag optimasi RAM/GPU dari scratch)
    train_loader = DataLoader(
        dataset, 
        batch_size=32, 
        shuffle=True, 
        num_workers=2,       # Membaca gambar sekuensial di background thread
        pin_memory=True      # Mengunci halaman RAM untuk transfer cepat ke VRAM GPU
    )

    # Initialize model objects
    model = MusicCRNN(num_classes=4).to(device)
    
    # BCELoss is mathematically required for independent binary multi-label classification
    criterion = nn.BCELoss() 
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Simple execution loop mock run
    model.train()
    print("Beginning CRNN training loop cycles...")
    for epoch in range(5):  # 5 sample test epochs
        running_loss = 0.0
        for batch_idx, (images, labels) in enumerate(train_loader):
            # Move data directly to target execution core
            images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            
            # Forward path
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            # Backward path optimization execution
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        print(f"Epoch [{epoch+1}/5] Completed - Average Loss: {running_loss / len(train_loader):.4f}")