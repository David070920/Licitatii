"""
Composite Risk Scorer

This module combines multiple risk detection algorithms to create a comprehensive
risk assessment for Romanian procurement tenders.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import numpy as np
from decimal import Decimal

from app.db.models import Tender, TenderRiskScore, RiskAlgorithm
from .base import BaseRiskDetector, RiskDetectionResult, RiskDetectionConfig
from .single_bidder_detector import SingleBidderDetector
from .price_anomaly_detector import PriceAnomalyDetector
from .frequent_winner_detector import FrequentWinnerDetector
from .geographic_clustering_detector import GeographicClusteringDetector


class CompositeRiskScorer:
    """Combines multiple risk detection algorithms into a comprehensive score"""
    
    def __init__(self, config: RiskDetectionConfig):
        self.config = config
        self.version = "1.0.0"
        
        # Initialize individual detectors
        self.single_bidder_detector = SingleBidderDetector(config)
        self.price_anomaly_detector = PriceAnomalyDetector(config)
        self.frequent_winner_detector = FrequentWinnerDetector(config)
        self.geographic_clustering_detector = GeographicClusteringDetector(config)
        
        # Algorithm weights
        self.weights = {
            "single_bidder": config.single_bidder_weight,
            "price_anomaly": config.price_anomaly_weight,
            "frequent_winner": config.frequent_winner_weight,
            "geographic_clustering": config.geographic_clustering_weight
        }
        
        # Normalize weights to sum to 1
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v/total_weight for k, v in self.weights.items()}
    
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Perform comprehensive risk analysis on a tender"""
        
        # Run individual algorithms
        single_bidder_result = self.single_bidder_detector.analyze_tender(tender, db)
        price_anomaly_result = self.price_anomaly_detector.analyze_tender(tender, db)
        frequent_winner_result = self.frequent_winner_detector.analyze_tender(tender, db)
        geographic_result = self.geographic_clustering_detector.analyze_tender(tender, db)
        
        # Combine results
        composite_result = self._combine_results(
            tender,
            single_bidder_result,
            price_anomaly_result,
            frequent_winner_result,
            geographic_result
        )
        
        return composite_result
    
    def analyze_batch(self, tenders: List[Tender], db: Session) -> List[RiskDetectionResult]:
        """Perform comprehensive risk analysis on multiple tenders"""
        
        results = []
        
        # Run batch analysis for each algorithm
        single_bidder_results = self.single_bidder_detector.analyze_batch(tenders, db)
        price_anomaly_results = self.price_anomaly_detector.analyze_batch(tenders, db)
        frequent_winner_results = self.frequent_winner_detector.analyze_batch(tenders, db)
        geographic_results = self.geographic_clustering_detector.analyze_batch(tenders, db)
        
        # Combine results for each tender
        for i, tender in enumerate(tenders):
            composite_result = self._combine_results(
                tender,
                single_bidder_results[i],
                price_anomaly_results[i],
                frequent_winner_results[i],
                geographic_results[i]
            )
            results.append(composite_result)
        
        return results
    
    def _combine_results(self, tender: Tender,
                        single_bidder_result: RiskDetectionResult,
                        price_anomaly_result: RiskDetectionResult,
                        frequent_winner_result: RiskDetectionResult,
                        geographic_result: RiskDetectionResult) -> RiskDetectionResult:
        """Combine individual algorithm results into composite score"""
        
        # Extract individual scores
        individual_scores = {
            "single_bidder": single_bidder_result.risk_score,
            "price_anomaly": price_anomaly_result.risk_score,
            "frequent_winner": frequent_winner_result.risk_score,
            "geographic_clustering": geographic_result.risk_score
        }
        
        # Calculate weighted composite score
        composite_score = sum(
            score * self.weights[algorithm] 
            for algorithm, score in individual_scores.items()
        )
        
        # Combine risk flags
        all_flags = []
        all_flags.extend(single_bidder_result.risk_flags)
        all_flags.extend(price_anomaly_result.risk_flags)
        all_flags.extend(frequent_winner_result.risk_flags)
        all_flags.extend(geographic_result.risk_flags)
        
        # Remove duplicates while preserving order
        unique_flags = []
        for flag in all_flags:
            if flag not in unique_flags:
                unique_flags.append(flag)
        
        # Apply risk amplification factors
        amplified_score = self._apply_amplification_factors(
            composite_score, individual_scores, unique_flags
        )
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            single_bidder_result,
            price_anomaly_result,
            frequent_winner_result,
            geographic_result
        )
        
        # Generate composite risk level
        risk_level = self._get_composite_risk_level(amplified_score)
        
        # Create detailed analysis
        detailed_analysis = {
            "composite_score": amplified_score,
            "individual_scores": individual_scores,
            "algorithm_weights": self.weights,
            "confidence": confidence,
            "risk_amplification_applied": amplified_score > composite_score,
            "algorithms": {
                "single_bidder": single_bidder_result.detailed_analysis,
                "price_anomaly": price_anomaly_result.detailed_analysis,
                "frequent_winner": frequent_winner_result.detailed_analysis,
                "geographic_clustering": geographic_result.detailed_analysis
            },
            "scoring_methodology": self._get_scoring_methodology(),
            "analysis_date": datetime.utcnow().isoformat(),
            "version": self.version
        }
        
        return RiskDetectionResult(
            risk_score=amplified_score,
            risk_level=risk_level,
            risk_flags=unique_flags,
            detailed_analysis=detailed_analysis,
            confidence=confidence
        )
    
    def _apply_amplification_factors(self, base_score: float, 
                                   individual_scores: Dict[str, float],
                                   flags: List[str]) -> float:
        """Apply amplification factors for multiple risk indicators"""
        
        amplified_score = base_score
        
        # Count high-risk algorithms
        high_risk_count = sum(1 for score in individual_scores.values() if score > 70)
        medium_risk_count = sum(1 for score in individual_scores.values() if 40 <= score <= 70)
        
        # Multiple high-risk algorithms amplification
        if high_risk_count >= 3:
            amplified_score *= 1.3
        elif high_risk_count >= 2:
            amplified_score *= 1.2
        elif high_risk_count >= 1 and medium_risk_count >= 2:
            amplified_score *= 1.15
        
        # Specific flag combinations that increase risk
        critical_flag_combinations = [
            ("SINGLE_BIDDER", "HIGH_WIN_RATE"),
            ("SINGLE_BIDDER", "DOMINANT_MARKET_POSITION"),
            ("ESTIMATED_VALUE_STATISTICAL_ANOMALY", "HIGH_WIN_RATE"),
            ("LOCAL_MARKET_DOMINANCE", "SINGLE_BIDDER"),
            ("VERY_HIGH_RECENT_WIN_RATE", "SINGLE_BIDDER")
        ]
        
        for flag1, flag2 in critical_flag_combinations:
            if flag1 in flags and flag2 in flags:
                amplified_score *= 1.25
                break
        
        # High-value tender amplification
        if "HIGH_VALUE_SINGLE_BIDDER" in flags:
            amplified_score *= 1.2
        
        return min(100.0, amplified_score)
    
    def _calculate_confidence(self, single_bidder_result: RiskDetectionResult,
                            price_anomaly_result: RiskDetectionResult,
                            frequent_winner_result: RiskDetectionResult,
                            geographic_result: RiskDetectionResult) -> float:
        """Calculate confidence level in the composite risk assessment"""
        
        # Base confidence from individual algorithms
        individual_confidences = [
            single_bidder_result.confidence,
            price_anomaly_result.confidence,
            frequent_winner_result.confidence,
            geographic_result.confidence
        ]
        
        # Average confidence
        avg_confidence = np.mean(individual_confidences)
        
        # Confidence adjustments
        
        # More algorithms with high confidence increase overall confidence
        high_confidence_count = sum(1 for conf in individual_confidences if conf > 0.8)
        if high_confidence_count >= 3:
            avg_confidence *= 1.1
        elif high_confidence_count >= 2:
            avg_confidence *= 1.05
        
        # Low confidence in any algorithm reduces overall confidence
        low_confidence_count = sum(1 for conf in individual_confidences if conf < 0.5)
        if low_confidence_count >= 2:
            avg_confidence *= 0.9
        elif low_confidence_count >= 1:
            avg_confidence *= 0.95
        
        # Consistency check - if algorithms agree on risk level, increase confidence
        risk_levels = [
            single_bidder_result.risk_level,
            price_anomaly_result.risk_level,
            frequent_winner_result.risk_level,
            geographic_result.risk_level
        ]
        
        level_consensus = max(risk_levels.count(level) for level in set(risk_levels))
        if level_consensus >= 3:
            avg_confidence *= 1.1
        elif level_consensus >= 2:
            avg_confidence *= 1.05
        
        return min(1.0, avg_confidence)
    
    def _get_composite_risk_level(self, score: float) -> str:
        """Get composite risk level based on score"""
        if score >= self.config.high_risk_threshold:
            return "HIGH"
        elif score >= self.config.medium_risk_threshold:
            return "MEDIUM"
        elif score >= self.config.low_risk_threshold:
            return "LOW"
        else:
            return "MINIMAL"
    
    def _get_scoring_methodology(self) -> Dict[str, Any]:
        """Get information about the scoring methodology"""
        return {
            "description": "Weighted combination of four risk detection algorithms",
            "algorithms": {
                "single_bidder": {
                    "weight": self.weights["single_bidder"],
                    "description": "Detects tenders with suspiciously few bidders"
                },
                "price_anomaly": {
                    "weight": self.weights["price_anomaly"],
                    "description": "Detects unusual pricing patterns using statistical analysis"
                },
                "frequent_winner": {
                    "weight": self.weights["frequent_winner"],
                    "description": "Detects companies with suspiciously high win rates"
                },
                "geographic_clustering": {
                    "weight": self.weights["geographic_clustering"],
                    "description": "Detects suspicious geographic patterns and local monopolies"
                }
            },
            "risk_thresholds": {
                "high": self.config.high_risk_threshold,
                "medium": self.config.medium_risk_threshold,
                "low": self.config.low_risk_threshold
            },
            "amplification_factors": {
                "multiple_high_risk": "Applied when multiple algorithms detect high risk",
                "critical_combinations": "Applied for specific flag combinations",
                "high_value_amplification": "Applied for high-value tenders with risk indicators"
            }
        }
    
    def save_risk_score(self, tender: Tender, result: RiskDetectionResult, db: Session) -> TenderRiskScore:
        """Save composite risk score to database"""
        
        # Create risk score record
        risk_score = TenderRiskScore(
            tender_id=tender.id,
            overall_risk_score=Decimal(str(result.risk_score)),
            risk_level=result.risk_level,
            single_bidder_risk=Decimal(str(result.detailed_analysis["individual_scores"]["single_bidder"])),
            price_anomaly_risk=Decimal(str(result.detailed_analysis["individual_scores"]["price_anomaly"])),
            frequency_risk=Decimal(str(result.detailed_analysis["individual_scores"]["frequent_winner"])),
            geographic_risk=Decimal(str(result.detailed_analysis["individual_scores"]["geographic_clustering"])),
            analysis_date=datetime.utcnow(),
            analysis_version=self.version,
            detailed_analysis=result.detailed_analysis,
            risk_flags=result.risk_flags,
            auto_generated=True
        )
        
        db.add(risk_score)
        db.commit()
        db.refresh(risk_score)
        
        return risk_score
    
    def update_algorithm_weights(self, new_weights: Dict[str, float]):
        """Update algorithm weights"""
        
        # Validate weights
        if not all(0 <= weight <= 1 for weight in new_weights.values()):
            raise ValueError("All weights must be between 0 and 1")
        
        # Update weights
        self.weights.update(new_weights)
        
        # Normalize weights to sum to 1
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v/total_weight for k, v in self.weights.items()}
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the composite scoring algorithm"""
        return {
            "name": "Composite Risk Scorer",
            "version": self.version,
            "description": "Combines multiple risk detection algorithms with weighted scoring",
            "component_algorithms": [
                self.single_bidder_detector.get_algorithm_info(),
                self.price_anomaly_detector.get_algorithm_info(),
                self.frequent_winner_detector.get_algorithm_info(),
                self.geographic_clustering_detector.get_algorithm_info()
            ],
            "scoring_methodology": self._get_scoring_methodology(),
            "current_weights": self.weights
        }
    
    def generate_risk_summary(self, result: RiskDetectionResult) -> Dict[str, Any]:
        """Generate a human-readable risk summary"""
        
        individual_scores = result.detailed_analysis["individual_scores"]
        
        # Identify primary risk factors
        primary_risks = []
        for algorithm, score in individual_scores.items():
            if score > 70:
                primary_risks.append({
                    "algorithm": algorithm,
                    "score": score,
                    "severity": "HIGH"
                })
            elif score > 40:
                primary_risks.append({
                    "algorithm": algorithm,
                    "score": score,
                    "severity": "MEDIUM"
                })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(result)
        
        return {
            "overall_risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "confidence": result.confidence,
            "primary_risk_factors": primary_risks,
            "total_risk_flags": len(result.risk_flags),
            "critical_flags": [flag for flag in result.risk_flags if "HIGH" in flag or "DOMINANT" in flag],
            "recommendations": recommendations,
            "analysis_date": result.detailed_analysis["analysis_date"]
        }
    
    def _generate_recommendations(self, result: RiskDetectionResult) -> List[str]:
        """Generate recommendations based on risk analysis"""
        
        recommendations = []
        flags = result.risk_flags
        individual_scores = result.detailed_analysis["individual_scores"]
        
        # Single bidder recommendations
        if individual_scores["single_bidder"] > 50:
            recommendations.append("Review tender specification for potential barriers to competition")
            if "SINGLE_BIDDER" in flags:
                recommendations.append("Investigate reasons for lack of competition")
        
        # Price anomaly recommendations
        if individual_scores["price_anomaly"] > 50:
            recommendations.append("Conduct detailed price analysis and market research")
            if "ESTIMATED_VALUE_STATISTICAL_ANOMALY" in flags:
                recommendations.append("Review estimated value calculation methodology")
        
        # Frequent winner recommendations
        if individual_scores["frequent_winner"] > 50:
            recommendations.append("Review market concentration and competition levels")
            if "DOMINANT_MARKET_POSITION" in flags:
                recommendations.append("Consider market investigation for potential monopolistic behavior")
        
        # Geographic clustering recommendations
        if individual_scores["geographic_clustering"] > 50:
            recommendations.append("Review geographic market dynamics and local competition")
            if "LOCAL_MARKET_DOMINANCE" in flags:
                recommendations.append("Investigate potential local monopolies or cartels")
        
        # High-risk recommendations
        if result.risk_score > 70:
            recommendations.append("Recommend detailed investigation by procurement oversight body")
            recommendations.append("Consider audit of procurement process and documentation")
        
        return recommendations