import torch
# 1. 检查是否支持CUDA
print("torch.cuda.is_available():", torch.cuda.is_available())  # 输出False就是CPU版
# 2. 查看PyTorch安装信息
print("PyTorch版本：", torch.__version__)
print("CUDA版本（PyTorch内置）：", torch.version.cuda)