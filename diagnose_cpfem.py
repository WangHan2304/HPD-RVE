"""快速诊断: 检查PhysicsBasedCPFEM在不同v_m下的原始和校准输出"""
from parametric_cpfem import PhysicsBasedCPFEM
import numpy as np

solver = PhysicsBasedCPFEM()

print("="*70)
print("DIAGNOSTIC: Raw vs Calibrated stress at different v_m")
print("="*70)

for v_m in [0.15, 0.25, 0.35, 0.45, 0.55]:
    # 不校准
    r_raw = solver.compute_stress_strain(
        v_m=v_m, d_f_um=15.0, d_m_um=7.5,
        max_strain=0.10, n_steps=50, seed=42,
        enable_calibration=False
    )
    # 校准
    r_cal = solver.compute_stress_strain(
        v_m=v_m, d_f_um=15.0, d_m_um=7.5,
        max_strain=0.10, n_steps=50, seed=42,
        enable_calibration=True
    )
    
    print(f"\nv_m={v_m:.2f}:")
    print(f"  RAW:   yield={r_raw['yield_stress_MPa']:.1f}, UTS={r_raw['uts_MPa']:.1f}, "
          f"MF_ratio={r_raw['mf_stress_ratio']}")
    print(f"  CAL:   yield={r_cal['yield_stress_MPa']:.1f}, UTS={r_cal['uts_MPa']:.1f}, "
          f"MF_ratio={r_cal['mf_stress_ratio']}")
    print(f"  f_tau0={r_raw['f_params_tau0']:.1f}, m_tau0={r_raw['m_params_tau0']:.1f}")

# 检查混合法则是否在物理上起作用
print("\n" + "="*70)
print("MIXING RULE CHECK:")
print("="*70)
# 纯铁素体 (v_m=0)
r_f = solver.compute_stress_strain(v_m=0.0, d_f_um=15.0, d_m_um=7.5, 
                                     max_strain=0.10, n_steps=50, seed=42,
                                     enable_calibration=False)
# 纯马氏体 (v_m=1.0)  
r_m = solver.compute_stress_strain(v_m=0.999, d_f_um=15.0, d_m_um=7.5,
                                     max_strain=0.10, n_steps=50, seed=42,
                                     enable_calibration=False)

print(f"Pure ferrite: yield={r_f['yield_stress_MPa']:.1f}, UTS={r_f['uts_MPa']:.1f}")
print(f"Pure martensite: yield={r_m['yield_stress_MPa']:.1f}, UTS={r_m['uts_MPa']:.1f}")

# 理论混合法则预测 v_m=0.28
vf, vm = 0.72, 0.28
pred_yield = vf * r_f['yield_stress_MPa'] + vm * r_m['yield_stress_MPa']
pred_uts = vf * r_f['uts_MPa'] + vm * r_m['uts_MPa']
print(f"\nPredicted (v_m=0.28): yield={pred_yield:.1f}, UTS={pred_uts:.1f}")
print(f"DP800 reference:      yield=340.0, UTS=800.0")
