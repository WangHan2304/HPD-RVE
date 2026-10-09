#!/bin/bash
# ============================================================
# DAMASK 3.0 安装脚本 (WSL2 Ubuntu 24.04)
# ============================================================
# 用法: bash install_damask.sh
# 此脚本在WSL2 Ubuntu中运行

set -e

echo "========================================"
echo "  DAMASK 3.0 Installation via PPA"
echo "========================================"

# Step 1: 添加 DAMASK PPA 仓库
echo ""
echo "[1/3] Adding DAMASK PPA repository..."
sudo add-apt-repository -y ppa:damask-multiphysics/ppa

# Step 2: 更新包列表
echo ""
echo "[2/3] Updating package list..."
sudo apt-get update -qq

# Step 3: 安装 DAMASK
echo ""
echo "[3/3] Installing DAMASK..."
sudo apt-get install -y damask

# 验证安装
echo ""
echo "========================================"
echo "  Installation Verification"
echo "========================================"
echo ""

if command -v DAMASK_grid &> /dev/null; then
    echo "✓ DAMASK_grid found at: $(which DAMASK_grid)"
    DAMASK_grid --help 2>&1 | head -5
else
    echo "✗ DAMASK_grid not found in PATH"
    echo "  Try: find /usr -name DAMASK_grid 2>/dev/null"
fi

echo ""
echo "Python package:"
python3 -c "import damask; print(f'  damask {damask.__version__}')" 2>/dev/null || echo "  (Python package check skipped)"

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "To run a simulation:"
echo "  cd /path/to/damask_run/"
echo "  DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml"
echo ""
