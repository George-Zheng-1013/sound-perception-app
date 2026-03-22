# ====================== 第一步：环境配置 ======================
import os
import shutil
import random
import multiprocessing
import io
import soundfile as sf
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import librosa
import matplotlib.pyplot as plt
from tqdm import tqdm
import datasets
from datasets import load_dataset, DownloadConfig
from huggingface_hub import HfApi
from sklearn.metrics import f1_score

# 1. 强制设置镜像和缓存
CACHE_DIR = "D:/audioset/dataset"
os.environ["HF_HOME"] = CACHE_DIR
os.environ["DATASETS_CACHE"] = os.path.join(CACHE_DIR, "datasets")
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TEMP"] = os.path.join(CACHE_DIR, "temp")
os.environ["TMP"] = os.path.join(CACHE_DIR, "temp")
os.makedirs(os.environ["TEMP"], exist_ok=True)
HfApi.DEFAULT_ENDPOINT = "https://hf-mirror.com"

# 2. 随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# ====================== 第二步：核心参数（极简优化版） ======================
# 筛选出的 Top 10 最具代表性的危险标签
DANGEROUS_LABELS = [
    "Siren", "Car horn", "Fire alarm", "Smoke alarm", "Explosion", 
    "Glass breaking", "Baby cry", "Dog bark", "Knock", "Footsteps"
]

# 精简后的 10 个安全标签
SAFE_LABELS = [
    "Speech", "Music", "Rain", "Wind", "Bird", 
    "Television", "Laughter", "Silence", "Water", "Walking"
]

ALL_TARGET_LABELS = sorted(list(set(DANGEROUS_LABELS + SAFE_LABELS)))
label2id = {label: i for i, label in enumerate(ALL_TARGET_LABELS)}
id2label = {i: label for label, i in label2id.items()}
NUM_CLASSES = len(ALL_TARGET_LABELS)

SAMPLE_RATE = 16000
DURATION = 10
N_MFCC = 40
BATCH_SIZE = 32
EPOCHS = 60 # 标签减少，可以多训练几轮
LR = 1e-3

# 预处理数据保存目录（更新为 v5，因为标签集大幅精简）
PREPROCESSED_DIR = "D:/audioset/preprocessed_v5"
os.makedirs(PREPROCESSED_DIR, exist_ok=True)

# ====================== 第三步：数据预处理 ======================

def process_example(example):
    h_labels = example.get("human_labels", [])
    target_ids = [label2id[l] for l in h_labels if l in label2id]
    if not target_ids: return None
    label_vec = np.zeros(NUM_CLASSES, dtype=np.float32)
    for tid in target_ids: label_vec[tid] = 1.0
    try:
        audio_data = example["audio"]
        if isinstance(audio_data, dict) and "bytes" in audio_data:
            audio, sr = sf.read(io.BytesIO(audio_data["bytes"]))
        else:
            audio, sr = audio_data["array"], audio_data["sampling_rate"]
        if len(audio.shape) > 1: audio = np.mean(audio, axis=1)
        if sr != SAMPLE_RATE: audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        target_length = SAMPLE_RATE * DURATION
        if len(audio) > target_length: audio = audio[:target_length]
        else: audio = np.pad(audio, (0, target_length - len(audio)), mode="constant")
        mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=N_MFCC, n_fft=512, hop_length=256)
        return {"mfcc": mfcc, "label": label_vec}
    except: return None

existing_files = [f for f in os.listdir(PREPROCESSED_DIR) if f.endswith(".pt")]

if not existing_files:
    print("\n📥 开始全量预处理 v5（极简标签集）...")
    LOCAL_DATA_DIR = "D:/audioset/dataset/datasets--agkphysics--AudioSet/snapshots/0c609e8302cf139307f639c57652032af0a88041/data/bal_train"
    parquet_files = [os.path.join(LOCAL_DATA_DIR, f) for f in os.listdir(LOCAL_DATA_DIR) if f.endswith(".parquet")]
    raw_dataset = load_dataset("parquet", data_files={"train": parquet_files}, split="train", streaming=True).cast_column("audio", datasets.Audio(decode=False))
    
    current_chunk, chunk_size, chunk_count = [], 1000, 0
    for ex in tqdm(raw_dataset, desc="预处理进度"):
        res = process_example(ex)
        if res:
            current_chunk.append(res)
            if len(current_chunk) >= chunk_size:
                torch.save(current_chunk, os.path.join(PREPROCESSED_DIR, f"chunk_{chunk_count}.pt"))
                current_chunk, chunk_count = [], chunk_count + 1
    if current_chunk: torch.save(current_chunk, os.path.join(PREPROCESSED_DIR, f"chunk_{chunk_count}.pt"))
    print(f"✅ 预处理完成。")

# ====================== 第四步：模型架构与数据加载 ======================

class SpecAugment(nn.Module):
    def __init__(self, freq_mask_range=15, time_mask_range=30):
        super().__init__()
        self.freq_mask_range = freq_mask_range
        self.time_mask_range = time_mask_range
    def forward(self, x):
        if not self.training: return x
        f = random.randint(0, self.freq_mask_range)
        f0 = random.randint(0, x.shape[2] - f)
        x[:, :, f0:f0+f, :] = 0
        t = random.randint(0, self.time_mask_range)
        t0 = random.randint(0, x.shape[3] - t)
        x[:, :, :, t0:t0+t] = 0
        return x

class AudioShardedDataset(Dataset):
    def __init__(self, directory, split="train", split_ratio=0.8):
        self.files = sorted([os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".pt")])
        random.seed(seed); random.shuffle(self.files)
        split_idx = int(len(self.files) * split_ratio)
        self.files = self.files[:split_idx] if split == "train" else self.files[split_idx:]
        self.data = []
        for f in tqdm(self.files, desc=f"加载{split}数据"): self.data.extend(torch.load(f))
    def __len__(self): return len(self.data)
    def __getitem__(self, idx):
        item = self.data[idx]
        return torch.tensor(item["mfcc"], dtype=torch.float32).unsqueeze(0), torch.tensor(item["label"], dtype=torch.float32)

print("🚀 加载数据...")
train_dataset = AudioShardedDataset(PREPROCESSED_DIR, split="train")
val_dataset = AudioShardedDataset(PREPROCESSED_DIR, split="val")
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

# 计算类别权重
all_labels = np.array([item["label"] for item in train_dataset.data])
pos_counts = np.sum(all_labels, axis=0)
neg_counts = len(all_labels) - pos_counts
pos_weights = torch.tensor(neg_counts / (pos_counts + 1e-6), dtype=torch.float32).to(DEVICE)

class ResBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride), nn.BatchNorm2d(out_channels))
    def forward(self, x):
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return torch.relu(out)

class AudioResNet(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.augment = SpecAugment()
        self.layer1 = nn.Sequential(nn.Conv2d(1, 64, kernel_size=3, padding=1), nn.BatchNorm2d(64), nn.ReLU())
        self.res1 = ResBlock(64, 64)
        self.pool1 = nn.MaxPool2d(2)
        self.res2 = ResBlock(64, 128)
        self.pool2 = nn.MaxPool2d(2)
        self.res3 = ResBlock(128, 256)
        self.pool3 = nn.MaxPool2d(2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Sequential(nn.Flatten(), nn.Linear(256, 512), nn.ReLU(), nn.Dropout(0.5), nn.Linear(512, num_classes))
    def forward(self, x):
        x = self.augment(x)
        x = self.layer1(x)
        x = self.pool1(self.res1(x))
        x = self.pool2(self.res2(x))
        x = self.pool3(self.res3(x))
        x = self.avgpool(x)
        x = self.fc(x)
        return x

model = AudioResNet(NUM_CLASSES).to(DEVICE)
criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weights).to(DEVICE)
optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=5e-3)
scheduler = optim.lr_scheduler.OneCycleLR(optimizer, max_lr=LR, steps_per_epoch=len(train_loader), epochs=EPOCHS)

# ====================== 第五步：训练逻辑 ======================
def calculate_metrics(outputs, labels):
    probs = torch.sigmoid(outputs).cpu().detach().numpy()
    preds = (probs > 0.5).astype(float)
    y_true = labels.cpu().numpy()
    f1 = f1_score(y_true, preds, average='macro', zero_division=0)
    pos_mask = (y_true == 1.0)
    recall = (preds[pos_mask] == 1.0).mean() if pos_mask.sum() > 0 else 0.0
    precision = (preds[pos_mask] == 1.0).sum() / (preds.sum() + 1e-6)
    return f1, recall, precision

def run_epoch(model, loader, criterion, optimizer=None):
    model.train() if optimizer else model.eval()
    total_loss, total_f1, total_recall, total_prec = 0, 0, 0, 0
    with torch.set_grad_enabled(optimizer is not None):
        for mfcc, labels in tqdm(loader, leave=False):
            mfcc, labels = mfcc.to(DEVICE), labels.to(DEVICE)
            if optimizer: optimizer.zero_grad()
            outputs = model(mfcc)
            loss = criterion(outputs, labels)
            if optimizer:
                loss.backward(); optimizer.step(); scheduler.step()
            f1, recall, prec = calculate_metrics(outputs, labels)
            total_loss += loss.item(); total_f1 += f1; total_recall += recall; total_prec += prec
    return total_loss / len(loader), total_f1 / len(loader), total_recall / len(loader), total_prec / len(loader)

print("\n🚀 开始精简版终极训练（v5）...")
best_v_f1, patience, trials = 0, 10, 0
for epoch in range(EPOCHS):
    t_loss, t_f1, t_rec, t_pre = run_epoch(model, train_loader, criterion, optimizer)
    v_loss, v_f1, v_rec, v_pre = run_epoch(model, val_loader, criterion)
    print(f"Epoch {epoch+1:02d} | Loss: {t_loss:.3f}/{v_loss:.3f} | F1: {t_f1:.3f}/{v_f1:.3f} | Rec: {t_rec:.3f}/{v_rec:.3f} | Pre: {t_pre:.3f}/{v_pre:.3f}")
    if v_f1 > best_v_f1:
        best_v_f1 = v_f1
        trials = 0
        torch.save({'model_state_dict': model.state_dict(), 'label2id': label2id, 'id2label': id2label, 'dangerous_labels': DANGEROUS_LABELS, 'num_classes': NUM_CLASSES}, "D:/audioset/danger_detector_detailed.pth")
        print(f"⭐ 发现更好的模型 (F1: {v_f1:.4f})")
    else:
        trials += 1
        if trials >= patience:
            print(f"🛑 早停。")
            break
print("\n✅ 训练完成。")
