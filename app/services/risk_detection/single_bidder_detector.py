"""
Single Bidder Detection Algorithm

This module implements risk detection for tenders with only one bidder,
which can indicate potential manipulation or insufficient competition.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import numpy as np

from app.db.models import Tender, TenderBid, ContractingAuthority, CPVCode
from .base import BaseRiskDetector, RiskDetectionResult, RiskDetectionConfig


class SingleBidderDetector(BaseRiskDetector):
    """Detector for single bidder risk patterns"""
    
    def __init__(self, config: RiskDetectionConfig):
        super().__init__(config)
        self.algorithm_name = "Single Bidder Detection"
        self.algorithm_version = "1.0.0"
    
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Analyze a single tender for single bidder risk"""
        
        # Basic single bidder check
        bid_count = len(tender.bids)
        
        if bid_count == 0:
            return RiskDetectionResult(
                risk_score=0.0,
                risk_level="MINIMAL",
                risk_flags=["NO_BIDS"],
                detailed_analysis={
                    "bid_count": bid_count,
                    "algorithm": self.algorithm_name,
                    "analysis_type": "single_tender"
                }
            )
        
        risk_flags = []
        risk_factors = {}
        
        # Check if only one bidder
        if bid_count == 1:
            risk_flags.append("SINGLE_BIDDER")
            risk_factors["single_bidder"] = True
        else:
            risk_factors["single_bidder"] = False
        
        # Get historical context for this contracting authority
        historical_context = self._get_historical_context(tender, db)
        
        # Calculate risk score based on multiple factors
        risk_score = self._calculate_single_bidder_risk_score(
            tender, bid_count, historical_context, risk_factors
        )
        
        # Add contextual risk flags
        if historical_context:
            risk_flags.extend(self._analyze_historical_patterns(
                tender, historical_context, risk_factors
            ))
        
        detailed_analysis = {
            "bid_count": bid_count,
            "historical_context": historical_context,
            "risk_factors": risk_factors,
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
        """Analyze multiple tenders for single bidder patterns"""
        results = []
        
        # Get overall statistics for better contextualization
        overall_stats = self._get_overall_statistics(tenders, db)
        
        for tender in tenders:
            result = self.analyze_tender(tender, db)
            
            # Enhance with batch context
            result.detailed_analysis["batch_stats"] = overall_stats
            
            results.append(result)
        
        return results
    
    def _get_historical_context(self, tender: Tender, db: Session) -> Dict[str, Any]:
        """Get historical context for the contracting authority"""
        
        # Get tenders from same authority in last 12 months
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        historical_tenders = db.query(Tender).filter(
            and_(
                Tender.contracting_authority_id == tender.contracting_authority_id,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        ).all()
        
        if not historical_tenders:
            return {}
        
        # Calculate statistics
        total_historical = len(historical_tenders)
        single_bidder_count = 0
        bid_counts = []
        
        for hist_tender in historical_tenders:
            bid_count = len(hist_tender.bids)
            bid_counts.append(bid_count)
            if bid_count == 1:
                single_bidder_count += 1
        
        single_bidder_rate = single_bidder_count / total_historical if total_historical > 0 else 0
        avg_bid_count = np.mean(bid_counts) if bid_counts else 0
        
        # Get CPV-specific context
        cpv_context = self._get_cpv_context(tender, db)
        
        return {
            "total_historical_tenders": total_historical,
            "single_bidder_count": single_bidder_count,
            "single_bidder_rate": single_bidder_rate,
            "average_bid_count": avg_bid_count,
            "cpv_context": cpv_context
        }
    
    def _get_cpv_context(self, tender: Tender, db: Session) -> Dict[str, Any]:
        """Get context for the same CPV code"""
        
        if not tender.cpv_code:
            return {}
        
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        cpv_tenders = db.query(Tender).filter(
            and_(
                Tender.cpv_code == tender.cpv_code,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        ).all()
        
        if not cpv_tenders:
            return {}
        
        cpv_bid_counts = [len(t.bids) for t in cpv_tenders]
        cpv_single_bidder_count = sum(1 for count in cpv_bid_counts if count == 1)
        
        return {
            "cpv_code": tender.cpv_code,
            "cpv_total_tenders": len(cpv_tenders),
            "cpv_single_bidder_count": cpv_single_bidder_count,
            "cpv_single_bidder_rate": cpv_single_bidder_count / len(cpv_tenders),
            "cpv_avg_bid_count": np.mean(cpv_bid_counts) if cpv_bid_counts else 0
        }
    
    def _calculate_single_bidder_risk_score(self, tender: Tender, bid_count: int, 
                                          historical_context: Dict[str, Any], 
                                          risk_factors: Dict[str, Any]) -> float:
        """Calculate risk score for single bidder detection"""
        
        base_score = 0.0
        
        # Base score for single bidder
        if bid_count == 1:
            base_score = 60.0  # High base risk for single bidder
        elif bid_count == 2:
            base_score = 25.0  # Medium risk for only 2 bidders
        elif bid_count == 3:
            base_score = 10.0  # Low risk for 3 bidders
        else:
            base_score = 0.0   # No risk for 4+ bidders
        
        # Adjust based on historical context
        if historical_context:
            authority_single_rate = historical_context.get("single_bidder_rate", 0)
            
            # If authority frequently has single bidders, increase risk
            if authority_single_rate > 0.5:
                base_score *= 1.5
                risk_factors["frequent_single_bidder_authority"] = True
            elif authority_single_rate > 0.3:
                base_score *= 1.2
                risk_factors["elevated_single_bidder_authority"] = True
            
            # CPV context adjustment
            cpv_context = historical_context.get("cpv_context", {})
            if cpv_context:
                cpv_single_rate = cpv_context.get("cpv_single_bidder_rate", 0)
                
                # If this CPV category typically has more bidders, increase risk
                if cpv_single_rate < 0.2 and bid_count == 1:
                    base_score *= 1.3
                    risk_factors["atypical_for_cpv"] = True
        
        # Adjust for estimated value
        if tender.estimated_value:
            value = float(tender.estimated_value)
            
            # Higher value contracts with single bidder are more suspicious
            if value > 1000000 and bid_count == 1:  # 1M RON threshold
                base_score *= 1.4
                risk_factors["high_value_single_bidder"] = True
            elif value > 500000 and bid_count == 1:  # 500K RON threshold
                base_score *= 1.2
                risk_factors["medium_value_single_bidder"] = True
        
        # Adjust for tender type
        if tender.tender_type in ["OPEN", "RESTRICTED"]:
            # Open procedures with single bidder are more suspicious
            if bid_count == 1:
                base_score *= 1.3
                risk_factors["open_procedure_single_bidder"] = True
        
        return min(100.0, base_score)
    
    def _analyze_historical_patterns(self, tender: Tender, historical_context: Dict[str, Any], 
                                   risk_factors: Dict[str, Any]) -> List[str]:
        """Analyze historical patterns for additional risk flags"""
        
        flags = []
        
        authority_single_rate = historical_context.get("single_bidder_rate", 0)
        
        if authority_single_rate > 0.7:
            flags.append("CHRONIC_SINGLE_BIDDER_AUTHORITY")
        elif authority_single_rate > 0.5:
            flags.append("FREQUENT_SINGLE_BIDDER_AUTHORITY")
        
        # Check CPV patterns
        cpv_context = historical_context.get("cpv_context", {})
        if cpv_context:
            cpv_single_rate = cpv_context.get("cpv_single_bidder_rate", 0)
            
            if cpv_single_rate < 0.1 and len(tender.bids) == 1:
                flags.append("ATYPICAL_SINGLE_BIDDER_FOR_CPV")
        
        return flags
    
    def _get_overall_statistics(self, tenders: List[Tender], db: Session) -> Dict[str, Any]:
        """Get overall statistics for the batch"""
        
        if not tenders:
            return {}
        
        bid_counts = [len(tender.bids) for tender in tenders]
        single_bidder_count = sum(1 for count in bid_counts if count == 1)
        
        return {
            "total_tenders": len(tenders),
            "single_bidder_count": single_bidder_count,
            "single_bidder_rate": single_bidder_count / len(tenders),
            "average_bid_count": np.mean(bid_counts) if bid_counts else 0,
            "median_bid_count": np.median(bid_counts) if bid_counts else 0
        }
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm"""
        return {
            "name": self.algorithm_name,
            "version": self.algorithm_version,
            "description": "Detects tenders with suspiciously few bidders, particularly single bidder situations",
            "risk_factors": [
                "Single bidder tenders",
                "Historical single bidder patterns",
                "CPV category context",
                "Tender value considerations",
                "Procedure type analysis"
            ],
            "parameters": {
                "single_bidder_threshold": self.config.single_bidder_threshold,
                "weight": self.config.single_bidder_weight,
                "analysis_window_months": self.config.analysis_window_months
            }
        }