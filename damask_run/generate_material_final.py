#!/usr/bin/env python3
"""
最终版：用damask库生成双相钢模拟所需的material.yaml
- Ferrite: 用 cF 近似 BCC（DAMASK 3.0.2 Fortran 对 cI 的 h_sl-sl 有限制）
- Martensite: 用 cF 近似 BCT
- 使用不同的弹性常数区分两相
"""
import numpy as np
import damask
from scipy.spatial.transform import Rotation

np.random.seed(42)
n_grains = 100
ferrite_vol = 0.72
n_ferrite = int(n_grains * ferrite_vol)

euler = np.zeros((n_grains, 3))
euler[:, 0] = np.random.uniform(0, 2*np.pi, n_grains)
euler[:, 1] = np.arccos(2*np.random.rand(n_grains) - 1)
euler[:, 2] = np.random.uniform(0, 2*np.pi, n_grains)
rot = Rotation.from_euler('zxz', euler)
quats = rot.as_quat()
quats_d = np.column_stack([quats[:, 3], quats[:, 0], quats[:, 1], quats[:, 2]])

phases = ['Ferrite'] * n_ferrite + ['Martensite'] * (n_grains - n_ferrite)

config = {
    "homogenization": {
        "SX": {
            "N_constituents": 1,
            "mechanical": {"type": "pass"},
        }
    },
    "phase": {
        "Ferrite": {
            "lattice": "cF",  # FCC近似BCC（DAMASK Fortran对cI h_sl-sl有限制）
            "mechanical": {
                "elastic": {"type": "Hooke", "C_11": 237.0e9, "C_12": 141.0e9, "C_44": 116.0e9},
                "plastic": {
                    "type": "phenopowerlaw",
                    "N_sl": [12],
                    "a_sl": [2.25],
                    "atol_xi": 1.0,
                    "dot_gamma_0_sl": [0.001],
                    "h_0_sl-sl": [1.0e9],
                    "h_sl-sl": [1, 1, 1.4, 1.4, 1.4, 1.4, 1.4],
                    "n_sl": [20],
                    "xi_0_sl": [95.0e6],
                    "xi_inf_sl": [260.0e6],
                },
            },
        },
        "Martensite": {
            "lattice": "cF",  # FCC近似BCT
            "mechanical": {
                "elastic": {"type": "Hooke", "C_11": 250.0e9, "C_12": 150.0e9, "C_44": 120.0e9},
                "plastic": {
                    "type": "phenopowerlaw",
                    "N_sl": [12],
                    "a_sl": [2.25],
                    "atol_xi": 1.0,
                    "dot_gamma_0_sl": [0.001],
                    "h_0_sl-sl": [2.0e9],
                    "h_sl-sl": [1, 1, 1.4, 1.4, 1.4, 1.4, 1.4],
                    "n_sl": [20],
                    "xi_0_sl": [250.0e6],
                    "xi_inf_sl": [600.0e6],
                },
            },
        },
    },
    "material": [],
}

for i in range(n_grains):
    q = quats_d[i]
    config["material"].append({
        "homogenization": "SX",
        "constituents": [{
            "phase": phases[i],
            "v": 1.0,
            "O": [float(q[0]), float(q[1]), float(q[2]), float(q[3])],
        }],
    })

c = damask.ConfigMaterial(config)
output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "material.yaml")
c.save(output)
print(f"Saved to {output}")
print(f"Phases: {list(c['phase'].keys())}")
print(f"Materials: {len(c['material'])}")

# 验证
c2 = damask.ConfigMaterial.load(output)
print("Validation: OK")
