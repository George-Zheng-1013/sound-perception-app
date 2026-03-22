import os
import glob

import torch
from tqdm import tqdm


root = r"E:\audioset1\AudioSet\panns_filtered"
output_path = os.path.join(root, "panns_merged.pt")


def main():
    pt_files = sorted(glob.glob(os.path.join(root, "panns_chunk_*.pt")))

    if not pt_files:
        print("没有找到任何 panns_chunk_*.pt 文件，请检查目录:", root)
        return

    all_waveforms = []
    all_labels = []

    print("开始合并 shard ...")

    for path in pt_files:
        print("加载:", os.path.basename(path))
        data = torch.load(path, map_location="cpu")

        for sample in tqdm(data):
            wav = sample["waveform"]  # numpy
            lab = sample["labels"]

            all_waveforms.append(torch.from_numpy(wav))
            all_labels.append(torch.from_numpy(lab))

    print("拼接成大 Tensor ...")

    waveforms = torch.stack(all_waveforms)  # [N, 160000]
    labels = torch.stack(all_labels)  # [N, 16]

    print("保存到:", output_path)

    torch.save(
        {
            "waveforms": waveforms,
            "labels": labels,
        },
        output_path,
    )

    print("完成。总样本数:", waveforms.shape[0])


if __name__ == "__main__":
    main()
