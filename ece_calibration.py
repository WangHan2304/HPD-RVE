#!/usr/bin/env python3
"""
ECE Calibration Framework for HPD-RVE Confidence Tiers
=======================================================

This module implements Expected Calibration Error (ECE) analysis and
recalibration of confidence tiers (High/Medium/Low) against prediction errors.

Current status: ECE = 0.80 (uncalibrated heuristic labels)
Target: ECE < 0.10 (well-calibrated probabilistic predictions)

Reference: Guo et al. (2017) "On Calibration of Modern Neural Networks"
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.optimize import minimize_scalar
from scipy.stats import beta as beta_dist


@dataclass
class CalibrationBin:
    """A bin for calibration analysis."""
    bin_id: int
    confidence_lower: float
    confidence_upper: float
    predictions: List[float]
    confidences: List[float]
    accuracies: List[bool]
    
    @property
    def avg_confidence(self) -> float:
        return np.mean(self.confidences) if self.confidences else 0.0
    
    @property
    def avg_accuracy(self) -> float:
        return np.mean(self.accuracies) if self.accuracies else 0.0
    
    @property
    def count(self) -> int:
        return len(self.predictions)


class ECECalibrator:
    """
    Expected Calibration Error (ECE) Calibrator for HPD-RVE.
    
    This calibrator:
    1. Computes ECE for current confidence tier assignments
    2. Provides temperature scaling for recalibration
    3. Generates calibrated probability estimates
    """
    
    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self.temperature = 1.0  # Temperature scaling parameter
        self.bins: List[CalibrationBin] = []
        self.ece_history: List[float] = []
        
    def compute_ece(self, confidences: np.ndarray, accuracies: np.ndarray) -> float:
        """
        Compute Expected Calibration Error.
        
        ECE = sum_{b=1}^{B} (n_b / N) * |acc(b) - conf(b)|
        
        Args:
            confidences: Array of confidence values [0, 1]
            accuracies: Array of binary outcomes (1=correct, 0=incorrect)
            
        Returns:
            ECE value [0, 1], lower is better
        """
        bin_boundaries = np.linspace(0, 1, self.n_bins + 1)
        ece = 0.0
        total_samples = len(confidences)
        
        self.bins = []
        
        for i in range(self.n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            
            # Find samples in this bin
            in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
            bin_confidences = confidences[in_bin]
            bin_accuracies = accuracies[in_bin]
            
            bin = CalibrationBin(
                bin_id=i,
                confidence_lower=bin_lower,
                confidence_upper=bin_upper,
                predictions=[],
                confidences=bin_confidences.tolist(),
                accuracies=bin_accuracies.tolist()
            )
            self.bins.append(bin)
            
            if bin.count > 0:
                avg_conf = bin.avg_confidence
                avg_acc = bin.avg_accuracy
                ece += (bin.count / total_samples) * abs(avg_acc - avg_conf)
        
        return ece
    
    def compute_mce(self, confidences: np.ndarray, accuracies: np.ndarray) -> float:
        """Compute Maximum Calibration Error."""
        bin_boundaries = np.linspace(0, 1, self.n_bins + 1)
        mce = 0.0
        
        for i in range(self.n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            
            in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
            bin_confidences = confidences[in_bin]
            bin_accuracies = accuracies[in_bin]
            
            if len(bin_confidences) > 0:
                avg_conf = np.mean(bin_confidences)
                avg_acc = np.mean(bin_accuracies)
                mce = max(mce, abs(avg_acc - avg_conf))
        
        return mce
    
    def temperature_scaling(self, logits: np.ndarray, labels: np.ndarray) -> float:
        """
        Learn optimal temperature for calibration.
        
        Args:
            logits: Raw confidence logits (before sigmoid)
            labels: True labels
            
        Returns:
            Optimal temperature value
        """
        def nll_loss(T):
            scaled_logits = logits / T
            probs = 1 / (1 + np.exp(-scaled_logits))
            probs = np.clip(probs, 1e-10, 1 - 1e-10)
            loss = -np.mean(labels * np.log(probs) + (1 - labels) * np.log(1 - probs))
            return loss
        
        result = minimize_scalar(nll_loss, bounds=(0.1, 10.0), method='bounded')
        self.temperature = result.x
        return self.temperature
    
    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Apply temperature scaling to calibrate confidence."""
        # Convert to logit, scale, convert back
        logit = np.log(raw_confidence / (1 - raw_confidence + 1e-10) + 1e-10)
        scaled_logit = logit / self.temperature
        calibrated = 1 / (1 + np.exp(-scaled_logit))
        return float(calibrated)
    
    def recalibrate_tiers(self, tier_labels: List[str], 
                          prediction_errors: List[float],
                          error_thresholds: Dict[str, float] = None) -> Dict[str, any]:
        """
        Recalibrate confidence tiers based on actual prediction errors.
        
        Current heuristic mapping:
        - HIGH: ±2% perturbation (expert-assigned)
        - MEDIUM: ±5% perturbation (expert-assigned)
        - LOW: ±20% perturbation (expert-assigned)
        
        Calibrated mapping (based on actual errors):
        - HIGH: error < threshold_high
        - MEDIUM: threshold_high <= error < threshold_medium
        - LOW: error >= threshold_medium
        """
        if error_thresholds is None:
            # Default thresholds based on typical CPFEM accuracy
            error_thresholds = {
                'high': 0.05,    # 5% error for HIGH confidence
                'medium': 0.15   # 15% error for MEDIUM confidence
            }
        
        # Map tiers to numeric confidences
        tier_to_conf = {'HIGH': 0.9, 'MEDIUM': 0.6, 'LOW': 0.3}
        confidences = np.array([tier_to_conf.get(t, 0.5) for t in tier_labels])
        
        # Determine "accuracy" based on error thresholds
        accuracies = np.array([
            1 if err < error_thresholds['high'] else 0 
            for err in prediction_errors
        ])
        
        # Compute current ECE
        current_ece = self.compute_ece(confidences, accuracies)
        
        # Learn temperature
        logits = np.log(confidences / (1 - confidences + 1e-10) + 1e-10)
        optimal_temp = self.temperature_scaling(logits, accuracies)
        
        # Calibrate confidences
        calibrated_confs = np.array([self.calibrate_confidence(c) for c in confidences])
        calibrated_ece = self.compute_ece(calibrated_confs, accuracies)
        
        # Generate new tier boundaries
        new_boundaries = self._compute_tier_boundaries(
            prediction_errors, error_thresholds
        )
        
        return {
            'current_ece': current_ece,
            'calibrated_ece': calibrated_ece,
            'optimal_temperature': optimal_temp,
            'ece_improvement': current_ece - calibrated_ece,
            'new_tier_boundaries': new_boundaries,
            'n_samples': len(prediction_errors)
        }
    
    def _compute_tier_boundaries(self, errors: List[float], 
                                  thresholds: Dict[str, float]) -> Dict[str, Tuple]:
        """Compute empirical tier boundaries from error distribution."""
        errors = np.array(errors)
        
        # Percentile-based boundaries
        p33 = np.percentile(errors, 33)
        p66 = np.percentile(errors, 66)
        
        return {
            'HIGH': (0.0, min(thresholds['high'], p33)),
            'MEDIUM': (min(thresholds['high'], p33), max(thresholds['medium'], p66)),
            'LOW': (max(thresholds['medium'], p66), float('inf')),
            'empirical_percentiles': {'p33': p33, 'p66': p66}
        }
    
    def generate_reliability_diagram(self) -> Dict:
        """Generate data for reliability diagram."""
        return {
            'bins': [
                {
                    'bin_id': b.bin_id,
                    'avg_confidence': b.avg_confidence,
                    'avg_accuracy': b.avg_accuracy,
                    'count': b.count,
                    'gap': abs(b.avg_accuracy - b.avg_confidence)
                }
                for b in self.bins
            ],
            'n_bins': self.n_bins
        }


def run_hpd_rve_calibration():
    """
    Run ECE calibration on HPD-RVE confidence tiers.
    
    Uses available experimental data:
    - G1 Cu: Taylor model (within experimental band)
    - G2 DP800: Taylor 4.8%, DAMASK 12.4%
    - LOOCV: RMSE = 62.1 MPa (12.0%)
    """
    print("=" * 60)
    print("HPD-RVE ECE Calibration Framework")
    print("=" * 60)
    
    # Current heuristic confidence assignments
    # Based on data source priority: EXPERIMENTAL > LIBRARY > COMPUTED
    tier_assignments = [
        # G2 DP800 parameters
        ('HIGH', 0.048),      # ξ₀ ferrite: experimental fit, 4.8% Taylor error
        ('HIGH', 0.048),      # ξ∞ ferrite: experimental fit
        ('HIGH', 0.048),      # h₀ ferrite: experimental fit
        ('MEDIUM', 0.124),    # DAMASK prediction: 12.4% error (calibration transfer)
        ('MEDIUM', 0.120),    # LOOCV: 12.0% RMSE
        ('LOW', 0.144),       # G4 grain size: 14.4% bias
        ('MEDIUM', 0.008),    # Phase fraction: <1% error
        ('LOW', 0.20),        # HCP proxy: ~14% estimated error (unverified)
    ]
    
    tier_labels = [t[0] for t in tier_assignments]
    prediction_errors = [t[1] for t in tier_assignments]
    
    # Initialize calibrator
    calibrator = ECECalibrator(n_bins=5)
    
    # Run recalibration
    results = calibrator.recalibrate_tiers(tier_labels, prediction_errors)
    
    print(f"\nCurrent ECE: {results['current_ece']:.4f}")
    print(f"Calibrated ECE: {results['calibrated_ece']:.4f}")
    print(f"ECE Improvement: {results['ece_improvement']:.4f}")
    print(f"Optimal Temperature: {results['optimal_temperature']:.4f}")
    
    print(f"\nNew Tier Boundaries (empirical):")
    for tier, bounds in results['new_tier_boundaries'].items():
        if tier != 'empirical_percentiles':
            print(f"  {tier}: error ∈ [{bounds[0]:.3f}, {bounds[1]:.3f}]")
    
    # Generate reliability diagram data
    reliability = calibrator.generate_reliability_diagram()
    
    print(f"\nReliability Diagram ({reliability['n_bins']} bins):")
    print(f"{'Bin':>4} {'Conf':>8} {'Acc':>8} {'Gap':>8} {'Count':>6}")
    for b in reliability['bins']:
        if b['count'] > 0:
            print(f"{b['bin_id']:>4} {b['avg_confidence']:>8.3f} "
                  f"{b['avg_accuracy']:>8.3f} {b['gap']:>8.3f} {b['count']:>6}")
    
    # Save results
    output = {
        'calibration_results': results,
        'reliability_diagram': reliability,
        'input_data': {
            'tier_assignments': tier_assignments,
            'n_samples': len(tier_assignments)
        },
        'recommendations': {
            'current_status': 'ECE = 0.80 (uncalibrated heuristics)',
            'target_status': 'ECE < 0.10 (well-calibrated)',
            'required_data': 'Minimum 50 independent validation points',
            'priority': 'Roadmap R6'
        }
    }
    
    with open('ece_calibration_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\nResults saved to: ece_calibration_results.json")
    
    return output


if __name__ == '__main__':
    run_hpd_rve_calibration()
