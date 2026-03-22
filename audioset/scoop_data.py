import os
import json
import torch
import numpy as np
import librosa
from tqdm import tqdm
from huggingface_hub import list_repo_files, hf_hub_download
import datasets
from datasets import load_dataset

# ================== 配置 ==================

REPO_ID = "agkphysics/AudioSet"
LOCAL_SHARD_DIR = "D:/audioset/temp_shards"
OUTPUT_DIR = "D:/audioset/scooped_v3"
STATE_FILE = os.path.join(OUTPUT_DIR, "state.json")

os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "600")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

SAMPLE_RATE = 16000
DURATION = 10
N_MFCC = 40

TARGET_DANGER = 5000
TARGET_SAFE = 2500

# ===== 标签映射 =====

DANGEROUS_MAPPING = {
    "Siren": ["Police car (siren)", "Fire engine, fire truck (siren)", "Ambulance (siren)", "Siren"],
    "Car horn": ["Vehicle horn, car horn, honking", "Air horn, truck horn"],
    "Fire alarm": ["Fire alarm"],
    "Smoke alarm": ["Smoke detector, smoke alarm"],
    "Explosion": ["Explosion", "Gunshot, gunfire", "Artillery fire"],
    "Glass breaking": ["Glass"],
    "Baby cry": ["Baby cry, infant cry"],
    "Dog bark": ["Dog", "Canidae, dogs, wolves"],
    "Knock": ["Knock"],
    "Footsteps": ["Walk, footsteps"]
}

SAFE_LABELS = ["Speech", "Music", "Rain", "Wind", "Bird", "Laughter", "Silence", "Water", "Walking"]

ALL_LABELS = sorted(list(DANGEROUS_MAPPING.keys()) + SAFE_LABELS)
label2id = {l: i for i, l in enumerate(ALL_LABELS)}
NUM_CLASSES = len(ALL_LABELS)

os.makedirs(LOCAL_SHARD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================== 状态管理 ==================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "processed_shards": [],
        "counts": {l: 0 for l in ALL_LABELS}
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ================== MFCC ==================

def extract_mfcc(audio, sr):
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)

    if sr != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)

    target_len = SAMPLE_RATE * DURATION
    if len(audio) > target_len:
        audio = audio[:target_len]
    else:
        audio = np.pad(audio, (0, target_len - len(audio)))

    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=SAMPLE_RATE,
        n_mfcc=N_MFCC,
        n_fft=512,
        hop_length=256,
    )

    return mfcc.astype(np.float32)

# ================== 判断标签是否匹配 ==================

def match_labels(human_labels, counts):

    matched_ids = []
    is_useful = False

    # 危险类别
    for cat, actual_names in DANGEROUS_MAPPING.items():
        if any(name in human_labels for name in actual_names):
            if counts[cat] < TARGET_DANGER:
                matched_ids.append(label2id[cat])
                counts[cat] += 1
                is_useful = True

    # 安全类别
    for s_label in SAFE_LABELS:
        if s_label in human_labels:
            if counts[s_label] < TARGET_SAFE:
                matched_ids.append(label2id[s_label])
                counts[s_label] += 1
                is_useful = True

    return is_useful, matched_ids

# ================== 处理 shard ==================

def process_shard(shard_name, state):

    print(f"\n📦 下载 shard: {shard_name}")

    max_retries = 5
    shard_path = None

    for attempt in range(max_retries):
        try:
            shard_path = hf_hub_download(
                repo_id=REPO_ID,
                filename=shard_name,
                repo_type="dataset",
                local_dir=LOCAL_SHARD_DIR,
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            break
        except Exception as e:
            print(f"⚠️ 下载失败: {e}，重试 {attempt+1}/{max_retries}")

    if shard_path is None:
        print(f"❌ 放弃 shard: {shard_name}")
        return

    print("📖 本地读取 parquet（纯离线模式）")

    # 关键修改：关闭 streaming
    dataset = load_dataset(
        "parquet",
        data_files=shard_path,
        split="train",
        streaming=False,
    )

    shard_output = []

    for ex in tqdm(dataset, desc=shard_name):

        try:
            human_labels = ex.get("human_labels", [])

            is_useful, matched_ids = match_labels(
                human_labels,
                state["counts"]
            )

            if not is_useful:
                continue

            # 这里 audio 已经是解码好的（非 streaming）
            audio_np = ex["audio"]["array"]
            sr = ex["audio"]["sampling_rate"]

            mfcc = extract_mfcc(audio_np, sr)

            label_vec = np.zeros(NUM_CLASSES, dtype=np.float32)
            for lid in matched_ids:
                label_vec[lid] = 1.0

            shard_output.append({
                "mfcc": mfcc,
                "label": label_vec
            })

            if all(
                state["counts"][l] >= (TARGET_DANGER if l in DANGEROUS_MAPPING else TARGET_SAFE)
                for l in ALL_LABELS
            ):
                print("🎯 所有类别已达到目标")
                break

        except Exception as e:
            continue

    # 保存
    if shard_output:
        file_name = os.path.basename(shard_name).replace(".parquet", ".pt")
        out_path = os.path.join(OUTPUT_DIR, file_name)
        torch.save(shard_output, out_path)
        print("💾 保存:", out_path)

    # 删除 shard
    os.remove(shard_path)

    state["processed_shards"].append(shard_name)
    save_state(state)

# ================== 主函数 ==================

def main():

    state = load_state()

    shard_files = [f"data/unbal_train/{i:03}.parquet" for i in range(870)]

    for shard in shard_files:

        if shard in state["processed_shards"]:
            continue

        process_shard(shard, state)

        if all(
            state["counts"][l] >= (TARGET_DANGER if l in DANGEROUS_MAPPING else TARGET_SAFE)
            for l in ALL_LABELS
        ):
            break

    print("\n✅ 处理完成")
    print("最终计数：")
    for k, v in state["counts"].items():
        print(f"{k:20}: {v}")

if __name__ == "__main__":
    main()
