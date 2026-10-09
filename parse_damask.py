# -*- coding: utf-8 -*-
"""
解析 DAMASK hdf5: 计算宏观工程应力-应变曲线, 提取
  - 弹性模量 E
  - 0.2% 偏移屈服强度 sigma_y (MPa)
  - 极限抗拉强度 UTS (MPa)
宏观应力 = 各相 P(一阶 P-K 应力) 的体素数加权平均; 单轴拉伸 x 分量 P_11 = 工程应力.
应变: 单轴 dot_F_11=0.001, 每增量 Δt=2s -> 工程应变 ε=0.002*increment_idx.
"""
import h5py
import numpy as np
import json
import sys


def parse(path, verbose=False):
    f = h5py.File(path, 'r')
    incs = sorted([k for k in f.keys() if k.startswith('increment_')],
                  key=lambda x: int(x.split('_')[1]))
    # 单轴拉伸: dot_F_11=0.001, 每增量 Δt=2s -> 工程应变 ε=0.002*increment_idx
    # (已由位移场 u_n 反演拟合确认该映射精确)
    eps, sig = [], []
    for inc in incs:
        idx = int(inc.split('_')[1])
        eps_i = 0.002 * idx
        pf = f[f'{inc}/phase/Ferrite/mechanical/P'][()]
        pm = f[f'{inc}/phase/Martensite/mechanical/P'][()]
        nF, nM = pf.shape[0], pm.shape[0]
        Pavg = (nF * pf.mean(axis=0) + nM * pm.mean(axis=0)) / (nF + nM)
        sig_i = Pavg[0, 0]  # Pa
        eps.append(eps_i)
        sig.append(sig_i)
    f.close()
    eps = np.array(eps)
    sig = np.array(sig) / 1e6  # MPa

    # 弹性模量: 取 ε<0.01 段线性拟合
    m = eps < 0.01
    if m.sum() >= 2:
        E = float(np.polyfit(eps[m], sig[m], 1)[0])
    else:
        E = float(np.polyfit(eps[:3], sig[:3], 1)[0])

    # 0.2% 偏移: σ_off = E*(ε-0.002); 屈服 = 曲线首次从上方穿到下方
    offset = E * (eps - 0.002)
    diff = sig - offset
    iy = None
    for i in range(1, len(diff)):
        if diff[i - 1] >= 0 and diff[i] < 0:
            # 线性插值交点
            x0, x1 = diff[i - 1], diff[i]
            frac = x0 / (x0 - x1)
            iy = i - 1 + frac
            break
    if iy is None:
        # 未屈服 (曲线始终在偏移线之上)
        sigma_y = float(sig[-1])
        iy_idx = len(sig) - 1
    else:
        i0 = int(np.floor(iy))
        i1 = min(i0 + 1, len(sig) - 1)
        frac = iy - i0
        sigma_y = float(sig[i0] * (1 - frac) + sig[i1] * frac)

    UTS = float(sig.max())
    if verbose:
        print(f"  E={E:.1f} MPa  sigma_y(0.2%)={sigma_y:.1f} MPa  UTS={UTS:.1f} MPa")
        print("  (eps, sig):")
        for e, s in zip(eps, sig):
            print(f"    {e:.4f}  {s:8.1f}")
    return {"E_MPa": E, "sigma_y_MPa": sigma_y, "UTS_MPa": UTS,
            "eps": eps.tolist(), "sig_MPa": sig.tolist()}


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "t1.hdf5"
    r = parse(p, verbose=True)
    print(json.dumps({k: v for k, v in r.items() if k not in ('eps', 'sig_MPa')}, indent=2))
