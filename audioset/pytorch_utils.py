import torch
import torch.nn.functional as F


def do_mixup(x, mixup_lambda):
    if mixup_lambda is None:
        return x
    lam = mixup_lambda
    if not isinstance(lam, torch.Tensor):
        lam = torch.tensor(lam, device=x.device, dtype=x.dtype)
    while lam.dim() < x.dim():
        lam = lam.unsqueeze(-1)
    return x * lam + x.flip(0) * (1 - lam)


def interpolate(x, ratio):
    if ratio == 1:
        return x
    return F.interpolate(x, scale_factor=ratio, mode="nearest")


def pad_framewise_output(x, frames_num):
    if x.size(1) >= frames_num:
        return x[:, :frames_num, :]
    pad_len = frames_num - x.size(1)
    pad = x[:, -1:, :].repeat(1, pad_len, 1)
    return torch.cat([x, pad], dim=1)

