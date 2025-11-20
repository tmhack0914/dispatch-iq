"""
Business Rules for Dispatch Optimization
Provides rule-based success probability calculations
"""

import pandas as pd
import numpy as np
from config import BUSINESS_RULES


class DispatchBusinessRules:
    """Business rules for calculating dispatch success probability"""
    
    def __init__(self):
        self.max_distance = BUSINESS_RULES['max_distance_km']
        self.ideal_distance = BUSINESS_RULES['ideal_distance_km']
        self.max_workload = BUSINESS_RULES['max_workload_ratio']
        self.ideal_workload = BUSINESS_RULES['ideal_workload_ratio']
        self.skill_match_bonus = BUSINESS_RULES['skill_match_bonus']
        self.skill_mismatch_penalty = BUSINESS_RULES['skill_mismatch_penalty']
    
    def calculate_rule_based_probability(self, features: pd.Series) -> float:
        """
        Calculate success probability based on business rules
        
        Args:
            features: Series with dispatch features (distance, skill_match, workload_ratio, etc.)
            
        Returns:
            Success probability (0-1)
        """
        # Start with base probability
        base_prob = 0.70
        
        # Distance factor
        distance = features.get('distance', 0)
        distance_factor = self._calculate_distance_factor(distance)
        
        # Skill match factor
        skill_match = features.get('skill_match', 0)
        skill_factor = self._calculate_skill_factor(skill_match)
        
        # Workload factor
        workload_ratio = features.get('workload_ratio', 0.5)
        workload_factor = self._calculate_workload_factor(workload_ratio)
        
        # Priority factor
        priority = features.get('priority', 'Normal')
        priority_factor = self._calculate_priority_factor(priority)
        
        # Combine factors
        probability = base_prob * distance_factor * skill_factor * workload_factor * priority_factor
        
        # Clamp to [0, 1]
        probability = max(0.0, min(1.0, probability))
        
        return probability
    
    def _calculate_distance_factor(self, distance: float) -> float:
        """Calculate distance impact factor (0-1.2)"""
        if distance <= self.ideal_distance:
            # Bonus for short distances
            return 1.0 + (0.2 * (1 - distance / self.ideal_distance))
        elif distance <= self.max_distance:
            # Penalty increases with distance
            excess = distance - self.ideal_distance
            max_excess = self.max_distance - self.ideal_distance
            penalty = 0.4 * (excess / max_excess)
            return 1.0 - penalty
        else:
            # Heavy penalty for very long distances
            return 0.5
    
    def _calculate_skill_factor(self, skill_match: int) -> float:
        """Calculate skill match impact factor"""
        if skill_match == 1:
            return 1.0 + self.skill_match_bonus
        else:
            return 1.0 - self.skill_mismatch_penalty
    
    def _calculate_workload_factor(self, workload_ratio: float) -> float:
        """Calculate workload impact factor"""
        if workload_ratio <= self.ideal_workload:
            # Optimal workload
            return 1.0
        elif workload_ratio <= self.max_workload:
            # Moderate workload - slight penalty
            excess = workload_ratio - self.ideal_workload
            max_excess = self.max_workload - self.ideal_workload
            penalty = 0.15 * (excess / max_excess)
            return 1.0 - penalty
        else:
            # Overloaded - heavy penalty
            return 0.7
    
    def _calculate_priority_factor(self, priority: str) -> float:
        """Calculate priority impact factor"""
        priority_factors = {
            'Critical': 1.1,   # 10% boost for critical
            'High': 1.05,      # 5% boost for high
            'Normal': 1.0,     # No adjustment
            'Low': 0.95        # 5% reduction for low
        }
        return priority_factors.get(priority, 1.0)
    
    def validate_assignment(self, dispatch: pd.Series, technician: pd.Series, 
                          assignments_count: int) -> tuple:
        """
        Validate if assignment is acceptable based on business rules
        
        Args:
            dispatch: Dispatch data
            technician: Technician data
            assignments_count: Current number of assignments for technician
            
        Returns:
            (is_valid, warnings): Boolean validity and list of warning messages
        """
        warnings = []
        is_valid = True
        
        # Check distance
        distance = dispatch.get('distance', 0)
        if distance > self.max_distance:
            warnings.append(f"Distance {distance:.1f}km exceeds maximum {self.max_distance}km")
            is_valid = False
        elif distance > self.ideal_distance:
            warnings.append(f"Distance {distance:.1f}km exceeds ideal {self.ideal_distance}km")
        
        # Check workload
        capacity = technician.get('workload_capacity', 8)
        workload_ratio = assignments_count / capacity if capacity > 0 else 0
        
        if workload_ratio > self.max_workload:
            warnings.append(f"Technician workload {workload_ratio:.1%} exceeds maximum {self.max_workload:.0%}")
            # Don't invalidate, just warn
        
        # Check skill match
        if dispatch.get('required_skill') != technician.get('technician_skill'):
            warnings.append("Skill mismatch - technician assigned outside primary skill")
        
        return is_valid, warnings


def blend_probabilities(ml_prob: float, rule_prob: float, rule_weight: float = 0.7) -> float:
    """
    Blend ML and rule-based probabilities
    
    Args:
        ml_prob: ML model probability
        rule_prob: Rule-based probability
        rule_weight: Weight for rule-based (0-1), ML gets (1 - rule_weight)
        
    Returns:
        Blended probability
    """
    ml_weight = 1.0 - rule_weight
    blended = (rule_prob * rule_weight) + (ml_prob * ml_weight)
    return max(0.0, min(1.0, blended))


def calculate_business_success_probability(distance: float, workload_ratio: float,
                                          required_skill: str, tech_skill: str) -> float:
    """
    Standalone function to calculate success probability (for backward compatibility)
    
    Args:
        distance: Distance in km
        workload_ratio: Current workload ratio
        required_skill: Required skill for dispatch
        tech_skill: Technician's primary skill
        
    Returns:
        Success probability (0-1)
    """
    rules = DispatchBusinessRules()
    
    features = pd.Series({
        'distance': distance,
        'workload_ratio': workload_ratio,
        'skill_match': 1 if required_skill == tech_skill else 0,
        'priority': 'Normal'
    })
    
    return rules.calculate_rule_based_probability(features)


if __name__ == "__main__":
    # Test business rules
    print("Testing Business Rules...")
    
    rules = DispatchBusinessRules()
    
    # Test case 1: Ideal conditions
    test1 = pd.Series({
        'distance': 30,
        'skill_match': 1,
        'workload_ratio': 0.6,
        'priority': 'Normal'
    })
    prob1 = rules.calculate_rule_based_probability(test1)
    print(f"\nTest 1 (Ideal): {prob1:.1%}")
    
    # Test case 2: Long distance, skill mismatch
    test2 = pd.Series({
        'distance': 150,
        'skill_match': 0,
        'workload_ratio': 0.9,
        'priority': 'Critical'
    })
    prob2 = rules.calculate_rule_based_probability(test2)
    print(f"Test 2 (Challenging): {prob2:.1%}")
    
    # Test case 3: Very long distance
    test3 = pd.Series({
        'distance': 300,
        'skill_match': 1,
        'workload_ratio': 0.5,
        'priority': 'High'
    })
    prob3 = rules.calculate_rule_based_probability(test3)
    print(f"Test 3 (Too far): {prob3:.1%}")
    
    # Test blending
    print(f"\nBlending test:")
    print(f"  ML: 0.85, Rule: 0.70, Blend(70% rule): {blend_probabilities(0.85, 0.70, 0.7):.1%}")

