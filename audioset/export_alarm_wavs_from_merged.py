import os
import sys
import random

import numpy as np
import torch
import soundfile as sf

from panns_dataset import ALL_LABELS


def export_wavs_random(merged_path: str, out_dir: str, sample_rate: int = 16000, limit: int = 100):
    if not os.path.exists(merged_path):
        raise FileNotFoundError(f"找不到 merged 文件: {merged_path}")

    os.makedirs(out_dir, exist_ok=True)

    data = torch.load(merged_path, map_location="cpu")

    waveforms = data.get("waveforms")
    labels = data.get("labels")

    if waveforms is None or labels is None:
        raise KeyError("merged 文件中找不到 'waveforms' 或 'labels' 键")

    if not torch.is_tensor(waveforms):
        waveforms = torch.as_tensor(waveforms)
    if not torch.is_tensor(labels):
        labels = torch.as_tensor(labels)

    num_samples = waveforms.shape[0]
    if num_samples == 0:
        print("数据集中没有任何样本")
        return

    if num_samples <= limit:
        selected_indices = list(range(num_samples))
    else:
        selected_indices = random.sample(range(num_samples), k=limit)

    print(f"总样本数: {num_samples}，将随机导出 {len(selected_indices)} 条到 {out_dir}")

    for i, idx in enumerate(selected_indices):
        wav = waveforms[idx].numpy().astype(np.float32)
        lab = labels[idx].numpy()

        pos_names = [ALL_LABELS[j] for j, v in enumerate(lab) if v > 0.5]
        label_str = "+".join(pos_names) if pos_names else "nolabel"

        filename = f"sample_{i:03d}_idx{idx:05d}_{label_str}.wav"
        out_path = os.path.join(out_dir, filename)

        sf.write(out_path, wav, sample_rate)
        print(f"已导出: {out_path}")

    print("导出完成")


def main():
    merged_path = r"D:\audioset\panns_merged_alarm_balanced_val.pt"
    out_dir = r"D:\audioset\exported_alarm_wavs"
    limit = 100

    print(f"使用写死配置随机导出样本（不限标签）：\n  merged 文件: {merged_path}\n  输出目录: {out_dir}\n  导出数量: {limit}")
    export_wavs_random(merged_path, out_dir, sample_rate=16000, limit=limit)


if __name__ == "__main__":
    main()
