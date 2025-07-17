"""
Trend Analyzer

This module analyzes trends in procurement risk patterns over time,
identifying emerging issues and tracking system performance.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict
import logging

from app.db.models import TenderRiskScore, Tender, ContractingAuthority, CPVCode

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends in procurement risk data"""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def analyze_risk_trends(self, db: Session, period_days: int = 90) -> Dict[str, Any]:
        """Analyze overall risk trends over time"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get risk scores over time
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).order_by(TenderRiskScore.analysis_date).all()
        
        if not risk_scores:
            return {
                "error": "No risk data available for the specified period",
                "period_days": period_days
            }
        
        # Group by time periods
        daily_trends = self._calculate_daily_trends(risk_scores)
        weekly_trends = self._calculate_weekly_trends(risk_scores)
        
        # Calculate trend direction
        trend_direction = self._calculate_trend_direction(daily_trends)
        
        # Identify significant changes
        significant_changes = self._identify_significant_changes(daily_trends)
        
        # Algorithm-specific trends
        algorithm_trends = self._analyze_algorithm_trends(risk_scores)
        
        return {
            "period_days": period_days,
            "analysis_date": datetime.utcnow().isoformat(),
            "daily_trends": daily_trends,
            "weekly_trends": weekly_trends,
            "trend_direction": trend_direction,
            "significant_changes": significant_changes,
            "algorithm_trends": algorithm_trends,
            "summary": self._generate_trend_summary(daily_trends, trend_direction)
        }
    
    def analyze_seasonal_patterns(self, db: Session, years: int = 2) -> Dict[str, Any]:
        """Analyze seasonal patterns in procurement risk"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=years * 365)
        
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {"error": "Insufficient data for seasonal analysis"}
        
        # Group by month
        monthly_patterns = defaultdict(list)
        
        for score in risk_scores:
            month = score.analysis_date.month
            monthly_patterns[month].append(float(score.overall_risk_score))
        
        # Calculate seasonal statistics
        seasonal_stats = {}
        for month, scores in monthly_patterns.items():
            if len(scores) >= 3:  # Minimum sample size
                seasonal_stats[month] = {
                    "month_name": self._get_month_name(month),
                    "avg_risk_score": np.mean(scores),
                    "median_risk_score": np.median(scores),
                    "std_risk_score": np.std(scores),
                    "sample_size": len(scores),
                    "high_risk_rate": sum(1 for s in scores if s >= 70) / len(scores)
                }
        
        # Identify seasonal peaks
        seasonal_peaks = self._identify_seasonal_peaks(seasonal_stats)
        
        return {
            "years_analyzed": years,
            "seasonal_patterns": seasonal_stats,
            "seasonal_peaks": seasonal_peaks,
            "recommendations": self._generate_seasonal_recommendations(seasonal_stats)
        }
    
    def analyze_geographic_trends(self, db: Session, period_days: int = 90) -> Dict[str, Any]:
        """Analyze geographic trends in risk patterns"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get risk scores with geographic info
        risk_scores = db.query(TenderRiskScore).join(Tender).join(ContractingAuthority).filter(
            and_(
                TenderRiskScore.analysis_date >= cutoff_date,
                ContractingAuthority.county.isnot(None)
            )
        ).all()
        
        if not risk_scores:
            return {"error": "No geographic data available"}
        
        # Group by county and time
        county_trends = defaultdict(lambda: defaultdict(list))
        
        for score in risk_scores:
            county = score.tender.contracting_authority.county
            week = score.analysis_date.strftime("%Y-W%U")
            county_trends[county][week].append(float(score.overall_risk_score))
        
        # Calculate trends for each county
        county_analysis = {}
        for county, weekly_data in county_trends.items():
            if len(weekly_data) >= 3:  # Minimum weeks
                weekly_averages = [
                    np.mean(scores) for scores in weekly_data.values()
                ]
                
                # Calculate trend
                weeks = list(range(len(weekly_averages)))
                slope, intercept, r_value, p_value, std_err = stats.linregress(weeks, weekly_averages)
                
                county_analysis[county] = {
                    "trend_slope": slope,
                    "trend_r_squared": r_value ** 2,
                    "trend_p_value": p_value,
                    "trend_direction": "increasing" if slope > 0 else "decreasing",
                    "is_significant": p_value < 0.05,
                    "avg_risk_score": np.mean(weekly_averages),
                    "weeks_analyzed": len(weekly_averages)
                }
        
        # Identify counties with concerning trends
        concerning_counties = [
            (county, data) for county, data in county_analysis.items()
            if data["trend_direction"] == "increasing" and data["is_significant"]
        ]
        
        return {
            "period_days": period_days,
            "county_trends": county_analysis,
            "concerning_counties": concerning_counties,
            "geographic_insights": self._generate_geographic_insights(county_analysis)
        }
    
    def analyze_authority_trends(self, db: Session, period_days: int = 90) -> Dict[str, Any]:
        """Analyze trends by contracting authority"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get risk scores by authority
        risk_scores = db.query(TenderRiskScore).join(Tender).join(ContractingAuthority).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {"error": "No authority data available"}
        
        # Group by authority
        authority_trends = defaultdict(list)
        
        for score in risk_scores:
            authority_id = score.tender.contracting_authority.id
            authority_trends[authority_id].append({
                "date": score.analysis_date,
                "score": float(score.overall_risk_score),
                "level": score.risk_level,
                "authority_name": score.tender.contracting_authority.name
            })
        
        # Analyze trends for authorities with sufficient data
        authority_analysis = {}
        for authority_id, scores in authority_trends.items():
            if len(scores) >= 5:  # Minimum sample size
                # Sort by date
                scores.sort(key=lambda x: x["date"])
                
                # Calculate moving average
                score_values = [s["score"] for s in scores]
                moving_avg = self._calculate_moving_average(score_values, window=3)
                
                # Calculate trend
                days = [(s["date"] - scores[0]["date"]).days for s in scores]
                slope, intercept, r_value, p_value, std_err = stats.linregress(days, score_values)
                
                authority_analysis[authority_id] = {
                    "authority_name": scores[0]["authority_name"],
                    "trend_slope": slope,
                    "trend_r_squared": r_value ** 2,
                    "trend_p_value": p_value,
                    "trend_direction": "increasing" if slope > 0 else "decreasing",
                    "is_significant": p_value < 0.05,
                    "avg_risk_score": np.mean(score_values),
                    "latest_score": score_values[-1],
                    "sample_size": len(scores),
                    "moving_average": moving_avg
                }
        
        # Identify authorities with concerning trends
        concerning_authorities = [
            (auth_id, data) for auth_id, data in authority_analysis.items()
            if data["trend_direction"] == "increasing" and data["is_significant"]
        ]
        
        return {
            "period_days": period_days,
            "authority_trends": authority_analysis,
            "concerning_authorities": concerning_authorities,
            "recommendations": self._generate_authority_recommendations(authority_analysis)
        }
    
    def analyze_sector_trends(self, db: Session, period_days: int = 90) -> Dict[str, Any]:
        """Analyze trends by sector (CPV codes)"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get risk scores by sector
        risk_scores = db.query(TenderRiskScore).join(Tender).filter(
            and_(
                TenderRiskScore.analysis_date >= cutoff_date,
                Tender.cpv_code.isnot(None)
            )
        ).all()
        
        if not risk_scores:
            return {"error": "No sector data available"}
        
        # Group by parent CPV code (first 4 digits)
        sector_trends = defaultdict(list)
        
        for score in risk_scores:
            cpv_parent = score.tender.cpv_code[:4]
            sector_trends[cpv_parent].append({
                "date": score.analysis_date,
                "score": float(score.overall_risk_score),
                "level": score.risk_level
            })
        
        # Analyze trends for sectors with sufficient data
        sector_analysis = {}
        for cpv_code, scores in sector_trends.items():
            if len(scores) >= 5:  # Minimum sample size
                # Sort by date
                scores.sort(key=lambda x: x["date"])
                
                # Calculate trend
                score_values = [s["score"] for s in scores]
                days = [(s["date"] - scores[0]["date"]).days for s in scores]
                
                slope, intercept, r_value, p_value, std_err = stats.linregress(days, score_values)
                
                sector_analysis[cpv_code] = {
                    "cpv_description": self._get_cpv_description(cpv_code),
                    "trend_slope": slope,
                    "trend_r_squared": r_value ** 2,
                    "trend_p_value": p_value,
                    "trend_direction": "increasing" if slope > 0 else "decreasing",
                    "is_significant": p_value < 0.05,
                    "avg_risk_score": np.mean(score_values),
                    "latest_score": score_values[-1],
                    "sample_size": len(scores)
                }
        
        # Identify sectors with concerning trends
        concerning_sectors = [
            (cpv, data) for cpv, data in sector_analysis.items()
            if data["trend_direction"] == "increasing" and data["is_significant"]
        ]
        
        return {
            "period_days": period_days,
            "sector_trends": sector_analysis,
            "concerning_sectors": concerning_sectors,
            "sector_insights": self._generate_sector_insights(sector_analysis)
        }
    
    def detect_anomalous_periods(self, db: Session, period_days: int = 180) -> Dict[str, Any]:
        """Detect anomalous periods in risk patterns"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).order_by(TenderRiskScore.analysis_date).all()
        
        if not risk_scores:
            return {"error": "No data available for anomaly detection"}
        
        # Group by week
        weekly_data = defaultdict(list)
        
        for score in risk_scores:
            week = score.analysis_date.strftime("%Y-W%U")
            weekly_data[week].append(float(score.overall_risk_score))
        
        # Calculate weekly averages
        weekly_averages = []
        weeks = []
        
        for week in sorted(weekly_data.keys()):
            scores = weekly_data[week]
            if len(scores) >= 3:  # Minimum sample size
                weekly_averages.append(np.mean(scores))
                weeks.append(week)
        
        if len(weekly_averages) < 4:
            return {"error": "Insufficient data for anomaly detection"}
        
        # Detect anomalies using z-score
        mean_score = np.mean(weekly_averages)
        std_score = np.std(weekly_averages)
        
        anomalous_periods = []
        for i, (week, avg_score) in enumerate(zip(weeks, weekly_averages)):
            z_score = abs(avg_score - mean_score) / std_score if std_score > 0 else 0
            
            if z_score > 2:  # Anomaly threshold
                anomalous_periods.append({
                    "week": week,
                    "avg_risk_score": avg_score,
                    "z_score": z_score,
                    "anomaly_type": "high" if avg_score > mean_score else "low",
                    "severity": "high" if z_score > 3 else "medium"
                })
        
        return {
            "period_days": period_days,
            "weeks_analyzed": len(weeks),
            "baseline_avg": mean_score,
            "baseline_std": std_score,
            "anomalous_periods": anomalous_periods,
            "anomaly_insights": self._generate_anomaly_insights(anomalous_periods)
        }
    
    # Helper methods
    def _calculate_daily_trends(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Dict[str, Any]]:
        """Calculate daily trend data"""
        
        daily_data = defaultdict(list)
        
        for score in risk_scores:
            date_key = score.analysis_date.date().isoformat()
            daily_data[date_key].append(float(score.overall_risk_score))
        
        daily_trends = {}
        for date, scores in daily_data.items():
            daily_trends[date] = {
                "avg_risk_score": np.mean(scores),
                "median_risk_score": np.median(scores),
                "std_risk_score": np.std(scores),
                "sample_size": len(scores),
                "high_risk_count": sum(1 for s in scores if s >= 70),
                "high_risk_rate": sum(1 for s in scores if s >= 70) / len(scores)
            }
        
        return daily_trends
    
    def _calculate_weekly_trends(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Dict[str, Any]]:
        """Calculate weekly trend data"""
        
        weekly_data = defaultdict(list)
        
        for score in risk_scores:
            week_key = score.analysis_date.strftime("%Y-W%U")
            weekly_data[week_key].append(float(score.overall_risk_score))
        
        weekly_trends = {}
        for week, scores in weekly_data.items():
            weekly_trends[week] = {
                "avg_risk_score": np.mean(scores),
                "median_risk_score": np.median(scores),
                "std_risk_score": np.std(scores),
                "sample_size": len(scores),
                "high_risk_count": sum(1 for s in scores if s >= 70),
                "high_risk_rate": sum(1 for s in scores if s >= 70) / len(scores)
            }
        
        return weekly_trends
    
    def _calculate_trend_direction(self, daily_trends: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall trend direction"""
        
        if len(daily_trends) < 3:
            return {"error": "Insufficient data for trend calculation"}
        
        # Sort by date
        sorted_dates = sorted(daily_trends.keys())
        avg_scores = [daily_trends[date]["avg_risk_score"] for date in sorted_dates]
        
        # Calculate linear regression
        days = list(range(len(avg_scores)))
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, avg_scores)
        
        return {
            "slope": slope,
            "r_squared": r_value ** 2,
            "p_value": p_value,
            "direction": "increasing" if slope > 0 else "decreasing",
            "is_significant": p_value < 0.05,
            "strength": "strong" if abs(r_value) > 0.7 else "moderate" if abs(r_value) > 0.3 else "weak"
        }
    
    def _identify_significant_changes(self, daily_trends: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify significant changes in trends"""
        
        if len(daily_trends) < 7:
            return []
        
        sorted_dates = sorted(daily_trends.keys())
        avg_scores = [daily_trends[date]["avg_risk_score"] for date in sorted_dates]
        
        # Calculate rolling average
        window = 7
        rolling_avg = []
        
        for i in range(len(avg_scores) - window + 1):
            rolling_avg.append(np.mean(avg_scores[i:i+window]))
        
        # Find significant changes
        changes = []
        threshold = np.std(rolling_avg) * 1.5  # 1.5 standard deviations
        
        for i in range(1, len(rolling_avg)):
            change = rolling_avg[i] - rolling_avg[i-1]
            if abs(change) > threshold:
                changes.append({
                    "date": sorted_dates[i + window - 1],
                    "change_magnitude": change,
                    "change_type": "increase" if change > 0 else "decrease",
                    "severity": "high" if abs(change) > threshold * 2 else "medium"
                })
        
        return changes
    
    def _analyze_algorithm_trends(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Any]:
        """Analyze trends for individual algorithms"""
        
        algorithm_data = {
            "single_bidder": [],
            "price_anomaly": [],
            "frequent_winner": [],
            "geographic": []
        }
        
        for score in risk_scores:
            date = score.analysis_date.date()
            
            if score.single_bidder_risk:
                algorithm_data["single_bidder"].append((date, float(score.single_bidder_risk)))
            if score.price_anomaly_risk:
                algorithm_data["price_anomaly"].append((date, float(score.price_anomaly_risk)))
            if score.frequency_risk:
                algorithm_data["frequent_winner"].append((date, float(score.frequency_risk)))
            if score.geographic_risk:
                algorithm_data["geographic"].append((date, float(score.geographic_risk)))
        
        algorithm_trends = {}
        for algorithm, data in algorithm_data.items():
            if len(data) >= 5:
                # Group by date and calculate averages
                date_groups = defaultdict(list)
                for date, score in data:
                    date_groups[date].append(score)
                
                # Calculate daily averages
                daily_avgs = []
                dates = []
                for date in sorted(date_groups.keys()):
                    daily_avgs.append(np.mean(date_groups[date]))
                    dates.append(date)
                
                if len(daily_avgs) >= 3:
                    # Calculate trend
                    days = [(date - dates[0]).days for date in dates]
                    slope, intercept, r_value, p_value, std_err = stats.linregress(days, daily_avgs)
                    
                    algorithm_trends[algorithm] = {
                        "slope": slope,
                        "r_squared": r_value ** 2,
                        "p_value": p_value,
                        "direction": "increasing" if slope > 0 else "decreasing",
                        "is_significant": p_value < 0.05,
                        "avg_score": np.mean(daily_avgs),
                        "latest_score": daily_avgs[-1],
                        "sample_size": len(data)
                    }
        
        return algorithm_trends
    
    def _generate_trend_summary(self, daily_trends: Dict[str, Dict[str, Any]], 
                               trend_direction: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of trends"""
        
        if not daily_trends:
            return {"error": "No trend data available"}
        
        # Calculate period statistics
        all_scores = []
        for date_data in daily_trends.values():
            all_scores.extend([date_data["avg_risk_score"]] * date_data["sample_size"])
        
        return {
            "period_avg_score": np.mean(all_scores),
            "period_high_risk_rate": sum(1 for s in all_scores if s >= 70) / len(all_scores),
            "trend_direction": trend_direction.get("direction", "unknown"),
            "trend_strength": trend_direction.get("strength", "unknown"),
            "is_trend_significant": trend_direction.get("is_significant", False),
            "total_tenders_analyzed": len(all_scores)
        }
    
    def _calculate_moving_average(self, values: List[float], window: int = 3) -> List[float]:
        """Calculate moving average"""
        
        if len(values) < window:
            return values
        
        moving_avg = []
        for i in range(len(values) - window + 1):
            moving_avg.append(np.mean(values[i:i+window]))
        
        return moving_avg
    
    def _get_month_name(self, month: int) -> str:
        """Get month name"""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return months[month - 1]
    
    def _identify_seasonal_peaks(self, seasonal_stats: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify seasonal peaks in risk"""
        
        if not seasonal_stats:
            return []
        
        # Find months with highest risk
        risk_scores = [(month, data["avg_risk_score"]) for month, data in seasonal_stats.items()]
        risk_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Identify peaks (top 25% of months)
        peak_threshold = len(risk_scores) // 4
        peaks = []
        
        for month, score in risk_scores[:peak_threshold]:
            peaks.append({
                "month": month,
                "month_name": self._get_month_name(month),
                "avg_risk_score": score,
                "rank": risk_scores.index((month, score)) + 1
            })
        
        return peaks
    
    def _generate_seasonal_recommendations(self, seasonal_stats: Dict[int, Dict[str, Any]]) -> List[str]:
        """Generate seasonal recommendations"""
        
        recommendations = []
        
        if not seasonal_stats:
            return recommendations
        
        # Find high-risk months
        high_risk_months = [
            (month, data) for month, data in seasonal_stats.items()
            if data["high_risk_rate"] > 0.2
        ]
        
        if high_risk_months:
            month_names = [self._get_month_name(month) for month, _ in high_risk_months]
            recommendations.append(f"Enhanced monitoring recommended for {', '.join(month_names)}")
        
        return recommendations
    
    def _generate_geographic_insights(self, county_analysis: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate geographic insights"""
        
        insights = []
        
        increasing_counties = [
            county for county, data in county_analysis.items()
            if data["trend_direction"] == "increasing" and data["is_significant"]
        ]
        
        if len(increasing_counties) > 5:
            insights.append("Multiple counties showing increasing risk trends - systemic issue possible")
        elif increasing_counties:
            insights.append(f"Risk increasing in {len(increasing_counties)} counties")
        
        return insights
    
    def _generate_authority_recommendations(self, authority_analysis: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate authority recommendations"""
        
        recommendations = []
        
        concerning_count = sum(
            1 for data in authority_analysis.values()
            if data["trend_direction"] == "increasing" and data["is_significant"]
        )
        
        if concerning_count > 0:
            recommendations.append(f"Enhanced monitoring for {concerning_count} authorities with increasing risk trends")
        
        return recommendations
    
    def _get_cpv_description(self, cpv_code: str) -> str:
        """Get CPV code description (simplified)"""
        
        # Simplified CPV descriptions
        cpv_descriptions = {
            "0311": "Agricultural products",
            "4521": "Construction work",
            "5041": "Medical equipment",
            "7242": "Consulting services",
            "9000": "Transport services"
        }
        
        return cpv_descriptions.get(cpv_code, f"CPV {cpv_code}")
    
    def _generate_sector_insights(self, sector_analysis: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate sector insights"""
        
        insights = []
        
        high_risk_sectors = [
            (cpv, data) for cpv, data in sector_analysis.items()
            if data["avg_risk_score"] > 60
        ]
        
        if high_risk_sectors:
            insights.append(f"{len(high_risk_sectors)} sectors showing elevated risk levels")
        
        return insights
    
    def _generate_anomaly_insights(self, anomalous_periods: List[Dict[str, Any]]) -> List[str]:
        """Generate insights about anomalous periods"""
        
        insights = []
        
        if not anomalous_periods:
            insights.append("No anomalous periods detected")
            return insights
        
        high_anomalies = [p for p in anomalous_periods if p["severity"] == "high"]
        if high_anomalies:
            insights.append(f"{len(high_anomalies)} high-severity anomalous periods detected")
        
        return insights
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the trend analyzer"""
        
        return {
            "name": "Trend Analyzer",
            "version": self.version,
            "description": "Analyzes trends in procurement risk patterns over time",
            "capabilities": [
                "Overall risk trend analysis",
                "Seasonal pattern detection",
                "Geographic trend analysis",
                "Authority-specific trends",
                "Sector trend analysis",
                "Anomalous period detection"
            ],
            "analysis_methods": [
                "Linear regression",
                "Moving averages",
                "Z-score anomaly detection",
                "Seasonal decomposition"
            ]
        }