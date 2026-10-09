# -*- coding: utf-8 -*-
"""
HPD-RVE 因子设计几何生成器 (FULL FACTORIAL: vm x dm/df)
========================================================
为 Rev2#13 的"解耦因子设计"生成真实 3D RVE 几何:
  - 相体积分数 vm 精确控制 (相场阈值 + 边界翻转修正到单个体素)
  - 晶粒尺寸比 dm/df 独立控制 (铁素体/马氏体各自内部 Voronoi 分晶粒,
     各自晶粒数由目标 dm/df 反解)

输出用 damask 自家 GeomGrid/ConfigMaterial 写入器, 保证与 DAMASK_grid 兼容。

用法:
  python factorial_rve_gen.py --vm 0.28 --dm_df 1.0 --seed 1 --N 32 --out ./g
  python factorial_rve_gen.py --grid  # 生成 4x4 全因子到 ./factorial_geoms/
"""
import argparse
import os
import json
import numpy as np
import damask
from scipy.ndimage import gaussian_filter


# ---- 相定义 (从已验证 material.yaml 复刻, 仅改几何, 材料参数固定) ----
SX = {"N_constituents": 1, "mechanical": {"type": "pass"}}

FERRITE = {
    "lattice": "cF",
    "mechanical": {
        "output": ["F", "P", "F_e", "F_p", "L_p"],
        "elastic": {"type": "Hooke", "C_11": 237e9, "C_12": 141e9, "C_44": 116e9},
        "plastic": {
            "type": "phenopowerlaw", "output": ["xi_sl"], "N_sl": [12], "a_sl": [2.25],
            "atol_xi": 1.0, "dot_gamma_0_sl": [0.001], "h_0_sl-sl": [1e9],
            "h_sl-sl": [1, 1, 1.4, 1.4, 1.4, 1.4, 1.4], "n_sl": [20],
            "xi_0_sl": [95e6], "xi_inf_sl": [260e6],
        },
    },
}

MARTENSITE = {
    "lattice": "cF",
    "mechanical": {
        "output": ["F", "P", "F_e", "F_p", "L_p"],
        "elastic": {"type": "Hooke", "C_11": 250e9, "C_12": 150e9, "C_44": 120e9},
        "plastic": {
            "type": "phenopowerlaw", "output": ["xi_sl"], "N_sl": [12], "a_sl": [2.25],
            "atol_xi": 1.0, "dot_gamma_0_sl": [0.001], "h_0_sl-sl": [2e9],
            "h_sl-sl": [1, 1, 1.4, 1.4, 1.4, 1.4, 1.4], "n_sl": [20],
            "xi_0_sl": [250e6], "xi_inf_sl": [600e6],
        },
    },
}


def random_quat(rng):
    """均匀随机单位四元数 [q0,q1,q2,q3] (w,x,y,z)"""
    u1, u2, u3 = rng.random(3)
    q0 = np.sqrt(1 - u1) * np.sin(2 * np.pi * u2)
    q1 = np.sqrt(1 - u1) * np.cos(2 * np.pi * u2)
    q2 = np.sqrt(u1) * np.sin(2 * np.pi * u3)
    q3 = np.sqrt(u1) * np.cos(2 * np.pi * u3)
    return [float(q0), float(q1), float(q2), float(q3)]


def build_phase_field(N, vm, rng, sigma=2.5):
    """平滑噪声阈值得到块状马氏体相场, 再翻转边界体素到精确 vm."""
    noise = rng.standard_normal((N, N, N))
    smooth = gaussian_filter(noise, sigma=sigma)
    thr = np.percentile(smooth, 100 * (1 - vm))  # 高值为马氏体, 占 vm
    mart = (smooth >= thr).astype(np.int8)
    target = int(round(vm * N * N * N))
    cur = int(mart.sum())
    order = np.argsort(np.abs(smooth - thr)).ravel()
    flat = mart.ravel()
    if cur < target:
        cand = order[flat[order] == 0][: target - cur]
        flat[cand] = 1
    elif cur > target:
        cand = order[flat[order] == 1][: cur - target]
        flat[cand] = 0
    return flat.reshape(N, N, N)


def voronoi_in_mask(mask, n_seeds, rng):
    """在 mask 区域内放 n_seeds 个种子, 对区域内体素做 Voronoi 分配.
    返回与 mask 同形局部晶粒号 (0 起, 仅 mask 内有效)."""
    pts = np.argwhere(mask)
    if len(pts) == 0 or n_seeds <= 0:
        return np.full(mask.shape, -1, dtype=np.int32)
    sel = rng.choice(len(pts), size=min(n_seeds, len(pts)), replace=False)
    seeds = pts[sel].astype(float)
    coords = pts.astype(float)
    grain = np.full(len(pts), -1, dtype=np.int32)
    B = 8192
    for s in range(0, len(pts), B):
        e = min(s + B, len(pts))
        d = np.sum((coords[s:e, None, :] - seeds[None, :, :]) ** 2, axis=2)
        grain[s:e] = np.argmin(d, axis=1)
    out = np.full(mask.shape, -1, dtype=np.int32)
    out[pts[:, 0], pts[:, 1], pts[:, 2]] = grain
    return out


def gen_geometry(vm, dm_df, seed, N=32, G=70, outdir="."):
    rng = np.random.default_rng(seed)
    os.makedirs(outdir, exist_ok=True)
    # 反解晶粒数: dm/df = ((vm/n_m)/((1-vm)/n_f))^(1/3)
    r = (dm_df ** 3) * (1 - vm) / vm
    n_m = max(2, int(round(G / (1 + r))))
    n_f = G - n_m
    # 1) 相场 (精确 vm)
    mart = build_phase_field(N, vm, rng)  # 1=马氏体
    ferrite_mask = mart == 0
    mart_mask = mart == 1
    # 2) 各相内部 Voronoi 分晶粒
    g_m = voronoi_in_mask(mart_mask, n_m, rng)
    g_f = voronoi_in_mask(ferrite_mask, n_f, rng)
    # 3) 合并全局 material id: 马氏体 0..n_m-1, 铁素体 n_m..G-1
    material = np.full((N, N, N), -1, dtype=np.int32)
    material[mart_mask] = g_m[mart_mask]
    material[ferrite_mask] = g_f[ferrite_mask] + n_m
    # 4) damask 自家 VTI
    geo = damask.GeomGrid(material, size=[float(N)] * 3, origin=[-N / 2.0] * 3)
    vti_path = os.path.join(outdir, "geometry.vti")
    geo.save(vti_path, compress=False)
    # 5) material.yaml (ConfigMaterial)
    mats = []
    for i in range(n_m):
        q = random_quat(rng)
        mats.append({"homogenization": "SX",
                     "constituents": [{"phase": "Martensite", "v": 1.0, "O": q}]})
    for i in range(n_f):
        q = random_quat(rng)
        mats.append({"homogenization": "SX",
                     "constituents": [{"phase": "Ferrite", "v": 1.0, "O": q}]})
    cfg = {
        "homogenization": {"SX": SX},
        "phase": {"Ferrite": FERRITE, "Martensite": MARTENSITE},
        "material": mats,
    }
    cm = damask.ConfigMaterial(cfg)
    yaml_path = os.path.join(outdir, "material.yaml")
    cm.save(yaml_path)
    # 6) meta
    actual_vm = float(mart_mask.sum()) / (N ** 3)
    actual_dm = ((actual_vm / n_m) / ((1 - actual_vm) / n_f)) ** (1 / 3)
    meta = {"vm_target": vm, "vm_actual": actual_vm,
            "dm_df_target": dm_df, "dm_df_actual": actual_dm,
            "n_martensite_grains": n_m, "n_ferrite_grains": n_f,
            "N": N, "seed": seed, "n_voxels": int(N ** 3)}
    with open(os.path.join(outdir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[gen] vm={vm} dm/df={dm_df} seed={seed}: actual vm={actual_vm:.3f} "
          f"dm/df={actual_dm:.3f} n_m={n_m} n_f={n_f} -> {vti_path}")
    return vti_path, yaml_path, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vm", type=float, default=0.28)
    ap.add_argument("--dm_df", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--N", type=int, default=32)
    ap.add_argument("--G", type=int, default=70)
    ap.add_argument("--out", type=str, default="./g")
    ap.add_argument("--grid", action="store_true",
                    help="生成 4x4 全因子 (vm x dm/df) 到 ./factorial_geoms/")
    a = ap.parse_args()
    if a.grid:
        vms = [0.20, 0.30, 0.40, 0.50]
        dfs = [0.3, 0.5, 0.7, 1.0]
        base = "./factorial_geoms"
        for vm in vms:
            for df in dfs:
                od = os.path.join(base, f"vm{vm:.2f}_df{df:.2f}")
                gen_geometry(vm, df, seed=1, N=a.N, G=a.G, outdir=od)
    else:
        gen_geometry(a.vm, a.dm_df, seed=a.seed, N=a.N, G=a.G, outdir=a.out)


if __name__ == "__main__":
    main()
