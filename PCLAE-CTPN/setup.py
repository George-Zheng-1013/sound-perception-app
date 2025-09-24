#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目安装和配置脚本
"""

import os
import sys
from pathlib import Path

def setup_project():
    """设置项目环境"""
    project_root = Path(__file__).parent
    
    # 检查必要文件是否存在
    required_files = [
        "CLAP_weights_2023.pth",
        "category_mapping.csv",
        "DATASET"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"警告: 缺少以下必要文件: {', '.join(missing_files)}")
        return False
    
    # 创建必要目录
    dirs_to_create = ["log", "results", "temp_audio"]
    for dir_name in dirs_to_create:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"创建目录: {dir_path}")
    
    print("项目设置完成！")
    return True

if __name__ == "__main__":
    setup_project()