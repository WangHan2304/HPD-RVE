"""
物理参数化CPFEM求解器 - 用于微观结构-性能定量映射

与原始TaylorCrystalPlasticitySolver的区别:
1. 不进行两点校准到固定实验数据
2. 使用混合法则直接反映体积分数的影响
3. 通过晶粒尺寸修正反映Hall-Petch效应
4. 保留取向采样的随机性作为统计不确定性

物理基础:
- 混合法则: σ_macro = v_f * σ_f + v_m * σ_m
- Hall-Petch: τ_0(d) = τ_0_ref + k_HP / sqrt(d)
- 晶粒尺寸通过滑移阻力影响屈服强度
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MaterialParams:
    """材料参数"""
    C11: float   # GPa
    C12: float
    C44: float
    tau_0: float  # 初始CRSS (MPa)
    tau_sat: float  # 饱和CRSS (MPa)
    h_0: float   # 初始硬化模量 (MPa)
    a: float     # 硬化指数
    n_slip: int  # 滑移系数量
    hall_petch_k: float  # Hall-Petch系数 (MPa·µm^0.5)


# ============================================================
# 材料参数库 (物理校准)
# ============================================================
# 铁素体 (BCC) - 参考晶粒尺寸 d_0 = 15 µm
FERRITE_PARAMS = MaterialParams(
    C11=237.0, C12=141.0, C44=116.0,
    tau_0=95.0, tau_sat=260.0, h_0=1000.0, a=2.25,
    n_slip=12, hall_petch_k=18.0  # MPa·µm^0.5 (典型BCC)
)

# 马氏体 (BCT) - 参考晶粒尺寸 d_0 = 3 µm
MARTENSITE_PARAMS = MaterialParams(
    C11=250.0, C12=150.0, C44=120.0,
    tau_0=250.0, tau_sat=600.0, h_0=2000.0, a=2.25,
    n_slip=12, hall_petch_k=25.0  # MPa·µm^0.5 (典型BCT/马氏体)
)

# DP800 参考参数 (用于对标)
DP800_REF = {
    "yield_stress_MPa": 340.0,  # Tasan et al. 2014
    "uts_MPa": 800.0,
    "vf_ferrite": 0.72,
    "vf_martensite": 0.28,
    "d_ferrite_um": 15.0,
    "d_martensite_um": 3.0,
}


# ============================================================
# BCC/BCT滑移系定义
# ============================================================
def get_bcc_slip_systems() -> List[Dict]:
    """BCC {110}<111> 滑移系 (12个)"""
    planes = [(1,1,0), (-1,1,0), (1,-1,0), (0,1,1), (0,-1,1), (0,1,-1),
              (1,0,1), (-1,0,1), (1,0,-1), (1,1,0), (-1,1,0), (1,-1,0)]
    directions = [(-1,1,1), (1,-1,1), (1,1,-1), (-1,1,1), (1,-1,1), (1,1,-1),
                  (1,1,-1), (1,-1,1), (-1,1,1), (1,1,1), (1,1,1), (1,1,1)]
    return [{"plane": list(p), "direction": list(d)} for p, d in zip(planes, directions)]


def get_bct_slip_systems() -> List[Dict]:
    """BCT {110}<111> + {112}<111> 滑移系 (24个)"""
    # 简化: 使用与BCC相同的12个主要滑移系
    return get_bcc_slip_systems()


# ============================================================
# 物理CPFEM核心
# ============================================================
class PhysicsBasedCPFEM:
    """基于物理的CPFEM求解器 - 无校准，直接输出物理预测"""
    
    def __init__(self):
        self.bcc_slips = get_bcc_slip_systems()
        self.bct_slips = get_bct_slip_systems()
    
    def _apply_hall_petch(self, params: MaterialParams, 
                          grain_size_um: float) -> MaterialParams:
        """Hall-Petch晶粒尺寸修正: τ_0(d) = τ_0(d_ref) + k_HP * (1/√d - 1/√d_ref)"""
        from copy import copy
        p = copy(params)
        d_ref = 15.0 if params == FERRITE_PARAMS else 3.0
        
        correction = params.hall_petch_k * (1.0/np.sqrt(grain_size_um) - 1.0/np.sqrt(d_ref))
        p.tau_0 = params.tau_0 + correction
        # 饱和值也相应缩放
        p.tau_sat = params.tau_sat + correction * 1.5  # 饱和值对尺寸敏感性较低
        return p
    
    def _compute_crystal_stress(self, F: np.ndarray, params: MaterialParams,
                                 euler_angles: Tuple[float, float, float]) -> float:
        """计算单晶Cauchy应力 (简化Taylor模型)"""
        phi1, Phi, phi2 = euler_angles
        
        # 旋转矩阵
        c1, s1 = np.cos(phi1), np.sin(phi1)
        c, s = np.cos(Phi), np.sin(Phi)
        c2, s2 = np.cos(phi2), np.sin(phi2)
        
        R = np.array([
            [c1*c2 - s1*s2*c, -c1*s2 - s1*c2*c, s1*s],
            [s1*c2 + c1*s2*c, -s1*s2 + c1*c2*c, -c1*s],
            [s2*s, c2*s, c]
        ])
        
        # 无穷小应变
        eps = 0.5 * (F + F.T) - np.eye(3)
        eps_xx = eps[0, 0]
        eps_vol = eps[0,0] + eps[1,1] + eps[2,2]
        
        # 弹性应力 (MPa)
        C11, C12, C44 = params.C11, params.C12, params.C44
        sigma = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                if i == j:
                    sigma[i, j] = C12 * eps_vol + (C11 - C12) * eps[i, i]
                else:
                    sigma[i, j] = 2.0 * C44 * eps[i, j]
        sigma *= 1000.0  # GPa -> MPa
        
        # Taylor因子计算
        slips = self.bcc_slips if params.n_slip == 12 else self.bct_slips
        total_schmid = 0.0
        for slip in slips:
            n = np.array(slip["plane"], dtype=float)
            d = np.array(slip["direction"], dtype=float)
            n = n / np.linalg.norm(n)
            d = d / np.linalg.norm(d)
            
            # Schmid张量 P = 0.5 * (d⊗n + n⊗d)
            P = 0.5 * (np.outer(d, n) + np.outer(n, d))
            # 旋转到晶体坐标
            P_crystal = R.T @ P @ R
            # 分切应力
            tau = np.sum(P_crystal * sigma)
            total_schmid += abs(tau)
        
        avg_schmid = total_schmid / len(slips) if slips else 0.3
        taylor_factor = 1.0 / max(avg_schmid / max(abs(sigma[0,0]), 1.0), 0.1)
        
        # 流动应力 (Voce硬化)
        E = C11 * 1000.0
        eps_elastic_yield = (taylor_factor * params.tau_0) / E
        eps_plastic = max(0.0, abs(eps_xx) - eps_elastic_yield)
        
        flow_stress = taylor_factor * params.tau_0
        if eps_plastic > 0 and params.tau_sat > params.tau_0:
            delta = params.tau_sat - params.tau_0
            hardening = delta * (1.0 - np.exp(-params.h_0 * eps_plastic / max(delta, 1.0)))
            flow_stress += taylor_factor * hardening
        
        # Ramberg-Osgood光滑过渡
        alpha_ro = 0.002
        n_ro = 8.0
        
        def ro_residual(s):
            if s <= 0:
                return -abs(eps_xx)
            elastic = s / E
            plastic = alpha_ro * (s / flow_stress) ** n_ro
            return elastic + plastic - abs(eps_xx)
        
        # 二分法
        lo, hi = 0.0, max(flow_stress * 3.0, abs(sigma[0,0]) * 2.0)
        for _ in range(50):
            mid = (lo + hi) / 2.0
            if ro_residual(mid) > 0:
                hi = mid
            else:
                lo = mid
        
        return (lo + hi) / 2.0
    
    def compute_stress_strain(self,
                              v_m: float,           # 马氏体体积分数
                              d_f_um: float = 15.0, # 铁素体晶粒尺寸 (µm)
                              d_m_um: float = 3.0,  # 马氏体晶粒尺寸 (µm)
                              n_ferrite_grains: int = 30,
                              n_martensite_grains: int = 20,
                              max_strain: float = 0.10,
                              n_steps: int = 50,
                              loading_mode: str = "uniaxial_tension",
                              seed: int = 42,
                              enable_calibration: bool = False) -> Dict:
        """
        物理参数化CPFEM计算
        
        Args:
            v_m: 马氏体体积分数
            d_f_um: 铁素体平均晶粒尺寸
            d_m_um: 马氏体平均晶粒尺寸
            enable_calibration: 是否用DP800参考数据校准 (默认False，直接物理预测)
        """
        np.random.seed(seed)
        
        # Hall-Petch修正材料参数
        f_params = self._apply_hall_petch(FERRITE_PARAMS, d_f_um)
        m_params = self._apply_hall_petch(MARTENSITE_PARAMS, d_m_um)
        
        v_f = 1.0 - v_m
        is_compression = (loading_mode == "uniaxial_compression")
        
        # 生成随机取向
        n_f_sample = min(n_ferrite_grains, 30)
        n_m_sample = min(n_martensite_grains, 20) if v_m > 0 else 0
        
        f_orient = [(np.random.uniform(0, 2*np.pi), np.random.uniform(0, np.pi),
                     np.random.uniform(0, 2*np.pi)) for _ in range(n_f_sample)]
        m_orient = [(np.random.uniform(0, 2*np.pi), np.random.uniform(0, np.pi),
                     np.random.uniform(0, 2*np.pi)) for _ in range(max(n_m_sample, 1))]
        
        strains = np.linspace(0, max_strain, n_steps + 1)[1:]
        
        stress_macro = []
        stress_ferrite = []
        stress_martensite = []
        
        for eps_xx in strains:
            nu = 0.3
            if is_compression:
                abs_eps = abs(eps_xx)
                F = np.diag([1.0 - abs_eps, 1.0 + nu*abs_eps, 1.0 + nu*abs_eps])
            else:
                F = np.diag([1.0 + eps_xx, 1.0 - nu*eps_xx, 1.0 - nu*eps_xx])
            
            # 铁素体相平均
            sf_vals = [self._compute_crystal_stress(F, f_params, o) for o in f_orient]
            sf_avg = np.mean(sf_vals)
            
            if v_m > 0:
                sm_vals = [self._compute_crystal_stress(F, m_params, o) for o in m_orient]
                sm_avg = np.mean(sm_vals)
            else:
                sm_avg = 0.0
            
            # 混合法则
            smacro = v_f * sf_avg + v_m * sm_avg
            
            stress_macro.append(float(smacro))
            stress_ferrite.append(float(sf_avg))
            stress_martensite.append(float(sm_avg))
        
        # 可选：DP800参考数据校准 (保持硬化形状，缩放幅度)
        if enable_calibration and v_m > 0.01:
            # 用DP800参考点校准
            ref_yield = DP800_REF["yield_stress_MPa"]
            ref_uts = DP800_REF["uts_MPa"]
            
            strains_arr = np.array(strains)
            idx_yield = np.argmin(np.abs(strains_arr - 0.002))
            idx_uts = np.argmin(np.abs(strains_arr - 0.10))
            
            raw_yield = abs(stress_macro[idx_yield])
            raw_uts = abs(stress_macro[idx_uts])
            
            if raw_yield > 0 and raw_uts > raw_yield:
                # 保持硬化形状，线性缩放
                scale_yield = ref_yield / raw_yield
                scale_uts = ref_uts / raw_uts
                
                # 使用插值缩放因子 (在小应变处使用yield scale，大应变处使用uts scale)
                for i, s in enumerate(strains_arr):
                    if s < 0.01:
                        t = s / 0.01
                        scale = scale_yield + t * (scale_uts - scale_yield)
                    else:
                        scale = scale_uts
                    stress_macro[i] = float(stress_macro[i] * scale)
                    stress_ferrite[i] = float(stress_ferrite[i] * scale)
                    if v_m > 0:
                        stress_martensite[i] = float(stress_martensite[i] * scale)
        
        # 提取关键力学量
        strains_arr = np.array(strains)
        stress_arr = np.array(stress_macro)
        
        idx_02 = np.argmin(np.abs(strains_arr - 0.002))
        idx_10 = np.argmin(np.abs(strains_arr - 0.10))
        idx_05 = np.argmin(np.abs(strains_arr - 0.05))
        
        yield_stress = float(stress_arr[idx_02])
        uts = float(np.max(stress_arr))
        hardening_rate = float((stress_arr[idx_10] - stress_arr[idx_05]) / 0.05)
        
        mf_ratio = None
        if v_m > 0 and abs(stress_ferrite[idx_10]) > 1:
            mf_ratio = float(abs(stress_martensite[idx_10]) / abs(stress_ferrite[idx_10]))
        
        return {
            "v_m": v_m,
            "v_f": v_f,
            "d_f_um": d_f_um,
            "d_m_um": d_m_um,
            "d_ratio": d_m_um / d_f_um if d_f_um > 0 else None,
            "seed": seed,
            "yield_stress_MPa": round(yield_stress, 1),
            "uts_MPa": round(uts, 1),
            "hardening_rate_MPa": round(hardening_rate, 1),
            "mf_stress_ratio": round(mf_ratio, 3) if mf_ratio else None,
            "flow_stress_5pct": round(float(stress_arr[idx_05]), 1),
            "flow_stress_10pct": round(float(stress_arr[idx_10]), 1),
            "strains": strains.tolist(),
            "stress_macro": [float(s) for s in stress_macro],
            "stress_ferrite": [float(s) for s in stress_ferrite],
            "stress_martensite": [float(s) for s in stress_martensite],
            "f_params_tau0": f_params.tau_0,
            "m_params_tau0": m_params.tau_0,
        }
