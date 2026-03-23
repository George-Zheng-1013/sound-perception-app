import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, SubsetRandomSampler
from tqdm import tqdm
import numpy as np

from cnn14_models import Cnn14  # 你现有的 CNN14 模型
from panns_dataset import (
    ALL_LABELS,
    PannsFastDataset,
)  # PannsFastDataset 读取你的 .pt 数据

device = "cuda" if torch.cuda.is_available() else "cpu"


def compute_map(y_true: np.ndarray, y_score: np.ndarray) -> float:
    num_classes = y_true.shape[1]
    ap_list = []
    for c in range(num_classes):
        y = y_true[:, c]
        scores = y_score[:, c]
        if y.sum() == 0:
            continue
        order = np.argsort(-scores)
        y_sorted = y[order]
        tp = np.cumsum(y_sorted)
        fp = np.cumsum(1 - y_sorted)
        precision = tp / (tp + fp + 1e-8)
        recall = tp / (y.sum() + 1e-8)
        recall_diff = np.diff(np.concatenate(([0.0], recall)))
        ap = np.sum(precision * recall_diff)
        ap_list.append(ap)
    if not ap_list:
        return 0.0
    return float(np.mean(ap_list))


# -------------------------------
# 轻量级分类器
# -------------------------------
class SimpleClassifier(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.fc = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        return self.fc(x)


class Cnn14WithMLP(nn.Module):
    def __init__(self, cnn_model: nn.Module, mlp: nn.Module):
        super().__init__()
        self.cnn = cnn_model
        self.mlp = mlp

    def forward(self, wav: torch.Tensor) -> torch.Tensor:
        out_dict = self.cnn(wav)
        emb = out_dict["clipwise_output"]
        logits = self.mlp(emb)
        return logits


# -------------------------------
# 加载预训练 CNN14 并冻结卷积层
# -------------------------------
def load_cnn14_for_features(checkpoint_path: str):
    base_model = Cnn14(
        sample_rate=16000,
        window_size=512,
        hop_size=160,
        mel_bins=64,
        fmin=50,
        fmax=8000,
        classes_num=527,
    )
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if "model" in state:
        base_model.load_state_dict(state["model"], strict=False)
    else:
        base_model.load_state_dict(state, strict=False)

    # 冻结 CNN14 所有参数
    for param in base_model.parameters():
        param.requires_grad = False

    # 不需要 fc_audioset，保留 clipwise embedding
    if hasattr(base_model, "fc_audioset"):
        base_model.fc_audioset = nn.Identity()

    if hasattr(base_model, "spec_augmenter"):
        base_model.spec_augmenter = nn.Identity()  # 不用增强，加速

    return base_model.to(device).eval()  # eval 模式


# -------------------------------
# 特征提取 DataLoader
# -------------------------------
def extract_embeddings(cnn_model, dataset, batch_size=16, num_workers=4):
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    embeddings = []
    labels = []

    with torch.no_grad():
        for wav, lbl in tqdm(loader, desc="Extracting embeddings"):
            wav = wav.to(device)
            out_dict = cnn_model(wav)
            emb = out_dict["clipwise_output"]  # [B, 2048]
            embeddings.append(emb.cpu())
            labels.append(lbl)

    embeddings = torch.cat(embeddings, dim=0)
    labels = torch.cat(labels, dim=0)
    return embeddings, labels


# -------------------------------
# 训练 MLP 分类器
# -------------------------------
def train_classifier(
    embeddings, labels, num_classes=len(ALL_LABELS), num_epochs=50, batch_size=16
):
    num_samples = embeddings.shape[0]
    indices = np.arange(num_samples)
    np.random.shuffle(indices)
    split = int(num_samples * 0.8)
    train_idx, val_idx = indices[:split], indices[split:]

    train_sampler = SubsetRandomSampler(train_idx)
    val_sampler = SubsetRandomSampler(val_idx)

    train_loader = DataLoader(
        torch.utils.data.TensorDataset(embeddings, labels),
        batch_size=batch_size,
        sampler=train_sampler,
    )
    val_loader = DataLoader(
        torch.utils.data.TensorDataset(embeddings, labels),
        batch_size=batch_size,
        sampler=val_sampler,
    )

    input_dim = embeddings.shape[1]
    model = SimpleClassifier(input_dim, num_classes).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    best_val_loss = float("inf")
    for epoch in range(num_epochs):
        # 训练
        model.train()
        train_loss_sum, train_count = 0.0, 0
        for emb_batch, lbl_batch in train_loader:
            emb_batch = emb_batch.to(device)
            lbl_batch = lbl_batch.to(device)
            logits = model(emb_batch)
            loss = criterion(logits, lbl_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss_sum += loss.item() * emb_batch.size(0)
            train_count += emb_batch.size(0)
        train_loss = train_loss_sum / train_count

        # 验证
        model.eval()
        val_loss_sum, val_count = 0.0, 0
        all_val_logits = []
        all_val_labels = []
        with torch.no_grad():
            for emb_batch, lbl_batch in val_loader:
                emb_batch = emb_batch.to(device)
                lbl_batch = lbl_batch.to(device)
                logits = model(emb_batch)
                loss = criterion(logits, lbl_batch)
                val_loss_sum += loss.item() * emb_batch.size(0)
                val_count += emb_batch.size(0)
                all_val_logits.append(logits.cpu())
                all_val_labels.append(lbl_batch.cpu())
        val_loss = val_loss_sum / val_count

        val_logits_np = torch.cat(all_val_logits, dim=0).numpy()
        val_labels_np = torch.cat(all_val_labels, dim=0).numpy()
        val_map = compute_map(val_labels_np, val_logits_np)

        print(
            f"Epoch {epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, mAP={val_map:.4f}"
        )

        # 保存最优模型
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), "mlp_classifier_best.pth")
            print(f"保存新最优模型，val_loss={best_val_loss:.4f}")

    return model


# -------------------------------
# 推理示例
# -------------------------------
def predict(model, cnn_model, waveform):
    """
    waveform: torch.Tensor, shape [T]
    """
    cnn_model.eval()
    model.eval()
    with torch.no_grad():
        wav = waveform.unsqueeze(0).to(device)  # [1, T]
        emb = cnn_model(wav)["clipwise_output"]  # [1, 2048]
        logits = model(emb)
        probs = torch.sigmoid(logits).squeeze(0)  # [16]
        # 多标签选择 threshold
        threshold = 0.5
        pred_labels = [ALL_LABELS[i] for i, p in enumerate(probs) if p >= threshold]
        return pred_labels


# -------------------------------
# 主流程
# -------------------------------
def main():
    merged_path = r"D:\audioset\panns_merged_alarm_balanced.pt"
    dataset = PannsFastDataset(merged_path)

    checkpoint_path = r"D:\audioset\Cnn14_16k_mAP=0.438.pth"
    cnn_model = load_cnn14_for_features(checkpoint_path)

    embeddings, labels = extract_embeddings(
        cnn_model, dataset, batch_size=16, num_workers=4
    )

    model = train_classifier(
        embeddings, labels, num_classes=len(ALL_LABELS), num_epochs=50, batch_size=16
    )

    # 训练完后，用单独的验证集进行验证
    val_merged_path = r"D:\audioset\panns_merged_alarm_balanced_val.pt"
    if not os.path.exists(val_merged_path):
        print(f"验证集文件不存在: {val_merged_path}")
    else:
        print(f"开始在独立验证集上评估: {val_merged_path}")
        val_dataset = PannsFastDataset(val_merged_path)
        val_embeddings, val_labels = extract_embeddings(
            cnn_model, val_dataset, batch_size=16, num_workers=4
        )
        val_loader = DataLoader(
            torch.utils.data.TensorDataset(val_embeddings, val_labels),
            batch_size=32,
            shuffle=False,
        )
        criterion = nn.BCEWithLogitsLoss()
        loss_sum, count = 0.0, 0
        with torch.no_grad():
            for emb_batch, lbl_batch in tqdm(
                val_loader, desc="Evaluating on external val set"
            ):
                emb_batch = emb_batch.to(device)
                lbl_batch = lbl_batch.to(device)
                logits = model(emb_batch)
                loss = criterion(logits, lbl_batch)
                loss_sum += loss.item() * emb_batch.size(0)
                count += emb_batch.size(0)
        avg_loss = loss_sum / count
        print(
            f"[验证集 {os.path.basename(val_merged_path)}] 平均 BCE loss: {avg_loss:.4f}"
        )

    # 保存端到端模型（Cnn14 + MLP）为一个 .pt 文件
    combined = Cnn14WithMLP(cnn_model, model)
    combined_out_path = r"D:\audioset\cnn14_mlp_combined.pt"
    torch.save(combined, combined_out_path)
    print(f"已将完整模型保存为: {combined_out_path}")


if __name__ == "__main__":
    main()
