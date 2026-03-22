import os
from collections import defaultdict
import json

import numpy as np
import pyarrow.parquet as pq
import libros
import torch
import soundfile as sf
import io


DATA_ROOT = r"E:\audioset1\AudioSet"
OUTPUT_DIR = r"E:\audioset1\AudioSet\panns_filtered"
ONTOLOGY_PATH = r"D:\audioset\ontology.json"

SAMPLE_RATE = 16000
DURATION = 10
TARGET_LEN = SAMPLE_RATE * DURATION

DANGER_LABELS = [
    "Vehicle",
    "Alarm",
    "Explosion",
    "Car passing by",
    "Accelerating, revving, vroom",
    "Engine",
    "Truck",
    "Motor vehicle (road)",
]

SAFE_LABELS = [
    "Speech",
    "Male speech, man speaking",
    "Female speech, woman speaking",
    "Music",
    "Acoustic guitar",
    "Violin, fiddle",
    "Dog",
    "Bird",
]

ALL_LABELS = DANGER_LABELS + SAFE_LABELS
LABEL2IDX = {name: i for i, name in enumerate(ALL_LABELS)}

LABEL_MAX = {name: 1000 for name in ALL_LABELS}

ONT_NAME_TO_TARGET = {
    # 危险类（精确匹配 ontology 名字）
    "Vehicle": "Vehicle",
    "Alarm": "Alarm",
    "Fire alarm": "Alarm",
    "Car alarm": "Alarm",
    "Reversing beeps": "Alarm",
    "Alarm clock": "Alarm",
    "Smoke detector, smoke alarm": "Alarm",
    "Explosion": "Explosion",
    "Car passing by": "Car passing by",
    "Accelerating, revving, vroom": "Accelerating, revving, vroom",
    "Engine": "Engine",
    "Truck": "Truck",
    "Motor vehicle (road)": "Motor vehicle (road)",
    # 安全类
    "Speech": "Speech",
    "Male speech, man speaking": "Male speech, man speaking",
    "Female speech, woman speaking": "Female speech, woman speaking",
    "Music": "Music",
    "Acoustic guitar": "Acoustic guitar",
    "Violin, fiddle": "Violin, fiddle",
    "Dog": "Dog",
    "Bird": "Bird",
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def collect_parquet_files(root):
    parquet_files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".parquet"):
                parquet_files.append(os.path.join(dirpath, name))
    return sorted(parquet_files)


def process_audio(audio_array, sr):
    x = np.asarray(audio_array, dtype=np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SAMPLE_RATE:
        x = librosa.resample(x, orig_sr=sr, target_sr=SAMPLE_RATE)
    if len(x) > TARGET_LEN:
        x = x[:TARGET_LEN]
    else:
        x = np.pad(x, (0, TARGET_LEN - len(x)))
    return x.astype(np.float32)


def load_ontology():
    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    id_to_name = {}
    for entry in data:
        label_id = entry.get("id")
        name = entry.get("name") or entry.get("display_name")
        if label_id and name:
            id_to_name[label_id] = name
    return id_to_name


def match_labels(label_names, counts):
    matched = []
    for ont_name in label_names:
        target = ONT_NAME_TO_TARGET.get(ont_name)
        if target is None:
            continue
        if counts[target] < LABEL_MAX[target]:
            if target not in matched:
                matched.append(target)
    return matched


def all_caps_reached(counts):
    for name in ALL_LABELS:
        if counts[name] < LABEL_MAX[name]:
            return False
    return True


def main():
    parquet_files = collect_parquet_files(DATA_ROOT)
    if not parquet_files:
        print("没有在本地找到任何 parquet 文件，请检查路径:", DATA_ROOT)
        return

    parquet_files = parquet_files[:50]

    id_to_name = load_ontology()

    print(f"发现 {len(parquet_files)} 个 parquet 分片，将开始筛选标签并保存为 PANNs 数据格式")

    counts = defaultdict(int)
    chunk = []
    chunk_size = 500
    chunk_idx = 0
    total_selected = 0
    stop = False
    seen_label_names = set()

    for shard_path in parquet_files:
        if stop:
            break
        print(f"\n📦 处理分片: {shard_path}")
        pf = pq.ParquetFile(shard_path)

        for batch in pf.iter_batches(batch_size=16):
            if stop:
                break
            batch_dict = batch.to_pydict()
            labels_id_list = batch_dict.get("labels", [])
            audio_list = batch_dict.get("audio", [])

            for label_ids, audio_info in zip(labels_id_list, audio_list):
                if label_ids is None or audio_info is None:
                    continue
                label_names = []
                for lid in label_ids:
                    name = id_to_name.get(lid)
                    if name:
                        label_names.append(name)
                if not label_names:
                    continue

                for n in label_names:
                    seen_label_names.add(n)

                matched_names = match_labels(label_names, counts)
                if not matched_names:
                    continue

                for name in matched_names:
                    counts[name] += 1

                if isinstance(audio_info, dict):
                    if "array" in audio_info and "sampling_rate" in audio_info:
                        audio_array = audio_info["array"]
                        sr = audio_info["sampling_rate"]
                    elif "bytes" in audio_info:
                        try:
                            audio_bytes = audio_info["bytes"]
                            audio_array, sr = sf.read(io.BytesIO(audio_bytes))
                        except Exception:
                            continue
                    elif "path" in audio_info:
                        rel_path = audio_info["path"]
                        full_path = rel_path if os.path.isabs(rel_path) else os.path.join(DATA_ROOT, rel_path)
                        try:
                            audio_array, sr = librosa.load(full_path, sr=None, mono=False)
                        except Exception:
                            continue
                    else:
                        continue
                else:
                    continue

                audio_np = process_audio(audio_array, sr)

                label_vec = np.zeros(len(ALL_LABELS), dtype=np.float32)
                for name in matched_names:
                    idx = LABEL2IDX[name]
                    label_vec[idx] = 1.0

                sample = {
                    "waveform": audio_np,
                    "labels": label_vec,
                }
                chunk.append(sample)
                total_selected += 1

                if len(chunk) >= chunk_size:
                    out_path = os.path.join(OUTPUT_DIR, f"panns_chunk_{chunk_idx}.pt")
                    torch.save(chunk, out_path)
                    print(f"💾 保存分片: {out_path}，样本数: {len(chunk)}")
                    chunk = []
                    chunk_idx += 1

                if all_caps_reached(counts):
                    stop = True
                    break

    if chunk:
        out_path = os.path.join(OUTPUT_DIR, f"panns_chunk_{chunk_idx}.pt")
        torch.save(chunk, out_path)
        print(f"💾 保存分片: {out_path}，样本数: {len(chunk)}")

    print("\n✅ 筛选完成")
    print(f"总选中样本数: {total_selected}")
    print("各标签计数:")
    for name in ALL_LABELS:
        print(f"{name:25s}: {counts[name]}")

    print("\n该分片中出现过的部分标签名示例（最多前 50 个）：")
    for i, n in enumerate(sorted(seen_label_names)):
        if i >= 50:
            break
        print(n)


if __name__ == "__main__":
    main()
