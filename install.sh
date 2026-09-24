#!/bin/bash
echo "🚀 ArisuFxPy Installation Started..."

# Update Termux
pkg update && pkg upgrade -y

# Install required dependencies
pkg install python clang cmake ninja git -y

# Clone your repo
git clone https://github.com/arisugpt/ArisuFxPy.git
cd ArisuFxPy

# Install the package
pip install .

echo "✅ ArisuFxPy Successfully Installed!"
echo "Run 'python arisu_tool.py' to start the tool."