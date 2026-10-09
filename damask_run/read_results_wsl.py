# -*- coding: utf-8 -*-
"""
读取DAMASK HDF5结果的脚本 - 在WSL中运行
用法: wsl python3 read_results_wsl.py
"""
import h5py
import numpy as np
import os

def read_damask_hdf5(filepath):
    """详细读取DAMASK HDF5结果"""
    print(f"\n{'='*60}")
    print(f"File: {filepath}")
    print(f"{'='*60}")
    
    with h5py.File(filepath, 'r') as f:
        # 列出所有顶层组
        print("\nTop-level groups:")
        for k in f.keys():
            print(f"  {k}")
        
        # 检查每个increment的homogenization数据
        incs = [k for k in f.keys() if k.startswith('increment_')]
        incs.sort(key=lambda x: int(x.split('_')[1]))
        
        print(f"\nFound {len(incs)} increments")
        
        for inc_name in incs[:2] + incs[-2:]:  # 只看前2和后2
            inc = f[inc_name]
            print(f"\n--- {inc_name} ---")
            
            # 递归检查
            def explore(grp, prefix=""):
                if hasattr(grp, 'keys'):
                    subkeys = list(grp.keys())
                    if subkeys:
                        for k in subkeys:
                            explore(grp[k], f"{prefix}/{k}")
                    else:
                        if prefix:
                            print(f"  {prefix}: (empty)")
                else:
                    arr = grp[()]
                    shape = arr.shape if hasattr(arr, 'shape') else 'scalar'
                    print(f"  {prefix}: shape={shape}, dtype={grp.dtype}")
            
            explore(inc, inc_name)
        
        # 检查setup
        print("\n--- setup ---")
        setup = f['setup']
        for k in setup.keys():
            val = setup[k][()]
            if isinstance(val, bytes):
                val = val.decode()
            print(f"  {k}: {val}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    
    # 两个结果文件
    files = [
        f"{base}/results_uniaxial/rve_load_uniaxial_tension_material.hdf5",
        f"{base}/results_planestrain/rve_load_plane_strain_tension_material.hdf5",
    ]
    
    for fpath in files:
        if os.path.exists(fpath):
            read_damask_hdf5(fpath)
        else:
            print(f"File not found: {fpath}")
