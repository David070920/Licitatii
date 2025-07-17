"""
Price Anomaly Detection Algorithm

This module implements risk detection for unusual pricing patterns in tenders,
using statistical analysis including z-scores and isolation forests.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.db.models import Tender, TenderBid, TenderAward, ContractingAuthority, CPVCode
from .base import BaseRiskDetector, RiskDetectionResult, RiskDetectionConfig, RiskAnalysisUtils


class PriceAnomalyDetector(BaseRiskDetector):
    """Detector for price anomaly patterns in tenders"""
    
    def __init__(self, config: RiskDetectionConfig):
        super().__init__(config)
        self.algorithm_name = "Price Anomaly Detection"
        self.algorithm_version = "1.0.0"
    
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Analyze a single tender for price anomalies"""
        
        if not tender.estimated_value or tender.estimated_value <= 0:
            return RiskDetectionResult(
                risk_score=0.0,
                risk_level="MINIMAL",
                risk_flags=["NO_ESTIMATED_VALUE"],
                detailed_analysis={
                    "algorithm": self.algorithm_name,
                    "analysis_type": "single_tender",
                    "reason": "No estimated value available"
                }
            )
        
        risk_flags = []
        risk_factors = {}
        
        # Get comparable tenders for analysis
        comparable_tenders = self._get_comparable_tenders(tender, db)
        
        if len(comparable_tenders) < self.config.min_sample_size_price_analysis:
            return RiskDetectionResult(
                risk_score=0.0,
                risk_level="MINIMAL",
                risk_flags=["INSUFFICIENT_COMPARABLE_DATA"],
                detailed_analysis={
                    "algorithm": self.algorithm_name,
                    "analysis_type": "single_tender",
                    "comparable_tenders_count": len(comparable_tenders),
                    "min_required": self.config.min_sample_size_price_analysis
                }
            )
        
        # Analyze estimated value anomalies
        estimated_value_analysis = self._analyze_estimated_value_anomalies(
            tender, comparable_tenders, risk_factors
        )
        
        # Analyze winning bid anomalies if available
        winning_bid_analysis = self._analyze_winning_bid_anomalies(
            tender, comparable_tenders, risk_factors
        )
        
        # Analyze bid spread anomalies
        bid_spread_analysis = self._analyze_bid_spread_anomalies(
            tender, comparable_tenders, risk_factors
        )
        
        # Calculate combined risk score
        risk_score = self._calculate_price_anomaly_risk_score(
            estimated_value_analysis,
            winning_bid_analysis, 
            bid_spread_analysis,
            risk_factors
        )
        
        # Generate risk flags
        risk_flags = self._generate_price_anomaly_flags(
            estimated_value_analysis,
            winning_bid_analysis,
            bid_spread_analysis,
            risk_factors
        )
        
        detailed_analysis = {
            "estimated_value_analysis": estimated_value_analysis,
            "winning_bid_analysis": winning_bid_analysis,
            "bid_spread_analysis": bid_spread_analysis,
            "risk_factors": risk_factors,
            "comparable_tenders_count": len(comparable_tenders),
            "algorithm": self.algorithm_name,
            "version": self.algorithm_version,
            "analysis_type": "single_tender",
            "analysis_date": datetime.utcnow().isoformat()
        }
        
        return RiskDetectionResult(
            risk_score=risk_score,
            risk_level=self.get_risk_level(risk_score),
            risk_flags=risk_flags,
            detailed_analysis=detailed_analysis
        )
    
    def analyze_batch(self, tenders: List[Tender], db: Session) -> List[RiskDetectionResult]:
        """Analyze multiple tenders for price anomalies using batch processing"""
        
        # Convert to DataFrame for efficient analysis
        df = RiskAnalysisUtils.convert_to_dataframe(tenders)
        
        results = []
        
        # Group by CPV code for better comparison
        cpv_groups = df.groupby('cpv_code')
        
        for cpv_code, group in cpv_groups:
            if len(group) < self.config.min_sample_size_price_analysis:
                # Individual analysis for small groups
                group_tenders = [t for t in tenders if t.cpv_code == cpv_code]
                for tender in group_tenders:
                    results.append(self.analyze_tender(tender, db))
            else:
                # Batch analysis for larger groups
                batch_results = self._analyze_cpv_batch(group, tenders, db)
                results.extend(batch_results)
        
        return results
    
    def _get_comparable_tenders(self, tender: Tender, db: Session) -> List[Tender]:
        """Get comparable tenders for price analysis"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=365 * 2)  # 2 years
        
        # Primary search: same CPV code
        comparable_query = db.query(Tender).filter(
            and_(
                Tender.cpv_code == tender.cpv_code,
                Tender.estimated_value.isnot(None),
                Tender.estimated_value > 0,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        )
        
        comparable_tenders = comparable_query.all()
        
        # If insufficient data, expand to parent CPV codes
        if len(comparable_tenders) < self.config.min_sample_size_price_analysis and tender.cpv_code:
            parent_cpv = tender.cpv_code[:6]  # Get parent CPV code
            
            parent_query = db.query(Tender).filter(
                and_(
                    Tender.cpv_code.like(f"{parent_cpv}%"),
                    Tender.estimated_value.isnot(None),
                    Tender.estimated_value > 0,
                    Tender.publication_date >= cutoff_date,
                    Tender.id != tender.id
                )
            )
            
            comparable_tenders = parent_query.all()
        
        return comparable_tenders
    
    def _analyze_estimated_value_anomalies(self, tender: Tender, comparable_tenders: List[Tender], 
                                         risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze estimated value anomalies"""
        
        estimated_values = [float(t.estimated_value) for t in comparable_tenders]
        tender_value = float(tender.estimated_value)
        
        # Calculate statistical measures
        mean_value = np.mean(estimated_values)
        median_value = np.median(estimated_values)
        std_value = np.std(estimated_values)
        
        # Z-score analysis
        z_score = self.calculate_z_score(tender_value, mean_value, std_value)
        
        # Isolation Forest analysis
        isolation_score = self._calculate_isolation_score(
            [tender_value], estimated_values
        )
        
        # IQR analysis
        q1 = np.percentile(estimated_values, 25)
        q3 = np.percentile(estimated_values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        is_outlier_iqr = tender_value < lower_bound or tender_value > upper_bound
        
        # Percentile analysis
        percentile = stats.percentileofscore(estimated_values, tender_value)
        
        analysis = {
            "tender_value": tender_value,
            "mean_value": mean_value,
            "median_value": median_value,
            "std_value": std_value,
            "z_score": z_score,
            "isolation_score": isolation_score,
            "percentile": percentile,
            "is_outlier_iqr": is_outlier_iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "comparable_count": len(comparable_tenders)
        }
        
        # Update risk factors
        if z_score > self.config.price_anomaly_z_threshold:
            risk_factors["high_z_score_estimated"] = True
        
        if isolation_score > self.config.price_anomaly_isolation_threshold:
            risk_factors["isolation_anomaly_estimated"] = True
        
        if is_outlier_iqr:
            risk_factors["iqr_outlier_estimated"] = True
        
        return analysis
    
    def _analyze_winning_bid_anomalies(self, tender: Tender, comparable_tenders: List[Tender], 
                                     risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze winning bid anomalies"""
        
        # Get winning bid for current tender
        winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
        
        if not winning_bid or not winning_bid.bid_amount:
            return {"analysis": "no_winning_bid"}
        
        # Get winning bids from comparable tenders
        comparable_winning_bids = []
        for comp_tender in comparable_tenders:
            comp_winning_bid = next((bid for bid in comp_tender.bids if bid.is_winner), None)
            if comp_winning_bid and comp_winning_bid.bid_amount:
                comparable_winning_bids.append(float(comp_winning_bid.bid_amount))
        
        if len(comparable_winning_bids) < self.config.min_sample_size_price_analysis:
            return {"analysis": "insufficient_winning_bid_data"}
        
        winning_amount = float(winning_bid.bid_amount)
        
        # Statistical analysis
        mean_winning = np.mean(comparable_winning_bids)
        median_winning = np.median(comparable_winning_bids)
        std_winning = np.std(comparable_winning_bids)
        
        z_score = self.calculate_z_score(winning_amount, mean_winning, std_winning)
        isolation_score = self._calculate_isolation_score(
            [winning_amount], comparable_winning_bids
        )
        
        # Analyze bid-to-estimate ratio
        bid_to_estimate_ratio = winning_amount / float(tender.estimated_value)
        
        comparable_ratios = []
        for comp_tender in comparable_tenders:
            comp_winning_bid = next((bid for bid in comp_tender.bids if bid.is_winner), None)
            if (comp_winning_bid and comp_winning_bid.bid_amount and 
                comp_tender.estimated_value and comp_tender.estimated_value > 0):
                ratio = float(comp_winning_bid.bid_amount) / float(comp_tender.estimated_value)
                comparable_ratios.append(ratio)
        
        ratio_analysis = {}
        if comparable_ratios:
            ratio_mean = np.mean(comparable_ratios)
            ratio_std = np.std(comparable_ratios)
            ratio_z_score = self.calculate_z_score(bid_to_estimate_ratio, ratio_mean, ratio_std)
            
            ratio_analysis = {
                "bid_to_estimate_ratio": bid_to_estimate_ratio,
                "ratio_mean": ratio_mean,
                "ratio_std": ratio_std,
                "ratio_z_score": ratio_z_score
            }
            
            if ratio_z_score > self.config.price_anomaly_z_threshold:
                risk_factors["anomalous_bid_to_estimate_ratio"] = True
        
        analysis = {
            "winning_amount": winning_amount,
            "mean_winning": mean_winning,
            "median_winning": median_winning,
            "std_winning": std_winning,
            "z_score": z_score,
            "isolation_score": isolation_score,
            "ratio_analysis": ratio_analysis,
            "comparable_count": len(comparable_winning_bids)
        }
        
        if z_score > self.config.price_anomaly_z_threshold:
            risk_factors["high_z_score_winning"] = True
        
        if isolation_score > self.config.price_anomaly_isolation_threshold:
            risk_factors["isolation_anomaly_winning"] = True
        
        return analysis
    
    def _analyze_bid_spread_anomalies(self, tender: Tender, comparable_tenders: List[Tender], 
                                    risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze bid spread anomalies"""
        
        if len(tender.bids) < 2:
            return {"analysis": "insufficient_bids_for_spread"}
        
        # Calculate bid spread for current tender
        bid_amounts = [float(bid.bid_amount) for bid in tender.bids if bid.bid_amount]
        
        if len(bid_amounts) < 2:
            return {"analysis": "insufficient_valid_bids"}
        
        tender_spread = max(bid_amounts) - min(bid_amounts)
        tender_spread_pct = (tender_spread / min(bid_amounts)) * 100 if min(bid_amounts) > 0 else 0
        
        # Get spreads from comparable tenders
        comparable_spreads = []
        comparable_spreads_pct = []
        
        for comp_tender in comparable_tenders:
            comp_bid_amounts = [float(bid.bid_amount) for bid in comp_tender.bids if bid.bid_amount]
            if len(comp_bid_amounts) >= 2:
                comp_spread = max(comp_bid_amounts) - min(comp_bid_amounts)
                comp_spread_pct = (comp_spread / min(comp_bid_amounts)) * 100 if min(comp_bid_amounts) > 0 else 0
                comparable_spreads.append(comp_spread)
                comparable_spreads_pct.append(comp_spread_pct)
        
        if len(comparable_spreads) < 3:
            return {"analysis": "insufficient_comparable_spreads"}
        
        # Statistical analysis
        mean_spread = np.mean(comparable_spreads_pct)
        std_spread = np.std(comparable_spreads_pct)
        
        spread_z_score = self.calculate_z_score(tender_spread_pct, mean_spread, std_spread)
        
        analysis = {
            "tender_spread": tender_spread,
            "tender_spread_pct": tender_spread_pct,
            "mean_spread_pct": mean_spread,
            "std_spread_pct": std_spread,
            "spread_z_score": spread_z_score,
            "bid_count": len(bid_amounts),
            "comparable_count": len(comparable_spreads)
        }
        
        # Low spread might indicate collusion
        if spread_z_score > self.config.price_anomaly_z_threshold and tender_spread_pct < mean_spread:
            risk_factors["unusually_low_bid_spread"] = True
        
        return analysis
    
    def _calculate_isolation_score(self, target_values: List[float], 
                                 reference_values: List[float]) -> float:
        """Calculate isolation forest anomaly score"""
        
        try:
            # Combine target and reference values
            all_values = np.array(reference_values + target_values).reshape(-1, 1)
            
            # Fit isolation forest
            isolation_forest = IsolationForest(contamination=0.1, random_state=42)
            isolation_forest.fit(all_values)
            
            # Score the target values
            target_array = np.array(target_values).reshape(-1, 1)
            scores = isolation_forest.decision_function(target_array)
            
            # Convert to anomaly score (higher = more anomalous)
            return float(1 - scores[0]) if len(scores) > 0 else 0.0
            
        except Exception as e:
            self.logger.warning(f"Isolation forest calculation failed: {e}")
            return 0.0
    
    def _calculate_price_anomaly_risk_score(self, estimated_analysis: Dict[str, Any],
                                          winning_analysis: Dict[str, Any],
                                          spread_analysis: Dict[str, Any],
                                          risk_factors: Dict[str, Any]) -> float:
        """Calculate combined price anomaly risk score"""
        
        score = 0.0
        
        # Estimated value anomalies
        if estimated_analysis.get("z_score", 0) > self.config.price_anomaly_z_threshold:
            score += 30.0
        
        if estimated_analysis.get("isolation_score", 0) > self.config.price_anomaly_isolation_threshold:
            score += 25.0
        
        if estimated_analysis.get("is_outlier_iqr", False):
            score += 20.0
        
        # Winning bid anomalies
        if winning_analysis.get("z_score", 0) > self.config.price_anomaly_z_threshold:
            score += 35.0
        
        if winning_analysis.get("isolation_score", 0) > self.config.price_anomaly_isolation_threshold:
            score += 30.0
        
        # Bid-to-estimate ratio anomalies
        ratio_analysis = winning_analysis.get("ratio_analysis", {})
        if ratio_analysis.get("ratio_z_score", 0) > self.config.price_anomaly_z_threshold:
            score += 25.0
        
        # Bid spread anomalies
        if spread_analysis.get("spread_z_score", 0) > self.config.price_anomaly_z_threshold:
            score += 20.0
        
        return min(100.0, score)
    
    def _generate_price_anomaly_flags(self, estimated_analysis: Dict[str, Any],
                                    winning_analysis: Dict[str, Any],
                                    spread_analysis: Dict[str, Any],
                                    risk_factors: Dict[str, Any]) -> List[str]:
        """Generate risk flags for price anomalies"""
        
        flags = []
        
        if risk_factors.get("high_z_score_estimated"):
            flags.append("ESTIMATED_VALUE_STATISTICAL_ANOMALY")
        
        if risk_factors.get("isolation_anomaly_estimated"):
            flags.append("ESTIMATED_VALUE_ISOLATION_ANOMALY")
        
        if risk_factors.get("iqr_outlier_estimated"):
            flags.append("ESTIMATED_VALUE_OUTLIER")
        
        if risk_factors.get("high_z_score_winning"):
            flags.append("WINNING_BID_STATISTICAL_ANOMALY")
        
        if risk_factors.get("isolation_anomaly_winning"):
            flags.append("WINNING_BID_ISOLATION_ANOMALY")
        
        if risk_factors.get("anomalous_bid_to_estimate_ratio"):
            flags.append("ANOMALOUS_BID_TO_ESTIMATE_RATIO")
        
        if risk_factors.get("unusually_low_bid_spread"):
            flags.append("UNUSUALLY_LOW_BID_SPREAD")
        
        return flags
    
    def _analyze_cpv_batch(self, group_df: pd.DataFrame, all_tenders: List[Tender], 
                          db: Session) -> List[RiskDetectionResult]:
        """Analyze a batch of tenders with same CPV code"""
        
        results = []
        group_tenders = [t for t in all_tenders if str(t.id) in group_df['id'].values]
        
        for tender in group_tenders:
            result = self.analyze_tender(tender, db)
            results.append(result)
        
        return results
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm"""
        return {
            "name": self.algorithm_name,
            "version": self.algorithm_version,
            "description": "Detects unusual pricing patterns using statistical analysis and machine learning",
            "risk_factors": [
                "Estimated value anomalies",
                "Winning bid anomalies", 
                "Bid-to-estimate ratio anomalies",
                "Bid spread anomalies",
                "Statistical outliers (z-score, IQR)",
                "Isolation forest anomalies"
            ],
            "parameters": {
                "z_threshold": self.config.price_anomaly_z_threshold,
                "isolation_threshold": self.config.price_anomaly_isolation_threshold,
                "weight": self.config.price_anomaly_weight,
                "min_sample_size": self.config.min_sample_size_price_analysis
            }
        }