# Risk Detection Algorithms Design

## Overview

The risk detection system implements algorithms to identify potential corruption indicators and procurement anomalies in Romanian public tenders. Based on the requirements, we focus on four primary risk categories: single bidder tenders, unusual pricing patterns, frequent winner patterns, and geographic clustering.

## Risk Detection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RISK DETECTION PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   DATA INPUT    │  │   ALGORITHM     │  │   RISK SCORING  │ │
│  │                 │  │   PROCESSING    │  │                 │ │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │ │
│  │  │New Tender │  │  │  │Single     │  │  │  │Score      │  │ │
│  │  │Data       │  │  │  │Bidder     │  │  │  │Calculation│  │ │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │ │
│  │                 │  │                 │  │                 │ │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │ │
│  │  │Historical │  │  │  │Price      │  │  │  │Risk       │  │ │
│  │  │Data       │  │  │  │Anomaly    │  │  │  │Level      │  │ │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │ │
│  │                 │  │                 │  │                 │ │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │ │
│  │  │Company    │  │  │  │Frequency  │  │  │  │Alert      │  │ │
│  │  │Profiles   │  │  │  │Analysis   │  │  │  │Generation │  │ │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │ │
│  │                 │  │                 │  │                 │ │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │ │
│  │  │Geographic │  │  │  │Geographic │  │  │  │Pattern    │  │ │
│  │  │Data       │  │  │  │Clustering │  │  │  │Detection  │  │ │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Risk Algorithm Implementations

### 1. Single Bidder Risk Detection

```python
class SingleBidderRiskDetector:
    def __init__(self):
        self.risk_thresholds = {
            "single_bidder_base_score": 75.0,
            "high_value_threshold": 500000,  # RON
            "critical_cpv_codes": ["45000000", "72000000", "79000000"],  # Construction, IT, Business services
            "repeat_authority_threshold": 3  # Authority with 3+ single bidder tenders
        }
        
    def analyze_tender_risk(self, tender_id: str) -> dict:
        """Analyze single bidder risk for a tender"""
        tender = self.get_tender_data(tender_id)
        bids = self.get_tender_bids(tender_id)
        
        risk_score = 0.0
        risk_factors = []
        
        # Base single bidder risk
        if len(bids) == 1:
            risk_score = self.risk_thresholds["single_bidder_base_score"]
            risk_factors.append("single_bidder")
            
            # High value tender increases risk
            if tender.estimated_value > self.risk_thresholds["high_value_threshold"]:
                risk_score += 15.0
                risk_factors.append("high_value_single_bidder")
                
            # Critical CPV codes increase risk
            if tender.cpv_code in self.risk_thresholds["critical_cpv_codes"]:
                risk_score += 10.0
                risk_factors.append("critical_sector_single_bidder")
                
            # Authority pattern analysis
            authority_single_bidder_count = self.count_authority_single_bidder_tenders(
                tender.contracting_authority_id, 
                days_back=365
            )
            
            if authority_single_bidder_count >= self.risk_thresholds["repeat_authority_threshold"]:
                risk_score += 20.0
                risk_factors.append("repeat_authority_single_bidder")
                
        return {
            "risk_score": min(risk_score, 100.0),
            "risk_factors": risk_factors,
            "algorithm": "single_bidder_detection",
            "analysis_details": {
                "bid_count": len(bids),
                "tender_value": tender.estimated_value,
                "cpv_code": tender.cpv_code,
                "authority_single_bidder_history": authority_single_bidder_count
            }
        }
        
    def count_authority_single_bidder_tenders(self, authority_id: int, days_back: int) -> int:
        """Count single bidder tenders for an authority in the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = """
        SELECT COUNT(*)
        FROM tenders t
        WHERE t.contracting_authority_id = :authority_id
        AND t.publication_date >= :cutoff_date
        AND (
            SELECT COUNT(*)
            FROM tender_bids tb
            WHERE tb.tender_id = t.id
        ) = 1
        """
        
        result = self.db.execute(query, {
            "authority_id": authority_id,
            "cutoff_date": cutoff_date
        })
        
        return result.scalar() or 0
```

### 2. Price Anomaly Detection

```python
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest

class PriceAnomalyDetector:
    def __init__(self):
        self.anomaly_thresholds = {
            "z_score_threshold": 2.5,
            "isolation_forest_contamination": 0.1,
            "min_historical_samples": 10,
            "price_deviation_threshold": 0.3  # 30% deviation
        }
        
    def analyze_price_anomaly(self, tender_id: str) -> dict:
        """Analyze price anomalies for a tender"""
        tender = self.get_tender_data(tender_id)
        bids = self.get_tender_bids(tender_id)
        
        if not bids:
            return self.create_empty_result()
            
        # Get historical data for comparison
        historical_data = self.get_historical_price_data(
            cpv_code=tender.cpv_code,
            contracting_authority_id=tender.contracting_authority_id,
            days_back=730  # 2 years
        )
        
        risk_score = 0.0
        risk_factors = []
        analysis_details = {}
        
        # 1. Statistical outlier detection
        if len(historical_data) >= self.anomaly_thresholds["min_historical_samples"]:
            outlier_analysis = self.detect_statistical_outliers(bids, historical_data)
            risk_score += outlier_analysis["risk_score"]
            risk_factors.extend(outlier_analysis["risk_factors"])
            analysis_details.update(outlier_analysis["details"])
            
        # 2. Bid spread analysis
        if len(bids) > 1:
            spread_analysis = self.analyze_bid_spread(bids)
            risk_score += spread_analysis["risk_score"]
            risk_factors.extend(spread_analysis["risk_factors"])
            analysis_details.update(spread_analysis["details"])
            
        # 3. Winner price analysis
        winner_analysis = self.analyze_winner_price(bids, tender.estimated_value)
        risk_score += winner_analysis["risk_score"]
        risk_factors.extend(winner_analysis["risk_factors"])
        analysis_details.update(winner_analysis["details"])
        
        return {
            "risk_score": min(risk_score, 100.0),
            "risk_factors": risk_factors,
            "algorithm": "price_anomaly_detection",
            "analysis_details": analysis_details
        }
        
    def detect_statistical_outliers(self, bids: List[dict], historical_data: List[dict]) -> dict:
        """Detect statistical outliers in bid prices"""
        if not historical_data:
            return {"risk_score": 0.0, "risk_factors": [], "details": {}}
            
        # Prepare data for analysis
        historical_prices = [item["price"] for item in historical_data]
        current_prices = [bid["bid_amount"] for bid in bids]
        
        # Calculate z-scores
        historical_mean = np.mean(historical_prices)
        historical_std = np.std(historical_prices)
        
        risk_score = 0.0
        risk_factors = []
        details = {
            "historical_mean": historical_mean,
            "historical_std": historical_std,
            "current_prices": current_prices
        }
        
        # Check for outliers
        for price in current_prices:
            z_score = abs((price - historical_mean) / historical_std) if historical_std > 0 else 0
            
            if z_score > self.anomaly_thresholds["z_score_threshold"]:
                if price < historical_mean:
                    risk_score += 25.0
                    risk_factors.append("unusually_low_price")
                else:
                    risk_score += 15.0
                    risk_factors.append("unusually_high_price")
                    
        # Isolation Forest for anomaly detection
        if len(historical_prices) >= 20:
            anomaly_score = self.isolation_forest_analysis(current_prices, historical_prices)
            if anomaly_score > 0.5:
                risk_score += 20.0
                risk_factors.append("price_pattern_anomaly")
                details["isolation_forest_score"] = anomaly_score
                
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "details": details
        }
        
    def isolation_forest_analysis(self, current_prices: List[float], historical_prices: List[float]) -> float:
        """Use Isolation Forest to detect price anomalies"""
        # Combine historical and current prices
        all_prices = np.array(historical_prices + current_prices).reshape(-1, 1)
        
        # Fit Isolation Forest
        iso_forest = IsolationForest(
            contamination=self.anomaly_thresholds["isolation_forest_contamination"],
            random_state=42
        )
        iso_forest.fit(all_prices)
        
        # Get anomaly scores for current prices
        current_prices_array = np.array(current_prices).reshape(-1, 1)
        anomaly_scores = iso_forest.decision_function(current_prices_array)
        
        # Return normalized anomaly score (0-1)
        return max(0, 1 - (np.mean(anomaly_scores) + 1) / 2)
        
    def analyze_bid_spread(self, bids: List[dict]) -> dict:
        """Analyze bid price spread for anomalies"""
        if len(bids) < 2:
            return {"risk_score": 0.0, "risk_factors": [], "details": {}}
            
        prices = [bid["bid_amount"] for bid in bids]
        prices.sort()
        
        risk_score = 0.0
        risk_factors = []
        
        # Calculate coefficient of variation
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        cv = std_price / mean_price if mean_price > 0 else 0
        
        details = {
            "bid_count": len(bids),
            "price_range": {"min": min(prices), "max": max(prices)},
            "coefficient_of_variation": cv,
            "spread_percentage": (max(prices) - min(prices)) / mean_price if mean_price > 0 else 0
        }
        
        # Very low spread might indicate bid coordination
        if cv < 0.05 and len(bids) > 2:
            risk_score += 30.0
            risk_factors.append("suspiciously_similar_bids")
            
        # Very high spread might indicate outliers
        if cv > 0.5:
            risk_score += 15.0
            risk_factors.append("unusual_bid_spread")
            
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "details": details
        }
```

### 3. Frequent Winner Pattern Detection

```python
class FrequentWinnerDetector:
    def __init__(self):
        self.pattern_thresholds = {
            "authority_win_threshold": 0.6,  # 60% win rate with same authority
            "sector_win_threshold": 0.4,     # 40% win rate in same sector
            "geographic_win_threshold": 0.5, # 50% win rate in same region
            "time_window_days": 365,         # Analysis window
            "min_tender_count": 5            # Minimum tenders to analyze
        }
        
    def analyze_frequent_winner_risk(self, tender_id: str) -> dict:
        """Analyze frequent winner patterns for a tender"""
        tender = self.get_tender_data(tender_id)
        winning_bid = self.get_winning_bid(tender_id)
        
        if not winning_bid:
            return self.create_empty_result()
            
        company_id = winning_bid.company_id
        
        risk_score = 0.0
        risk_factors = []
        analysis_details = {}
        
        # 1. Authority-specific win rate analysis
        authority_analysis = self.analyze_authority_win_rate(
            company_id, 
            tender.contracting_authority_id
        )
        risk_score += authority_analysis["risk_score"]
        risk_factors.extend(authority_analysis["risk_factors"])
        analysis_details.update(authority_analysis["details"])
        
        # 2. Sector-specific win rate analysis
        sector_analysis = self.analyze_sector_win_rate(
            company_id, 
            tender.cpv_code
        )
        risk_score += sector_analysis["risk_score"]
        risk_factors.extend(sector_analysis["risk_factors"])
        analysis_details.update(sector_analysis["details"])
        
        # 3. Geographic pattern analysis
        geographic_analysis = self.analyze_geographic_win_rate(
            company_id, 
            tender.contracting_authority_id
        )
        risk_score += geographic_analysis["risk_score"]
        risk_factors.extend(geographic_analysis["risk_factors"])
        analysis_details.update(geographic_analysis["details"])
        
        # 4. Temporal pattern analysis
        temporal_analysis = self.analyze_temporal_patterns(company_id)
        risk_score += temporal_analysis["risk_score"]
        risk_factors.extend(temporal_analysis["risk_factors"])
        analysis_details.update(temporal_analysis["details"])
        
        return {
            "risk_score": min(risk_score, 100.0),
            "risk_factors": risk_factors,
            "algorithm": "frequent_winner_detection",
            "analysis_details": analysis_details
        }
        
    def analyze_authority_win_rate(self, company_id: int, authority_id: int) -> dict:
        """Analyze company win rate with specific authority"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.pattern_thresholds["time_window_days"])
        
        # Get total tenders where company participated
        total_participations = self.count_company_participations(
            company_id, authority_id, cutoff_date
        )
        
        # Get total wins
        total_wins = self.count_company_wins(
            company_id, authority_id, cutoff_date
        )
        
        if total_participations < self.pattern_thresholds["min_tender_count"]:
            return {"risk_score": 0.0, "risk_factors": [], "details": {}}
            
        win_rate = total_wins / total_participations
        
        risk_score = 0.0
        risk_factors = []
        
        if win_rate >= self.pattern_thresholds["authority_win_threshold"]:
            risk_score += 40.0
            risk_factors.append("high_authority_win_rate")
            
        # Additional risk for very high win rates
        if win_rate >= 0.8:
            risk_score += 20.0
            risk_factors.append("extremely_high_authority_win_rate")
            
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "details": {
                "authority_win_rate": win_rate,
                "total_participations": total_participations,
                "total_wins": total_wins
            }
        }
        
    def analyze_sector_win_rate(self, company_id: int, cpv_code: str) -> dict:
        """Analyze company win rate in specific sector"""
        # Get CPV code prefix (first 2 digits for main category)
        cpv_prefix = cpv_code[:2] if len(cpv_code) >= 2 else cpv_code
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.pattern_thresholds["time_window_days"])
        
        # Get sector participation data
        sector_participations = self.count_sector_participations(
            company_id, cpv_prefix, cutoff_date
        )
        
        sector_wins = self.count_sector_wins(
            company_id, cpv_prefix, cutoff_date
        )
        
        if sector_participations < self.pattern_thresholds["min_tender_count"]:
            return {"risk_score": 0.0, "risk_factors": [], "details": {}}
            
        win_rate = sector_wins / sector_participations
        
        risk_score = 0.0
        risk_factors = []
        
        if win_rate >= self.pattern_thresholds["sector_win_threshold"]:
            risk_score += 25.0
            risk_factors.append("high_sector_win_rate")
            
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "details": {
                "sector_win_rate": win_rate,
                "sector_participations": sector_participations,
                "sector_wins": sector_wins,
                "cpv_prefix": cpv_prefix
            }
        }
        
    def analyze_temporal_patterns(self, company_id: int) -> dict:
        """Analyze temporal patterns in company wins"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.pattern_thresholds["time_window_days"])
        
        # Get monthly win distribution
        monthly_wins = self.get_monthly_win_distribution(company_id, cutoff_date)
        
        risk_score = 0.0
        risk_factors = []
        
        if monthly_wins:
            # Calculate coefficient of variation for monthly wins
            wins_array = np.array(list(monthly_wins.values()))
            mean_wins = np.mean(wins_array)
            std_wins = np.std(wins_array)
            cv = std_wins / mean_wins if mean_wins > 0 else 0
            
            # Very consistent monthly wins might indicate patterns
            if cv < 0.3 and mean_wins > 1:
                risk_score += 15.0
                risk_factors.append("consistent_monthly_wins")
                
            # Sudden spikes in wins
            max_wins = np.max(wins_array)
            if max_wins > mean_wins + 2 * std_wins:
                risk_score += 10.0
                risk_factors.append("win_concentration_spike")
                
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "details": {
                "monthly_wins": monthly_wins,
                "temporal_coefficient_variation": cv if 'cv' in locals() else 0
            }
        }
```

### 4. Geographic Clustering Detection

```python
class GeographicClusteringDetector:
    def __init__(self):
        self.clustering_thresholds = {
            "radius_km": 50,              # 50km radius for clustering
            "min_cluster_size": 3,        # Minimum tenders in cluster
            "cluster_win_threshold": 0.7, # 70% win rate in cluster
            "time_window_days": 365       # Analysis window
        }
        
    def analyze_geographic_clustering(self, tender_id: str) -> dict:
        """Analyze geographic clustering patterns"""
        tender = self.get_tender_data(tender_id)
        winning_bid = self.get_winning_bid(tender_id)
        
        if not winning_bid:
            return self.create_empty_result()
            
        company_id = winning_bid.company_id
        authority_location = self.get_authority_location(tender.contracting_authority_id)
        
        if not authority_location:
            return self.create_empty_result()
            
        risk_score = 0.0
        risk_factors = []
        analysis_details = {}
        
        # 1. Find nearby authorities
        nearby_authorities = self.find_nearby_authorities(
            authority_location, 
            self.clustering_thresholds["radius_km"]
        )
        
        # 2. Analyze company performance in geographic cluster
        cluster_analysis = self.analyze_cluster_performance(
            company_id, 
            nearby_authorities
        )
        
        if cluster_analysis["total_tenders"] >= self.clustering_thresholds["min_cluster_size"]:
            win_rate = cluster_analysis["wins"] / cluster_analysis["total_tenders"]
            
            if win_rate >= self.clustering_thresholds["cluster_win_threshold"]:
                risk_score += 35.0
                risk_factors.append("high_geographic_cluster_win_rate")
                
            # Additional risk for very high clustering
            if win_rate >= 0.9:
                risk_score += 25.0
                risk_factors.append("geographic_monopoly_pattern")
                
        # 3. Distance analysis
        distance_analysis = self.analyze_company_authority_distance(
            company_id, 
            tender.contracting_authority_id
        )
        risk_score += distance_analysis["risk_score"]
        risk_factors.extend(distance_analysis["risk_factors"])
        
        analysis_details.update({
            "cluster_performance": cluster_analysis,
            "distance_analysis": distance_analysis["details"],
            "nearby_authorities_count": len(nearby_authorities)
        })
        
        return {
            "risk_score": min(risk_score, 100.0),
            "risk_factors": risk_factors,
            "algorithm": "geographic_clustering_detection",
            "analysis_details": analysis_details
        }
        
    def find_nearby_authorities(self, center_location: dict, radius_km: float) -> List[int]:
        """Find authorities within specified radius"""
        # Using Haversine formula for distance calculation
        query = """
        SELECT id, latitude, longitude
        FROM contracting_authorities
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
        
        authorities = self.db.execute(query).fetchall()
        nearby_authorities = []
        
        for authority in authorities:
            distance = self.calculate_distance(
                center_location["latitude"], center_location["longitude"],
                authority.latitude, authority.longitude
            )
            
            if distance <= radius_km:
                nearby_authorities.append(authority.id)
                
        return nearby_authorities
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
        
    def analyze_cluster_performance(self, company_id: int, authority_ids: List[int]) -> dict:
        """Analyze company performance in geographic cluster"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.clustering_thresholds["time_window_days"])
        
        query = """
        SELECT 
            COUNT(*) as total_tenders,
            SUM(CASE WHEN tb.is_winner = true THEN 1 ELSE 0 END) as wins
        FROM tender_bids tb
        JOIN tenders t ON tb.tender_id = t.id
        WHERE tb.company_id = :company_id
        AND t.contracting_authority_id = ANY(:authority_ids)
        AND t.publication_date >= :cutoff_date
        """
        
        result = self.db.execute(query, {
            "company_id": company_id,
            "authority_ids": authority_ids,
            "cutoff_date": cutoff_date
        }).fetchone()
        
        return {
            "total_tenders": result.total_tenders or 0,
            "wins": result.wins or 0
        }
```

## Risk Score Calculation

### 1. Composite Risk Score

```python
class RiskScoreCalculator:
    def __init__(self):
        self.algorithm_weights = {
            "single_bidder_detection": 0.3,
            "price_anomaly_detection": 0.25,
            "frequent_winner_detection": 0.25,
            "geographic_clustering_detection": 0.2
        }
        
        self.risk_level_thresholds = {
            "low": 0,
            "medium": 30,
            "high": 60,
            "critical": 80
        }
        
    def calculate_composite_risk_score(self, tender_id: str) -> dict:
        """Calculate composite risk score for a tender"""
        # Run all risk detection algorithms
        single_bidder_result = SingleBidderRiskDetector().analyze_tender_risk(tender_id)
        price_anomaly_result = PriceAnomalyDetector().analyze_price_anomaly(tender_id)
        frequent_winner_result = FrequentWinnerDetector().analyze_frequent_winner_risk(tender_id)
        geographic_result = GeographicClusteringDetector().analyze_geographic_clustering(tender_id)
        
        # Calculate weighted score
        weighted_score = (
            single_bidder_result["risk_score"] * self.algorithm_weights["single_bidder_detection"] +
            price_anomaly_result["risk_score"] * self.algorithm_weights["price_anomaly_detection"] +
            frequent_winner_result["risk_score"] * self.algorithm_weights["frequent_winner_detection"] +
            geographic_result["risk_score"] * self.algorithm_weights["geographic_clustering_detection"]
        )
        
        # Collect all risk factors
        all_risk_factors = (
            single_bidder_result["risk_factors"] +
            price_anomaly_result["risk_factors"] +
            frequent_winner_result["risk_factors"] +
            geographic_result["risk_factors"]
        )
        
        # Determine risk level
        risk_level = self.determine_risk_level(weighted_score)
        
        return {
            "overall_risk_score": weighted_score,
            "risk_level": risk_level,
            "single_bidder_risk": single_bidder_result["risk_score"],
            "price_anomaly_risk": price_anomaly_result["risk_score"],
            "frequency_risk": frequent_winner_result["risk_score"],
            "geographic_risk": geographic_result["risk_score"],
            "risk_factors": all_risk_factors,
            "detailed_analysis": {
                "single_bidder": single_bidder_result,
                "price_anomaly": price_anomaly_result,
                "frequent_winner": frequent_winner_result,
                "geographic_clustering": geographic_result
            }
        }
        
    def determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= self.risk_level_thresholds["critical"]:
            return "critical"
        elif score >= self.risk_level_thresholds["high"]:
            return "high"
        elif score >= self.risk_level_thresholds["medium"]:
            return "medium"
        else:
            return "low"
```

## Risk Pattern Analysis

### 1. Pattern Detection Engine

```python
class RiskPatternDetector:
    def __init__(self):
        self.pattern_detectors = {
            "company_monopoly": self.detect_company_monopoly,
            "authority_favoritism": self.detect_authority_favoritism,
            "sector_concentration": self.detect_sector_concentration,
            "temporal_clustering": self.detect_temporal_clustering
        }
        
    def detect_patterns(self, time_window_days: int = 365) -> List[dict]:
        """Detect risk patterns across all tenders"""
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        patterns = []
        
        for pattern_name, detector_func in self.pattern_detectors.items():
            pattern_results = detector_func(cutoff_date)
            patterns.extend(pattern_results)
            
        return patterns
        
    def detect_company_monopoly(self, cutoff_date: datetime) -> List[dict]:
        """Detect companies with monopolistic patterns"""
        query = """
        SELECT 
            c.id,
            c.name,
            ca.name as authority_name,
            COUNT(*) as total_wins,
            SUM(ta.awarded_amount) as total_value
        FROM companies c
        JOIN tender_bids tb ON c.id = tb.company_id
        JOIN tenders t ON tb.tender_id = t.id
        JOIN contracting_authorities ca ON t.contracting_authority_id = ca.id
        JOIN tender_awards ta ON tb.id = ta.winning_bid_id
        WHERE tb.is_winner = true
        AND t.publication_date >= :cutoff_date
        GROUP BY c.id, c.name, ca.id, ca.name
        HAVING COUNT(*) >= 5
        AND COUNT(*) > (
            SELECT COUNT(*) * 0.6
            FROM tenders t2
            WHERE t2.contracting_authority_id = ca.id
            AND t2.publication_date >= :cutoff_date
        )
        """
        
        results = self.db.execute(query, {"cutoff_date": cutoff_date}).fetchall()
        patterns = []
        
        for result in results:
            patterns.append({
                "pattern_type": "company_monopoly",
                "company_id": result.id,
                "company_name": result.name,
                "authority_name": result.authority_name,
                "pattern_score": min(result.total_wins * 10, 100),
                "details": {
                    "total_wins": result.total_wins,
                    "total_value": result.total_value
                }
            })
            
        return patterns
```

## Risk Alert System

### 1. Alert Generation

```python
class RiskAlertGenerator:
    def __init__(self):
        self.alert_thresholds = {
            "high_risk_tender": 60,
            "critical_risk_tender": 80,
            "pattern_detection": 70,
            "authority_risk_spike": 50
        }
        
    def generate_alerts(self, risk_analysis: dict, tender_id: str) -> List[dict]:
        """Generate risk alerts based on analysis"""
        alerts = []
        
        # High risk tender alert
        if risk_analysis["overall_risk_score"] >= self.alert_thresholds["high_risk_tender"]:
            alerts.append({
                "alert_type": "high_risk_tender",
                "severity": "high" if risk_analysis["overall_risk_score"] >= 80 else "medium",
                "tender_id": tender_id,
                "message": f"Tender shows high risk score: {risk_analysis['overall_risk_score']:.1f}",
                "risk_factors": risk_analysis["risk_factors"],
                "recommended_actions": self.get_recommended_actions(risk_analysis["risk_factors"])
            })
            
        # Specific algorithm alerts
        if risk_analysis["single_bidder_risk"] >= 75:
            alerts.append({
                "alert_type": "single_bidder_risk",
                "severity": "high",
                "tender_id": tender_id,
                "message": "Single bidder tender detected",
                "recommended_actions": ["Investigate market conditions", "Review tender specifications"]
            })
            
        return alerts
        
    def get_recommended_actions(self, risk_factors: List[str]) -> List[str]:
        """Get recommended actions based on risk factors"""
        actions = []
        
        if "single_bidder" in risk_factors:
            actions.append("Investigate market conditions and bidder eligibility")
            
        if "unusually_low_price" in risk_factors:
            actions.append("Review bid evaluation criteria and financial capacity")
            
        if "high_authority_win_rate" in risk_factors:
            actions.append("Audit contracting authority procedures")
            
        if "geographic_monopoly_pattern" in risk_factors:
            actions.append("Investigate regional market competition")
            
        return actions or ["General risk assessment recommended"]
```

## Performance Optimization

### 1. Caching Strategy

```python
class RiskAnalysisCache:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.cache_ttl = {
            "risk_score": 3600,      # 1 hour
            "historical_data": 86400, # 24 hours
            "pattern_analysis": 7200  # 2 hours
        }
        
    def get_cached_risk_score(self, tender_id: str) -> dict:
        """Get cached risk score"""
        cache_key = f"risk_score:{tender_id}"
        cached_data = self.redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
        
    def cache_risk_score(self, tender_id: str, risk_analysis: dict):
        """Cache risk analysis results"""
        cache_key = f"risk_score:{tender_id}"
        self.redis_client.setex(
            cache_key,
            self.cache_ttl["risk_score"],
            json.dumps(risk_analysis)
        )
```

This risk detection system provides comprehensive analysis capabilities for identifying potential corruption indicators in Romanian public procurement while maintaining high performance and accuracy through statistical analysis and pattern recognition.