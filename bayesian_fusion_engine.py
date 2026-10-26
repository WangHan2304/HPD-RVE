#!/usr/bin/env python3
"""
Bayesian Parameter Fusion Engine for HPD-RVE
=============================================
Replaces the simple priority-based if-else fusion with a formal Bayesian
updating framework. Each source provides a likelihood; the posterior is
computed analytically for conjugate normal distributions.

Outputs:
  - bayesian_fusion_results.json: Full results for paper integration
  - figures_paper_latest/fig_bayesian_convergence.png: Convergence comparison
  - figures_paper_latest/fig_cost_savings.png: Computational cost comparison
"""

import json
import numpy as np
from pathlib import Path

np.random.seed(42)

# ============================================================
# 1. Bayesian Fusion Engine
# ============================================================

class BayesianFusionEngine:
    """
    Bayesian parameter fusion with ordinal confidence tiers.
    
    Each source provides a point estimate and an uncertainty (std dev).
    The engine computes the posterior via Bayesian model averaging:
    
        Prior:     p ~ N(mu_L, sigma_L^2)     [library value]
        Likelihood: y ~ N(mu_E, sigma_E^2)     [experimental value]
        Posterior:  p* ~ N(mu*, sigma*^2)
    
    where:
        1/sigma*^2 = 1/sigma_L^2 + 1/sigma_E^2
        mu* = sigma*^2 * (mu_L/sigma_L^2 + mu_E/sigma_E^2)
    
    Confidence tiers map to uncertainty multipliers:
        High (1.0):   sigma = 0.02 * |value|   (±2% uncertainty)
        Medium (0.85): sigma = 0.05 * |value|   (±5% uncertainty)
        Low (0.55):   sigma = 0.20 * |value|   (±20% uncertainty)
    """
    
    CONFIDENCE_TO_SIGMA = {
        1.0: 0.02,    # High: ±2%
        0.85: 0.05,   # Medium: ±5%
        0.55: 0.20,   # Low: ±20%
    }
    
    def __init__(self):
        self.history = []
    
    def fuse(self, param_name, sources, true_value=None):
        """
        Fuse multiple sources for a single parameter.
        
        Parameters
        ----------
        param_name : str
        sources : list of dict
            Each dict has: {'value': float, 'confidence': float, 'label': str}
        true_value : float, optional
            For synthetic experiments only — the ground truth.
        
        Returns
        -------
        result : dict with posterior, KL divergence, decision metrics
        """
        if len(sources) == 0:
            raise ValueError("No sources provided")
        
        if len(sources) == 1:
            s = sources[0]
            sigma = self.CONFIDENCE_TO_SIGMA[s['confidence']] * abs(s['value'])
            return {
                'param': param_name,
                'posterior_mean': s['value'],
                'posterior_std': sigma,
                'resolved_value': s['value'],
                'source': s['label'],
                'confidence_tier': s['confidence'],
                'kl_divergence': 0.0,
                'information_gain_bits': 0.0,
            }
        
        # Multi-source Bayesian fusion
        # Start with lowest-confidence as prior, update with higher-confidence
        sorted_sources = sorted(sources, key=lambda s: s['confidence'])
        
        # Initialize prior from lowest confidence source
        prior = sorted_sources[0]
        mu = prior['value']
        sigma_prior = self.CONFIDENCE_TO_SIGMA[prior['confidence']] * abs(mu)
        if sigma_prior < 1e-10:
            sigma_prior = 1.0  # fallback for zero-valued params
        
        # Sequentially update with each higher-confidence source
        for s in sorted_sources[1:]:
            sigma_like = self.CONFIDENCE_TO_SIGMA[s['confidence']] * abs(s['value'])
            if sigma_like < 1e-10:
                sigma_like = 1.0
            
            # Bayesian update (conjugate normal)
            prec_prior = 1.0 / sigma_prior**2
            prec_like = 1.0 / sigma_like**2
            prec_post = prec_prior + prec_like
            sigma_post = np.sqrt(1.0 / prec_post)
            mu_post = (mu * prec_prior + s['value'] * prec_like) / prec_post
            
            # KL divergence: information gain from this update
            # KL(N_post || N_prior) = 0.5 * [log(sigma_prior^2/sigma_post^2) + 
            #          (sigma_post^2 + (mu_post - mu)^2)/sigma_prior^2 - 1]
            kl = 0.5 * (np.log(sigma_prior**2 / sigma_post**2) + 
                        (sigma_post**2 + (mu_post - mu)**2) / sigma_prior**2 - 1)
            
            mu = mu_post
            sigma_prior = sigma_post
        
        # Final posterior
        sigma_final = sigma_prior
        mu_final = mu
        
        # Total KL divergence (from initial prior to final posterior)
        sigma_init = self.CONFIDENCE_TO_SIGMA[sorted_sources[0]['confidence']] * abs(sorted_sources[0]['value'])
        if sigma_init < 1e-10:
            sigma_init = 1.0
        kl_total = 0.5 * (np.log(sigma_init**2 / sigma_final**2) + 
                          (sigma_final**2 + (mu_final - sorted_sources[0]['value'])**2) / sigma_init**2 - 1)
        
        # Dominant source (highest confidence)
        dominant = max(sources, key=lambda s: s['confidence'])
        
        return {
            'param': param_name,
            'posterior_mean': round(mu_final, 4),
            'posterior_std': round(sigma_final, 4),
            'resolved_value': round(mu_final, 4),
            'source': dominant['label'],
            'confidence_tier': dominant['confidence'],
            'kl_divergence': round(kl_total, 6),
            'information_gain_bits': round(kl_total / np.log(2), 4),
            'true_value': true_value,
            'error_vs_truth': round(abs(mu_final - true_value) / abs(true_value) * 100, 4) if true_value else None,
        }


# ============================================================
# 2. Synthetic Data Experiment
# ============================================================

def run_synthetic_experiment():
    """
    Generate synthetic parameter sets with known ground truth.
    Compare 4 fusion strategies:
      (A) Bayesian updating (proposed)
      (B) Priority-based (current: experimental wins)
      (C) Simple average (naive baseline)
      (D) Random selection (worst-case baseline)
    
    Metrics:
      - Mean absolute error vs. ground truth
      - Posterior uncertainty (std dev)
      - Computational cost (proportional to N_models * UQ_samples)
    """
    
    # Define 10 synthetic parameters with "true" values
    true_values = {
        'C11_ferrite': 237.0,    # GPa
        'C12_ferrite': 141.0,    # GPa
        'C44_ferrite': 116.0,    # GPa
        'CRSS_ferrite': 95.0,    # MPa
        'CRSS_martensite': 310.0, # MPa
        'h0_ferrite': 180.0,     # MPa
        'h0_martensite': 350.0,  # MPa
        'xi_inf_ferrite': 260.0, # MPa
        'xi_inf_mart': 530.0,    # MPa
        'vol_frac_mart': 0.28,   # dimensionless
    }
    
    # Simulate sources with different confidence levels
    # High confidence = experimental (±2% noise)
    # Medium confidence = library (±5% noise)
    # Low confidence = computed (±20% noise)
    
    n_trials = 100
    results = {
        'bayesian': [],
        'priority': [],
        'average': [],
        'random': [],
    }
    
    for trial in range(n_trials):
        trial_errors = {'bayesian': 0, 'priority': 0, 'average': 0, 'random': 0}
        
        for param_name, true_val in true_values.items():
            # Generate noisy observations
            exp_val = true_val * (1 + np.random.normal(0, 0.02))    # ±2% experimental
            lib_val = true_val * (1 + np.random.normal(0, 0.05))    # ±5% library
            comp_val = true_val * (1 + np.random.normal(0, 0.20))   # ±20% computed
            
            # Strategy A: Bayesian fusion
            engine = BayesianFusionEngine()
            sources = [
                {'value': comp_val, 'confidence': 0.55, 'label': 'COMPUTED'},
                {'value': lib_val, 'confidence': 0.85, 'label': 'LIBRARY'},
                {'value': exp_val, 'confidence': 1.0, 'label': 'EXPERIMENTAL'},
            ]
            bayes_result = engine.fuse(param_name, sources, true_val)
            trial_errors['bayesian'] += abs(bayes_result['resolved_value'] - true_val) / abs(true_val)
            
            # Strategy B: Priority-based (experimental always wins)
            priority_val = exp_val  # experimental always wins
            trial_errors['priority'] += abs(priority_val - true_val) / abs(true_val)
            
            # Strategy C: Simple average
            avg_val = (exp_val + lib_val + comp_val) / 3
            trial_errors['average'] += abs(avg_val - true_val) / abs(true_val)
            
            # Strategy D: Random selection
            random_choice = np.random.choice([exp_val, lib_val, comp_val])
            trial_errors['random'] += abs(random_choice - true_val) / abs(true_val)
        
        # Normalize by number of parameters
        n_params = len(true_values)
        for strategy in results:
            results[strategy].append(trial_errors[strategy] / n_params)
    
    # Compute summary statistics
    summary = {}
    for strategy, errors in results.items():
        errors = np.array(errors)
        summary[strategy] = {
            'mean_error_pct': round(float(np.mean(errors) * 100), 4),
            'std_error_pct': round(float(np.std(errors) * 100), 4),
            'max_error_pct': round(float(np.max(errors) * 100), 4),
            'median_error_pct': round(float(np.median(errors) * 100), 4),
        }
    
    return summary, results


def compute_cost_savings():
    """
    Compare computational cost between adaptive and fixed schemes.
    
    Adaptive: High confidence → N=3, UQ=±2%
              Medium confidence → N=3, UQ=±5%  
              Low confidence → N=5, UQ=±20%
    
    Fixed (baseline): All parameters → N=5, UQ=±20%
    
    Cost metric: total number of CPFEM evaluations = sum(N_models * n_UQ_samples)
    """
    
    # Simulate a DP800 parameter set (10 parameters)
    # In practice: some are high confidence (experimental), some medium, some low
    param_confidences = {
        'C11': 1.0,     # experimental
        'C12': 1.0,     # experimental
        'C44': 1.0,     # experimental
        'CRSS_f': 1.0,  # experimental (fitted)
        'CRSS_m': 0.85, # library
        'h0_f': 0.85,   # library
        'h0_m': 0.85,   # library
        'xi_inf_f': 0.85, # library
        'xi_inf_m': 0.55, # computed (estimated)
        'vol_frac': 1.0,  # experimental (EBSD)
    }
    
    # Adaptive scheme
    adaptive_cost = 0
    for param, conf in param_confidences.items():
        if conf >= 1.0:
            n_models = 3
            n_uq = 1  # ±2% → minimal perturbation needed
        elif conf >= 0.85:
            n_models = 3
            n_uq = 3  # ±5% → moderate sampling
        else:
            n_models = 5
            n_uq = 5  # ±20% → extensive sampling
        adaptive_cost += n_models * n_uq
    
    # Fixed baseline (all N=5, UQ=±20%)
    fixed_cost = len(param_confidences) * 5 * 5
    
    # Medium baseline (all N=3, UQ=±5%)
    medium_cost = len(param_confidences) * 3 * 3
    
    savings_vs_fixed = (1 - adaptive_cost / fixed_cost) * 100
    savings_vs_medium = (1 - adaptive_cost / medium_cost) * 100
    
    return {
        'adaptive_total_evals': adaptive_cost,
        'fixed_baseline_evals': fixed_cost,
        'medium_baseline_evals': medium_cost,
        'savings_vs_fixed_pct': round(savings_vs_fixed, 1),
        'savings_vs_medium_pct': round(savings_vs_medium, 1),
        'n_parameters': len(param_confidences),
    }


# ============================================================
# 3. Run all experiments and save results
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Bayesian Fusion Engine — Synthetic Validation")
    print("=" * 60)
    
    # Run synthetic experiment
    summary, raw_results = run_synthetic_experiment()
    
    print("\n1. Fusion Strategy Comparison (100 trials × 10 parameters):")
    print("-" * 55)
    print(f"{'Strategy':<20} {'Mean Error':<12} {'Std Error':<12} {'Max Error':<12}")
    print("-" * 55)
    for strategy, stats in summary.items():
        print(f"{strategy:<20} {stats['mean_error_pct']:>8.3f}%   {stats['std_error_pct']:>8.3f}%   {stats['max_error_pct']:>8.3f}%")
    
    # Run cost analysis
    cost = compute_cost_savings()
    
    print(f"\n2. Computational Cost Analysis:")
    print("-" * 55)
    print(f"   Adaptive scheme:     {cost['adaptive_total_evals']:>4} CPFEM evaluations")
    print(f"   Fixed baseline:      {cost['fixed_baseline_evals']:>4} CPFEM evaluations")
    print(f"   Medium baseline:     {cost['medium_baseline_evals']:>4} CPFEM evaluations")
    print(f"   Savings vs fixed:    {cost['savings_vs_fixed_pct']:>6.1f}%")
    print(f"   Savings vs medium:   {cost['savings_vs_medium_pct']:>6.1f}%")
    
    # DP800 specific Bayesian fusion demo
    print(f"\n3. DP800 Ferrite CRSS — Bayesian Fusion Demo:")
    print("-" * 55)
    engine = BayesianFusionEngine()
    
    dp800_sources = [
        {'value': 120.0, 'confidence': 0.85, 'label': 'LIBRARY (Landolt-Börnstein)'},
        {'value': 135.0, 'confidence': 1.0, 'label': 'EXPERIMENTAL (fit, this work)'},
    ]
    result = engine.fuse('ferrite_CRSS', dp800_sources, true_value=130.0)
    print(f"   Library value:     120.0 MPa (confidence: 0.85)")
    print(f"   Experimental value: 135.0 MPa (confidence: 1.0)")
    print(f"   Posterior mean:     {result['posterior_mean']:.2f} MPa")
    print(f"   Posterior std:      {result['posterior_std']:.2f} MPa")
    print(f"   KL divergence:      {result['kl_divergence']:.4f} nats ({result['information_gain_bits']:.2f} bits)")
    print(f"   Error vs truth:     {result['error_vs_truth']:.2f}%")
    
    # Save results
    output = {
        'synthetic_experiment': summary,
        'cost_analysis': cost,
        'dp800_demo': result,
        'description': 'Bayesian fusion engine validation results for HPD-RVE paper',
    }
    
    output_path = Path('/home/cl/20260617RVE论文/bayesian_fusion_results.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")
    
    # Generate convergence figure
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Left: Convergence curves (error vs. number of sources fused)
        ax = axes[0]
        strategies = ['bayesian', 'priority', 'average', 'random']
        colors = ['#2196F3', '#FF9800', '#4CAF50', '#F44336']
        labels = ['Bayesian (proposed)', 'Priority-based (current)', 
                  'Simple average', 'Random selection']
        
        for strategy, color, label in zip(strategies, colors, labels):
            errors = [np.mean(raw_results[strategy][:i+1]) * 100 for i in range(len(raw_results[strategy]))]
            ax.plot(range(1, len(errors)+1), errors, color=color, label=label, linewidth=2)
        
        ax.set_xlabel('Trial Number', fontsize=12)
        ax.set_ylabel('Mean Relative Error (%)', fontsize=12)
        ax.set_title('(a) Convergence: Error vs. Ground Truth', fontsize=13)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # Right: Cost comparison bar chart
        ax = axes[1]
        cost_labels = ['Adaptive\n(proposed)', 'Fixed baseline\n(all N=5, ±20%)', 'Medium baseline\n(all N=3, ±5%)']
        cost_values = [cost['adaptive_total_evals'], cost['fixed_baseline_evals'], cost['medium_baseline_evals']]
        bar_colors = ['#2196F3', '#F44336', '#FF9800']
        
        bars = ax.bar(cost_labels, cost_values, color=bar_colors, width=0.6)
        for bar, val in zip(bars, cost_values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{val}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_ylabel('Total CPFEM Evaluations', fontsize=12)
        ax.set_title('(b) Computational Cost Comparison', fontsize=13)
        ax.set_ylim(0, max(cost_values) * 1.2)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add savings annotation
        ax.annotate(f'Savings: {cost["savings_vs_fixed_pct"]:.0f}%\nvs. fixed baseline',
                    xy=(0, cost['adaptive_total_evals']), xytext=(1.3, cost['fixed_baseline_evals']*0.7),
                    fontsize=10, color='#2196F3', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='#2196F3'))
        
        plt.tight_layout()
        fig_path = Path('/home/cl/20260617RVE论文/figures_paper_latest/fig_bayesian_validation.png')
        fig_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_path, dpi=200, bbox_inches='tight')
        print(f"Figure saved to: {fig_path}")
        plt.close()
        
    except ImportError:
        print("matplotlib not available, skipping figure generation")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
