# -*- coding: utf-8 -*-
"""
DAMASK结果后处理
从HDF5文件中提取应力-应变曲线用于论文
"""
import h5py
import numpy as np
import json
import os
import sys

def extract_stress_strain(hdf5_path: str) -> dict:
    """从DAMASK HDF5结果中提取宏观应力-应变数据"""
    
    with h5py.File(hdf5_path, 'r') as f:
        # 检查可用的数据集
        print(f"Available groups in HDF5: {list(f.keys())}")
        
        results = {}
        
        # 尝试多种可能的路径获取数据
        # DAMASK 3.0 结构: /homogenization/SX/
        
        # 获取增量步信息
        if 'increments' in f:
            incs = f['increments']
            n_incs = len(incs)
            print(f"Number of increments: {n_incs}")
        else:
            print("WARNING: No 'increments' group found")
            print("Available top-level keys:", list(f.keys()))
            # 尝试遍历所有顶层组
            for key in f.keys():
                item = f[key]
                if hasattr(item, 'keys'):
                    print(f"  {key}: {list(item.keys())}")
        
        # 尝试提取变形梯度 F 和第一Piola-Kirchhoff应力 P
        try:
            # 路径取决于DAMASK版本和homogenization scheme
            # 常见路径:
            possible_F_paths = [
                'homogenization/SX/F',
                'homogenization/1/F',
                'cell_data/homogenization/F',
            ]
            
            F_data = None
            P_data = None
            
            for path in possible_F_paths:
                if path in f:
                    print(f"Found F at: {path}")
                    F_data = f[path][:]
                    break
            
            if F_data is None:
                # 尝试搜索
                print("Searching for F and P datasets...")
                def search_h5(name, obj):
                    if 'F' in name and hasattr(obj, 'shape'):
                        print(f"  Found: {name}, shape={obj.shape}")
                
                f.visititems(search_h5)
            
        except Exception as e:
            print(f"Error extracting data: {e}")
    
    return results


def extract_from_increments(hdf5_path: str) -> dict:
    """
    备用方法: 从increments结构提取数据
    DAMASK 3.0 可能把数据存在 /increments/<step>/... 下
    """
    import h5py
    import numpy as np
    
    with h5py.File(hdf5_path, 'r') as f:
        print("\n=== HDF5 Structure ===")
        f.visit(print)
        
        print("\n=== Top-level groups ===")
        for key in f.keys():
            print(f"  {key}: {type(f[key])}")
        
    return {}


if __name__ == "__main__":
    # 检查结果文件
    result_dirs = ["results_uniaxial", "results_planestrain"]
    
    for d in result_dirs:
        if not os.path.isdir(d):
            continue
        h5_files = [f for f in os.listdir(d) if f.endswith('.hdf5') or f.endswith('.h5')]
        print(f"\n=== {d} ===")
        print(f"  HDF5 files: {h5_files}")
        
        for hf in h5_files:
            path = os.path.join(d, hf)
            print(f"\n  Processing: {path}")
            extract_from_increments(path)
    
    print("\nPost-processing complete.")
