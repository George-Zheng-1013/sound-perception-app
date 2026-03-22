import glob
import os
from typing import Tuple

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


ALL_LABELS = [
    "Vehicle",
    "Alarm",
    "Explosion",
    "Car passing by",
    "Accelerating, revving, vroom",
    "Engine",
    "Truck",
    "Motor vehicle (road)",
    "Speech",
    "Male speech, man speaking",
    "Female speech, woman speaking",
    "Music",
    "Acoustic guitar",
    "Violin, fiddle",
    "Dog",
    "Bird",
]


class PannsFastDataset(Dataset):
    def __init__(self, merged_path: str):
        print("正在加载合并后的数据文件...")
        data = torch.load(merged_path, map_location="cpu")
        self.waveforms = data["waveforms"]  # [N, 160000]
        self.labels = data["labels"]        # [N, 16]
        print("加载完成，总样本数:", self.waveforms.shape[0])

    def __len__(self):
        return self.waveforms.shape[0]

    def __getitem__(self, idx):
        return self.waveforms[idx], self.labels[idx]


def create_dataloader(
    root: str,
    batch_size: int = 16,
    num_workers: int = 4,
    pin_memory: bool = False,
) -> DataLoader:
    dataset = PannsFastDataset(root)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        drop_last=False,
        pin_memory=pin_memory,
    )
    return loader


if __name__ == "__main__":
    root = r"E:\audioset_dataset\panns_filtered"
    loader = create_dataloader(root, batch_size=8, num_workers=0)
    print("总样本数:", len(loader.dataset))
    for i, (wav, y) in enumerate(loader):
        print("batch", i, "waveform shape:", wav.shape, "labels shape:", y.shape)
        if i >= 1:
            break
