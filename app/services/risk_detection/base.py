"""
Base classes and utilities for risk detection algorithms
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.db.models import Tender, TenderRiskScore
import logging

logger = logging.getLogger(__name__)


class RiskDetectionConfig:
    """Configuration for risk detection algorithms"""
    
    def __init__(self):
        # Single Bidder Detection
        self.single_bidder_threshold = 0.8
        self.single_bidder_weight = 0.25
        
        # Price Anomaly Detection
        self.price_anomaly_z_threshold = 2.0
        self.price_anomaly_isolation_threshold = 0.1
        self.price_anomaly_weight = 0.30
        
        # Frequent Winner Detection
        self.frequent_winner_threshold = 0.7
        self.frequent_winner_weight = 0.25
        
        # Geographic Clustering
        self.geographic_clustering_threshold = 0.6
        self.geographic_clustering_weight = 0.20
        
        # Overall scoring
        self.high_risk_threshold = 70.0
        self.medium_risk_threshold = 40.0
        self.low_risk_threshold = 20.0
        
        # Minimum sample sizes
        self.min_sample_size_price_analysis = 10
        self.min_sample_size_frequency_analysis = 5
        self.min_sample_size_geographic_analysis = 3
        
        # Time windows for analysis
        self.analysis_window_months = 12
        self.historical_data_years = 3


class RiskDetectionResult:
    """Result of a risk detection analysis"""
    
    def __init__(self, 
                 risk_score: float,
                 risk_level: str,
                 risk_flags: List[str],
                 detailed_analysis: Dict[str, Any],
                 confidence: float = 1.0):
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.risk_flags = risk_flags
        self.detailed_analysis = detailed_analysis
        self.confidence = confidence
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_flags": self.risk_flags,
            "detailed_analysis": self.detailed_analysis,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class BaseRiskDetector(ABC):
    """Base class for all risk detection algorithms"""
    
    def __init__(self, config: RiskDetectionConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Analyze a single tender for risk factors"""
        pass
    
    @abstractmethod
    def analyze_batch(self, tenders: List[Tender], db: Session) -> List[RiskDetectionResult]:
        """Analyze multiple tenders for risk factors"""
        pass
    
    @abstractmethod
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm"""
        pass
    
    def normalize_score(self, score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Normalize score to 0-100 range"""
        if max_val == min_val:
            return 0.0
        normalized = (score - min_val) / (max_val - min_val)
        return max(0.0, min(100.0, normalized * 100.0))
    
    def calculate_z_score(self, value: float, mean: float, std: float) -> float:
        """Calculate z-score for a value"""
        if std == 0:
            return 0.0
        return abs(value - mean) / std
    
    def get_risk_level(self, score: float) -> str:
        """Get risk level based on score"""
        if score >= self.config.high_risk_threshold:
            return "HIGH"
        elif score >= self.config.medium_risk_threshold:
            return "MEDIUM"
        elif score >= self.config.low_risk_threshold:
            return "LOW"
        else:
            return "MINIMAL"
    
    def log_analysis(self, tender_id: str, analysis_type: str, result: RiskDetectionResult):
        """Log analysis result"""
        self.logger.info(
            f"Risk analysis completed",
            extra={
                "tender_id": tender_id,
                "analysis_type": analysis_type,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "flags_count": len(result.risk_flags)
            }
        )


class RiskAnalysisCache:
    """Cache for risk analysis results"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return eval(cached_data)  # In production, use proper JSON deserialization
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache analysis result"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                str(result)  # In production, use proper JSON serialization
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")


class RiskAnalysisUtils:
    """Utility functions for risk analysis"""
    
    @staticmethod
    def convert_to_dataframe(tenders: List[Tender]) -> pd.DataFrame:
        """Convert list of tenders to pandas DataFrame"""
        data = []
        for tender in tenders:
            data.append({
                'id': str(tender.id),
                'contracting_authority_id': tender.contracting_authority_id,
                'estimated_value': float(tender.estimated_value) if tender.estimated_value else None,
                'publication_date': tender.publication_date,
                'submission_deadline': tender.submission_deadline,
                'cpv_code': tender.cpv_code,
                'tender_type': tender.tender_type,
                'procedure_type': tender.procedure_type,
                'status': tender.status,
                'county': tender.contracting_authority.county if tender.contracting_authority else None,
                'city': tender.contracting_authority.city if tender.contracting_authority else None,
                'bid_count': len(tender.bids),
                'has_winner': any(bid.is_winner for bid in tender.bids),
                'winning_amount': None
            })
            
            # Get winning bid amount
            winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
            if winning_bid:
                data[-1]['winning_amount'] = float(winning_bid.bid_amount) if winning_bid.bid_amount else None
        
        return pd.DataFrame(data)
    
    @staticmethod
    def filter_valid_values(df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Filter DataFrame to only include rows with valid values in specified column"""
        return df[df[column].notna() & (df[column] > 0)]
    
    @staticmethod
    def calculate_outliers_iqr(values: np.ndarray) -> Tuple[float, float]:
        """Calculate outlier bounds using IQR method"""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        return lower_bound, upper_bound
    
    @staticmethod
    def calculate_market_concentration(winners: List[str]) -> float:
        """Calculate market concentration using Herfindahl-Hirschman Index"""
        if not winners:
            return 0.0
        
        # Count occurrences of each winner
        winner_counts = {}
        for winner in winners:
            winner_counts[winner] = winner_counts.get(winner, 0) + 1
        
        # Calculate market shares
        total_contracts = len(winners)
        market_shares = [count / total_contracts for count in winner_counts.values()]
        
        # Calculate HHI
        hhi = sum(share ** 2 for share in market_shares)
        return hhi