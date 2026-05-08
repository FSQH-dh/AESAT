#!/bin/bash
# 检查文件是否存在
if [ -f "main.py" ]; then
    echo "正在执行 main.py 文件..."
    python3 -u main.py
else
    echo "错误：未找到 main.py 文件，请确保文件存在并位于当前目录下。"
fi