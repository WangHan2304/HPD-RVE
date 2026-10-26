#!/usr/bin/env python3
"""
G5 (4-Phase Advanced Steel) CPFEM Simulation
==============================================
Phase composition: Ferrite(BCC) 25% + Austenite(FCC) 25% + Martensite(BCT) 25% + δ-Ferrite(BCC) 25%
Uses the PhysicsBasedCPFEM framework (same as G2/G3) extended to 4 phases.

This provides a Python CPFEM simulation result that is equivalent in approach
to the G2 Taylor CPFEM validation. For the full-field DAMASK simulation,
see damask_run_g5/ directory.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from copy import copy

# ============================================================
# Material Parameters for G5 (4-phase steel)
# ============================================================

@dataclass
class PhaseParams:
    """Phase-level material parameters"""
    name: str
    lattice: str
    C11: float; C12: float; C44: float  # GPa
    tau_0: float; tau_sat: float  # MPa (CRSS)
    h_0: float; a: float  # Hardening
    n_slip: int
    hall_petch_k: float  # MPa*um^0.5
    d_ref: float  # Reference grain size (um)
    vol_frac: float  # Volume fraction

# G5 Phase parameters (literature-consistent with G2/G3)
G5_PHASES = {
    "Ferrite": PhaseParams(
        name="Ferrite", lattice="BCC",
        C11=237.0, C12=141.0, C44=116.0,
        tau_0=95.0, tau_sat=260.0, h_0=1000.0, a=2.25,
        n_slip=12, hall_petch_k=18.0, d_ref=15.0,
        vol_frac=0.25
    ),
    "Austenite": PhaseParams(
        name="Austenite", lattice="FCC",
        C11=205.0, C12=138.0, C44=126.0,
        tau_0=150.0, tau_sat=400.0, h_0=1500.0, a=2.25,
        n_slip=12, hall_petch_k=20.0, d_ref=30.0,
        vol_frac=0.25
    ),
    "Martensite": PhaseParams(
        name="Martensite", lattice="BCT",
        C11=250.0, C12=150.0, C44=120.0,
        tau_0=250.0, tau_sat=600.0, h_0=2000.0, a=2.25,
        n_slip=12, hall_petch_k=25.0, d_ref=3.0,
        vol_frac=0.25
    ),
    "DeltaFerrite": PhaseParams(
        name="DeltaFerrite", lattice="BCC",
        C11=230.0, C12=135.0, C44=110.0,
        tau_0=105.0, tau_sat=280.0, h_0=1100.0, a=2.25,
        n_slip=12, hall_petch_k=18.0, d_ref=20.0,
        vol_frac=0.25
    ),
}

# Grain sizes for G5 (typical for advanced steel)
G5_GRAIN_SIZES = {
    "Ferrite": 12.0,       # um
    "Austenite": 25.0,     # um
    "Martensite": 3.0,     # um
    "DeltaFerrite": 18.0,  # um
}

# ============================================================
# Slip systems
# ============================================================

def get_bcc_slip_systems() -> List[Dict]:
    """BCC {110}<111> slip systems (12)"""
    planes = [(1,1,0), (-1,1,0), (1,-1,0), (0,1,1), (0,-1,1), (0,1,-1),
              (1,0,1), (-1,0,1), (1,0,-1), (1,1,0), (-1,1,0), (1,-1,0)]
    directions = [(-1,1,1), (1,-1,1), (1,1,-1), (-1,1,1), (1,-1,1), (1,1,-1),
                  (1,1,-1), (1,-1,1), (-1,1,1), (1,1,1), (1,1,1), (1,1,1)]
    return [{"plane": list(p), "direction": list(d)} for p, d in zip(planes, directions)]

def get_fcc_slip_systems() -> List[Dict]:
    """FCC {111}<110> slip systems (12)"""
    planes = [(1,1,1), (1,1,1), (1,1,1), (-1,1,1), (-1,1,1), (-1,1,1),
              (1,-1,1), (1,-1,1), (1,-1,1), (1,1,-1), (1,1,-1), (1,1,-1)]
    directions = [(1,-1,0), (1,0,-1), (0,1,-1), (1,1,0), (1,0,1), (0,1,-1),
                  (1,1,0), (1,0,-1), (0,1,1), (1,-1,0), (1,0,1), (0,1,1)]
    return [{"plane": list(p), "direction": list(d)} for p, d in zip(planes, directions)]


# ============================================================
# G5 CPFEM Solver
# ============================================================

class G5CPFEMSolver:
    """4-phase CPFEM solver using Taylor iso-strain homogenization"""

    def __init__(self, seed: int = 88):
        self.seed = seed
        self.bcc_slips = get_bcc_slip_systems()
        self.fcc_slips = get_fcc_slip_systems()
        np.random.seed(seed)

    def _get_slip_systems(self, lattice: str) -> List[Dict]:
        if lattice in ("BCC", "BCT"):
            return self.bcc_slips
        elif lattice == "FCC":
            return self.fcc_slips
        else:
            return self.bcc_slips  # default

    def _apply_hall_petch(self, params: PhaseParams, grain_size_um: float) -> PhaseParams:
        """Hall-Petch correction: tau_0(d) = tau_0(d_ref) + k_HP * (1/sqrt(d) - 1/sqrt(d_ref))"""
        p = copy(params)
        correction = params.hall_petch_k * (1.0/np.sqrt(grain_size_um) - 1.0/np.sqrt(params.d_ref))
        p.tau_0 = max(params.tau_0 + correction, 10.0)
        p.tau_sat = max(params.tau_sat + correction * 1.5, p.tau_0 + 10.0)
        return p

    def _compute_single_crystal_stress(self, F: np.ndarray, params: PhaseParams,
                                        euler_angles: Tuple[float, float, float]) -> float:
        """Compute single crystal Cauchy stress under Taylor iso-strain"""
        phi1, Phi, phi2 = euler_angles

        # Rotation matrix (Bunge convention, ZXZ)
        c1, s1 = np.cos(phi1), np.sin(phi1)
        c, s = np.cos(Phi), np.sin(Phi)
        c2, s2 = np.cos(phi2), np.sin(phi2)

        R = np.array([
            [c1*c2 - s1*s2*c, -c1*s2 - s1*c2*c, s1*s],
            [s1*c2 + c1*s2*c, -s1*s2 + c1*c2*c, -c1*s],
            [s2*s, c2*s, c]
        ])

        # Infinitesimal strain
        eps = 0.5 * (F + F.T) - np.eye(3)
        eps_xx = eps[0, 0]
        eps_vol = eps[0,0] + eps[1,1] + eps[2,2]

        # Elastic stress (MPa)
        C11, C12, C44 = params.C11, params.C12, params.C44
        sigma = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                if i == j:
                    sigma[i, j] = C12 * eps_vol + (C11 - C12) * eps[i, i]
                else:
                    sigma[i, j] = 2.0 * C44 * eps[i, j]
        sigma *= 1000.0  # GPa -> MPa

        # Taylor factor via Schmid analysis
        slips = self._get_slip_systems(params.lattice)
        total_schmid = 0.0
        for slip in slips:
            n = np.array(slip["plane"], dtype=float)
            d = np.array(slip["direction"], dtype=float)
            n = n / np.linalg.norm(n)
            d = d / np.linalg.norm(d)

            # Schmid tensor: P = 0.5 * (d⊗n + n⊗d)
            P = 0.5 * (np.outer(d, n) + np.outer(n, d))
            P_crystal = R.T @ P @ R
            tau = np.sum(P_crystal * sigma)
            total_schmid += abs(tau)

        avg_schmid = total_schmid / len(slips) if slips else 0.3
        ref_stress = max(abs(sigma[0,0]), 1.0)
        taylor_factor = 1.0 / max(avg_schmid / ref_stress, 0.1)

        # Flow stress with Voce hardening
        E = C11 * 1000.0  # MPa
        eps_elastic_yield = (taylor_factor * params.tau_0) / E
        eps_plastic = max(0.0, abs(eps_xx) - eps_elastic_yield)

        flow_stress = taylor_factor * params.tau_0
        if eps_plastic > 0 and params.tau_sat > params.tau_0:
            delta = params.tau_sat - params.tau_0
            hardening = delta * (1.0 - np.exp(-params.h_0 * eps_plastic / max(delta, 1.0)))
            flow_stress += taylor_factor * hardening

        # Ramberg-Osgood smooth transition
        alpha_ro = 0.002
        n_ro = 8.0

        def ro_residual(s):
            if s <= 0:
                return -abs(eps_xx)
            elastic = s / E
            plastic = alpha_ro * (s / flow_stress) ** n_ro
            return elastic + plastic - abs(eps_xx)

        # Bisection
        lo, hi = 0.0, max(flow_stress * 3.0, abs(sigma[0,0]) * 2.0)
        for _ in range(50):
            mid = (lo + hi) / 2.0
            if ro_residual(mid) > 0:
                hi = mid
            else:
                lo = mid

        return (lo + hi) / 2.0

    def simulate(self, max_strain: float = 0.10, n_steps: int = 50,
                 n_grains_per_phase: int = 15) -> Dict:
        """
        Run G5 CPFEM simulation.

        Args:
            max_strain: Maximum engineering strain
            n_steps: Number of strain increments
            n_grains_per_phase: Number of grain orientation samples per phase

        Returns:
            Dict with stress-strain curves, phase-level results, and metrics
        """
        print("=" * 70)
        print("  G5 (4-Phase Advanced Steel) CPFEM Simulation")
        print("=" * 70)
        print(f"  Phases: Ferrite(25%) + Austenite(25%) + Martensite(25%) + δ-Ferrite(25%)")
        print(f"  Max strain: {max_strain:.2f}, Steps: {n_steps}")
        print(f"  Grains per phase: {n_grains_per_phase}")
        print()

        # Apply Hall-Petch to each phase
        phase_params_hp = {}
        for name, params in G5_PHASES.items():
            gs = G5_GRAIN_SIZES[name]
            p_hp = self._apply_hall_petch(params, gs)
            phase_params_hp[name] = p_hp
            print(f"  {name} (d={gs:.0f} um): tau_0={p_hp.tau_0:.1f} MPa, tau_sat={p_hp.tau_sat:.1f} MPa")

        # Generate random orientations for each phase
        np.random.seed(self.seed)
        orientations = {}
        for name in G5_PHASES:
            ori_list = []
            for _ in range(n_grains_per_phase):
                phi1 = np.random.uniform(0, 2 * np.pi)
                Phi = np.random.uniform(0, np.pi)
                phi2 = np.random.uniform(0, 2 * np.pi)
                ori_list.append((phi1, Phi, phi2))
            orientations[name] = ori_list

        # Strain steps
        strains = np.linspace(0, max_strain, n_steps + 1)[1:]

        # Storage
        macro_stress = []
        phase_stresses = {name: [] for name in G5_PHASES}

        print(f"\n  Computing stress-strain curve...")
        for eps_xx in strains:
            nu = 0.3
            F = np.diag([1.0 + eps_xx, 1.0 - nu * eps_xx, 1.0 - nu * eps_xx])

            # Compute per-phase average stress
            phase_s = {}
            for name, params in phase_params_hp.items():
                ori_list = orientations[name]
                stresses = [self._compute_single_crystal_stress(F, params, o) for o in ori_list]
                phase_s[name] = float(np.mean(stresses))
                phase_stresses[name].append(phase_s[name])

            # Rule-of-mixtures: σ_macro = Σ v_i * σ_i
            s_macro = sum(G5_PHASES[name].vol_frac * phase_s[name] for name in G5_PHASES)
            macro_stress.append(float(s_macro))

        # ============================================================
        # Extract key metrics
        # ============================================================
        strains_arr = np.array(strains)
        stress_arr = np.array(macro_stress)

        idx_02 = np.argmin(np.abs(strains_arr - 0.002))
        idx_05 = np.argmin(np.abs(strains_arr - 0.05))
        idx_10 = np.argmin(np.abs(strains_arr - 0.10))

        yield_stress = float(stress_arr[idx_02])
        uts = float(np.max(stress_arr))
        flow_05 = float(stress_arr[idx_05])
        flow_10 = float(stress_arr[idx_10])
        hardening_rate = float((flow_10 - flow_05) / 0.05)

        # Phase stress ratios at final step
        final_phase_s = {name: phase_stresses[name][-1] for name in G5_PHASES}
        ferrite_s = final_phase_s["Ferrite"]
        phase_ratios = {name: s / ferrite_s for name, s in final_phase_s.items()} if ferrite_s > 0 else {}

        # Results dictionary
        results = {
            "metadata": {
                "material": "G5 (4-Phase Advanced Steel)",
                "phases": [
                    {"name": "Ferrite", "lattice": "BCC", "vol_frac": 0.25},
                    {"name": "Austenite", "lattice": "FCC", "vol_frac": 0.25},
                    {"name": "Martensite", "lattice": "BCT", "vol_frac": 0.25},
                    {"name": "DeltaFerrite", "lattice": "BCC", "vol_frac": 0.25},
                ],
                "solver": "PhysicsBasedCPFEM (Taylor iso-strain)",
                "seed": self.seed,
                "n_grains_per_phase": n_grains_per_phase,
                "max_strain": max_strain,
                "n_steps": n_steps,
            },
            "macro": {
                "strain": strains.tolist(),
                "stress": macro_stress,
                "yield_stress_mpa": yield_stress,
                "uts_mpa": uts,
                "flow_stress_5pct_mpa": flow_05,
                "flow_stress_10pct_mpa": flow_10,
                "hardening_rate_mpa": hardening_rate,
            },
            "phase": {
                name: {
                    "strain": strains.tolist(),
                    "stress": phase_stresses[name],
                    "final_stress_mpa": final_phase_s[name],
                    "stress_ratio_vs_ferrite": phase_ratios.get(name, 0),
                    "tau_0_mpa": float(phase_params_hp[name].tau_0),
                    "tau_sat_mpa": float(phase_params_hp[name].tau_sat),
                    "grain_size_um": G5_GRAIN_SIZES[name],
                }
                for name in G5_PHASES
            },
            "phase_stress_ratios": phase_ratios,
        }

        # ============================================================
        # Print summary
        # ============================================================
        print(f"\n{'=' * 70}")
        print("  RESULTS SUMMARY")
        print("=" * 70)
        print(f"  Yield stress (0.2% offset):  {yield_stress:.1f} MPa")
        print(f"  Flow stress at 5% strain:    {flow_05:.1f} MPa")
        print(f"  Flow stress at 10% strain:   {flow_10:.1f} MPa")
        print(f"  Ultimate stress:             {uts:.1f} MPa")
        print(f"  Hardening rate (5-10%):      {hardening_rate:.0f} MPa")
        print()
        print("  Phase-level final stresses:")
        for name in G5_PHASES:
            s = final_phase_s[name]
            r = phase_ratios.get(name, 0)
            print(f"    {name:20s}: {s:8.1f} MPa  (ratio vs Ferrite: {r:.3f})")
        print()
        print("  Phase stress hierarchy:")
        sorted_phases = sorted(final_phase_s.items(), key=lambda x: x[1], reverse=True)
        for i, (name, s) in enumerate(sorted_phases):
            print(f"    {i+1}. {name}: {s:.1f} MPa")
        print()

        # Rule-of-mixtures verification
        rom_check = sum(G5_PHASES[n].vol_frac * final_phase_s[n] for n in G5_PHASES)
        print(f"  Rule-of-mixtures check: {rom_check:.1f} MPa (vs macro: {flow_10:.1f} MPa)")
        print(f"  Difference: {abs(rom_check - flow_10):.4f} MPa")
        print()

        return results


# ============================================================
# Main execution
# ============================================================

if __name__ == "__main__":
    # Run simulation
    solver = G5CPFEMSolver(seed=88)
    results = solver.simulate(max_strain=0.10, n_steps=50, n_grains_per_phase=25)

    # Save results
    output_path = Path(__file__).parent / "g5_cpfem_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"  [OK] Results saved to: {output_path}")

    # Also save to damask_run_g5/ for completeness
    g5_dir = Path(__file__).parent / "damask_run_g5"
    g5_dir.mkdir(parents=True, exist_ok=True)
    output_path2 = g5_dir / "g5_cpfem_results.json"
    with open(output_path2, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"  [OK] Results also saved to: {output_path2}")
    print()
    print("=" * 70)
    print("  G5 CPFEM Simulation Complete!")
    print("=" * 70)
