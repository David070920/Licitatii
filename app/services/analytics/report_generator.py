"""
Risk Report Generator

This module provides comprehensive risk reporting capabilities for different
user types and use cases in the Romanian procurement transparency platform.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import pandas as pd
import json
from decimal import Decimal

from app.db.models import (
    Tender, TenderRiskScore, TenderAward, Company, 
    ContractingAuthority, CPVCode, User
)
from .statistical_analyzer import StatisticalAnalyzer


class ReportGenerator:
    """Generates comprehensive risk reports for various stakeholders"""
    
    def __init__(self):
        self.statistical_analyzer = StatisticalAnalyzer()
        self.version = "1.0.0"
    
    def generate_executive_summary(self, db: Session, period_days: int = 30) -> Dict[str, Any]:
        """Generate executive summary report for leadership"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get risk scores for the period
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "report_type": "executive_summary",
                "period_days": period_days,
                "message": "No risk data available for the specified period",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Calculate key metrics
        total_analyzed = len(risk_scores)
        high_risk_count = sum(1 for score in risk_scores if score.risk_level == "HIGH")
        medium_risk_count = sum(1 for score in risk_scores if score.risk_level == "MEDIUM")
        
        # Calculate total contract value analyzed
        total_value = 0
        high_risk_value = 0
        
        for score in risk_scores:
            if score.tender and score.tender.estimated_value:
                value = float(score.tender.estimated_value)
                total_value += value
                if score.risk_level == "HIGH":
                    high_risk_value += value
        
        # Top risk factors
        all_flags = []
        for score in risk_scores:
            all_flags.extend(score.risk_flags)
        
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        top_risk_factors = sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Algorithm performance
        algorithm_scores = {
            "single_bidder": [float(s.single_bidder_risk) for s in risk_scores if s.single_bidder_risk],
            "price_anomaly": [float(s.price_anomaly_risk) for s in risk_scores if s.price_anomaly_risk],
            "frequent_winner": [float(s.frequency_risk) for s in risk_scores if s.frequency_risk],
            "geographic": [float(s.geographic_risk) for s in risk_scores if s.geographic_risk]
        }
        
        # Key insights
        insights = self._generate_executive_insights(risk_scores, period_days)
        
        return {
            "report_type": "executive_summary",
            "period_days": period_days,
            "generated_at": datetime.utcnow().isoformat(),
            "key_metrics": {
                "total_tenders_analyzed": total_analyzed,
                "high_risk_count": high_risk_count,
                "high_risk_percentage": (high_risk_count / total_analyzed) * 100,
                "medium_risk_count": medium_risk_count,
                "medium_risk_percentage": (medium_risk_count / total_analyzed) * 100,
                "total_contract_value": total_value,
                "high_risk_value": high_risk_value,
                "high_risk_value_percentage": (high_risk_value / total_value) * 100 if total_value > 0 else 0
            },
            "top_risk_factors": top_risk_factors,
            "algorithm_performance": {
                algorithm: {
                    "avg_score": sum(scores) / len(scores) if scores else 0,
                    "max_score": max(scores) if scores else 0,
                    "detections": len([s for s in scores if s > 50])
                }
                for algorithm, scores in algorithm_scores.items()
            },
            "key_insights": insights,
            "recommendations": self._generate_executive_recommendations(risk_scores)
        }
    
    def generate_detailed_risk_report(self, db: Session, period_days: int = 30) -> Dict[str, Any]:
        """Generate detailed risk analysis report for analysts"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get comprehensive data
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "report_type": "detailed_risk_report",
                "period_days": period_days,
                "message": "No risk data available",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Statistical analysis
        overall_scores = [float(score.overall_risk_score) for score in risk_scores]
        risk_levels = [score.risk_level for score in risk_scores]
        
        statistical_analysis = self.statistical_analyzer.calculate_risk_metrics(overall_scores, risk_levels)
        
        # Algorithm analysis
        algorithm_analysis = self._analyze_algorithm_performance(risk_scores)
        
        # Geographic analysis
        geographic_analysis = self._analyze_geographic_patterns(risk_scores, db)
        
        # Temporal analysis
        temporal_analysis = self._analyze_temporal_patterns(risk_scores)
        
        # Contracting authority analysis
        authority_analysis = self._analyze_contracting_authorities(risk_scores, db)
        
        # High-risk tender details
        high_risk_details = self._get_high_risk_tender_details(risk_scores, db)
        
        return {
            "report_type": "detailed_risk_report",
            "period_days": period_days,
            "generated_at": datetime.utcnow().isoformat(),
            "statistical_analysis": statistical_analysis,
            "algorithm_analysis": algorithm_analysis,
            "geographic_analysis": geographic_analysis,
            "temporal_analysis": temporal_analysis,
            "authority_analysis": authority_analysis,
            "high_risk_details": high_risk_details,
            "methodology": self._get_methodology_description()
        }
    
    def generate_public_transparency_report(self, db: Session, period_days: int = 30) -> Dict[str, Any]:
        """Generate public transparency report for citizens and media"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "report_type": "public_transparency_report",
                "period_days": period_days,
                "message": "No data available for the specified period",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Public-friendly metrics
        total_analyzed = len(risk_scores)
        high_risk_count = sum(1 for score in risk_scores if score.risk_level == "HIGH")
        
        # Calculate financial impact
        total_value = sum(
            float(score.tender.estimated_value) 
            for score in risk_scores 
            if score.tender and score.tender.estimated_value
        )
        
        high_risk_value = sum(
            float(score.tender.estimated_value) 
            for score in risk_scores 
            if score.risk_level == "HIGH" and score.tender and score.tender.estimated_value
        )
        
        # Most common issues
        all_flags = []
        for score in risk_scores:
            all_flags.extend(score.risk_flags)
        
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        # Convert technical flags to public-friendly descriptions
        public_issues = self._convert_flags_to_public_descriptions(flag_counts)
        
        # County-level summary
        county_summary = self._generate_county_summary(risk_scores, db)
        
        # High-value high-risk tenders (public interest)
        high_value_high_risk = [
            {
                "title": score.tender.title,
                "contracting_authority": score.tender.contracting_authority.name if score.tender.contracting_authority else "Unknown",
                "estimated_value": float(score.tender.estimated_value) if score.tender.estimated_value else None,
                "risk_score": float(score.overall_risk_score),
                "main_concerns": score.risk_flags[:3]  # Top 3 concerns
            }
            for score in risk_scores
            if (score.risk_level == "HIGH" and 
                score.tender and 
                score.tender.estimated_value and 
                float(score.tender.estimated_value) > 500000)  # 500K RON threshold
        ]
        
        # Sort by value
        high_value_high_risk.sort(key=lambda x: x["estimated_value"] or 0, reverse=True)
        
        return {
            "report_type": "public_transparency_report",
            "period_days": period_days,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_tenders_analyzed": total_analyzed,
                "total_value_analyzed": total_value,
                "high_risk_tenders": high_risk_count,
                "high_risk_percentage": (high_risk_count / total_analyzed) * 100,
                "high_risk_value": high_risk_value,
                "potential_savings": high_risk_value * 0.1  # Estimated 10% savings potential
            },
            "common_issues": public_issues,
            "county_summary": county_summary,
            "high_value_concerns": high_value_high_risk[:10],  # Top 10
            "explanation": {
                "what_is_this": "This report analyzes public procurement data to identify potential irregularities and promote transparency.",
                "risk_levels": {
                    "HIGH": "Tenders with significant indicators of potential irregularities",
                    "MEDIUM": "Tenders with some concerning patterns that warrant attention",
                    "LOW": "Tenders with minor irregularities or normal variations"
                },
                "methodology": "Analysis uses statistical methods and pattern recognition to identify unusual procurement patterns."
            }
        }
    
    def generate_business_intelligence_report(self, db: Session, period_days: int = 30) -> Dict[str, Any]:
        """Generate business intelligence report for market participants"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get data
        risk_scores = db.query(TenderRiskScore).join(Tender).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "report_type": "business_intelligence_report",
                "period_days": period_days,
                "message": "No data available",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Market opportunity analysis
        market_opportunities = self._analyze_market_opportunities(risk_scores, db)
        
        # Competition analysis
        competition_analysis = self._analyze_competition_patterns(risk_scores, db)
        
        # Sector analysis
        sector_analysis = self._analyze_sector_patterns(risk_scores, db)
        
        # Authority analysis
        authority_insights = self._analyze_authority_patterns(risk_scores, db)
        
        # Procurement trends
        procurement_trends = self._analyze_procurement_trends(risk_scores, db)
        
        return {
            "report_type": "business_intelligence_report",
            "period_days": period_days,
            "generated_at": datetime.utcnow().isoformat(),
            "market_opportunities": market_opportunities,
            "competition_analysis": competition_analysis,
            "sector_analysis": sector_analysis,
            "authority_insights": authority_insights,
            "procurement_trends": procurement_trends,
            "recommendations": self._generate_business_recommendations(risk_scores, db)
        }
    
    def generate_compliance_report(self, db: Session, period_days: int = 30) -> Dict[str, Any]:
        """Generate compliance report for regulatory oversight"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "report_type": "compliance_report",
                "period_days": period_days,
                "message": "No data available",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Compliance violations
        violations = self._categorize_compliance_violations(risk_scores)
        
        # Authority compliance
        authority_compliance = self._analyze_authority_compliance(risk_scores, db)
        
        # Systemic issues
        systemic_issues = self._identify_systemic_issues(risk_scores, db)
        
        # Recommendations for regulatory action
        regulatory_recommendations = self._generate_regulatory_recommendations(risk_scores, db)
        
        return {
            "report_type": "compliance_report",
            "period_days": period_days,
            "generated_at": datetime.utcnow().isoformat(),
            "compliance_violations": violations,
            "authority_compliance": authority_compliance,
            "systemic_issues": systemic_issues,
            "regulatory_recommendations": regulatory_recommendations,
            "legal_framework": self._get_legal_framework_context()
        }
    
    # Helper methods
    def _generate_executive_insights(self, risk_scores: List[TenderRiskScore], period_days: int) -> List[str]:
        """Generate key insights for executive summary"""
        
        insights = []
        
        # Risk level trends
        high_risk_rate = sum(1 for score in risk_scores if score.risk_level == "HIGH") / len(risk_scores)
        
        if high_risk_rate > 0.20:
            insights.append(f"High risk rate of {high_risk_rate:.1%} indicates systemic procurement issues")
        elif high_risk_rate > 0.10:
            insights.append(f"Elevated risk rate of {high_risk_rate:.1%} requires management attention")
        
        # Single bidder patterns
        single_bidder_flags = sum(
            1 for score in risk_scores 
            if "SINGLE_BIDDER" in score.risk_flags
        )
        
        if single_bidder_flags > len(risk_scores) * 0.3:
            insights.append("High prevalence of single bidder tenders suggests competition issues")
        
        # Geographic concentration
        geographic_flags = sum(
            1 for score in risk_scores 
            if any("GEOGRAPHIC" in flag or "LOCAL" in flag for flag in score.risk_flags)
        )
        
        if geographic_flags > len(risk_scores) * 0.2:
            insights.append("Geographic concentration patterns indicate potential local monopolies")
        
        return insights
    
    def _generate_executive_recommendations(self, risk_scores: List[TenderRiskScore]) -> List[str]:
        """Generate recommendations for executive action"""
        
        recommendations = []
        
        high_risk_count = sum(1 for score in risk_scores if score.risk_level == "HIGH")
        
        if high_risk_count > 0:
            recommendations.append("Implement enhanced oversight for high-risk tenders")
            recommendations.append("Conduct detailed audits of flagged procurements")
        
        # Most common flags
        all_flags = []
        for score in risk_scores:
            all_flags.extend(score.risk_flags)
        
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        if flag_counts.get("SINGLE_BIDDER", 0) > len(risk_scores) * 0.2:
            recommendations.append("Review tender specifications to enhance competition")
        
        if flag_counts.get("HIGH_WIN_RATE", 0) > len(risk_scores) * 0.1:
            recommendations.append("Investigate market concentration and potential monopolistic behavior")
        
        return recommendations
    
    def _analyze_algorithm_performance(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Any]:
        """Analyze performance of individual algorithms"""
        
        algorithms = {
            "single_bidder": [float(s.single_bidder_risk) for s in risk_scores if s.single_bidder_risk],
            "price_anomaly": [float(s.price_anomaly_risk) for s in risk_scores if s.price_anomaly_risk],
            "frequent_winner": [float(s.frequency_risk) for s in risk_scores if s.frequency_risk],
            "geographic": [float(s.geographic_risk) for s in risk_scores if s.geographic_risk]
        }
        
        performance = {}
        for algorithm, scores in algorithms.items():
            if scores:
                performance[algorithm] = self.statistical_analyzer.analyze_distribution(scores, algorithm)
        
        return performance
    
    def _analyze_geographic_patterns(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze geographic patterns in risk"""
        
        county_risks = {}
        
        for score in risk_scores:
            if score.tender and score.tender.contracting_authority:
                county = score.tender.contracting_authority.county
                if county:
                    if county not in county_risks:
                        county_risks[county] = []
                    county_risks[county].append(float(score.overall_risk_score))
        
        county_analysis = {}
        for county, scores in county_risks.items():
            if len(scores) >= 3:  # Minimum sample size
                county_analysis[county] = {
                    "avg_risk_score": sum(scores) / len(scores),
                    "tender_count": len(scores),
                    "high_risk_count": sum(1 for s in scores if s >= 70)
                }
        
        return county_analysis
    
    def _analyze_temporal_patterns(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Any]:
        """Analyze temporal patterns in risk"""
        
        # Group by month
        monthly_risks = {}
        
        for score in risk_scores:
            month_key = score.analysis_date.strftime("%Y-%m")
            if month_key not in monthly_risks:
                monthly_risks[month_key] = []
            monthly_risks[month_key].append(float(score.overall_risk_score))
        
        monthly_analysis = {}
        for month, scores in monthly_risks.items():
            monthly_analysis[month] = {
                "avg_risk_score": sum(scores) / len(scores),
                "tender_count": len(scores),
                "high_risk_count": sum(1 for s in scores if s >= 70)
            }
        
        return monthly_analysis
    
    def _analyze_contracting_authorities(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze contracting authority patterns"""
        
        authority_risks = {}
        
        for score in risk_scores:
            if score.tender and score.tender.contracting_authority:
                authority_id = score.tender.contracting_authority.id
                authority_name = score.tender.contracting_authority.name
                
                if authority_id not in authority_risks:
                    authority_risks[authority_id] = {
                        "name": authority_name,
                        "scores": []
                    }
                authority_risks[authority_id]["scores"].append(float(score.overall_risk_score))
        
        # Calculate metrics for authorities with sufficient data
        authority_analysis = {}
        for authority_id, data in authority_risks.items():
            scores = data["scores"]
            if len(scores) >= 3:  # Minimum sample size
                authority_analysis[authority_id] = {
                    "name": data["name"],
                    "tender_count": len(scores),
                    "avg_risk_score": sum(scores) / len(scores),
                    "high_risk_count": sum(1 for s in scores if s >= 70),
                    "high_risk_rate": (sum(1 for s in scores if s >= 70) / len(scores)) * 100
                }
        
        return authority_analysis
    
    def _get_high_risk_tender_details(self, risk_scores: List[TenderRiskScore], db: Session) -> List[Dict[str, Any]]:
        """Get detailed information about high-risk tenders"""
        
        high_risk_tenders = [score for score in risk_scores if score.risk_level == "HIGH"]
        
        details = []
        for score in high_risk_tenders[:20]:  # Top 20
            tender = score.tender
            if tender:
                details.append({
                    "tender_id": str(tender.id),
                    "title": tender.title,
                    "contracting_authority": tender.contracting_authority.name if tender.contracting_authority else None,
                    "estimated_value": float(tender.estimated_value) if tender.estimated_value else None,
                    "publication_date": tender.publication_date.isoformat() if tender.publication_date else None,
                    "risk_score": float(score.overall_risk_score),
                    "risk_flags": score.risk_flags,
                    "algorithm_scores": {
                        "single_bidder": float(score.single_bidder_risk) if score.single_bidder_risk else None,
                        "price_anomaly": float(score.price_anomaly_risk) if score.price_anomaly_risk else None,
                        "frequent_winner": float(score.frequency_risk) if score.frequency_risk else None,
                        "geographic": float(score.geographic_risk) if score.geographic_risk else None
                    }
                })
        
        return details
    
    def _get_methodology_description(self) -> Dict[str, Any]:
        """Get description of risk detection methodology"""
        
        return {
            "overview": "Multi-algorithm risk detection system analyzing procurement patterns",
            "algorithms": {
                "single_bidder": "Detects tenders with suspiciously few bidders",
                "price_anomaly": "Identifies unusual pricing patterns using statistical analysis",
                "frequent_winner": "Detects companies with unusually high win rates",
                "geographic": "Identifies suspicious geographic clustering patterns"
            },
            "scoring": "Weighted combination of algorithm outputs with amplification factors",
            "risk_levels": {
                "HIGH": "Score >= 70, immediate attention required",
                "MEDIUM": "Score 40-69, enhanced monitoring recommended",
                "LOW": "Score 20-39, routine monitoring",
                "MINIMAL": "Score < 20, no special attention required"
            }
        }
    
    def _convert_flags_to_public_descriptions(self, flag_counts: Dict[str, int]) -> List[Dict[str, Any]]:
        """Convert technical flags to public-friendly descriptions"""
        
        flag_descriptions = {
            "SINGLE_BIDDER": "Only one company submitted a bid",
            "HIGH_WIN_RATE": "Company wins contracts very frequently",
            "ESTIMATED_VALUE_ANOMALY": "Unusual estimated contract value",
            "LOCAL_MARKET_DOMINANCE": "Single company dominates local market",
            "PRICE_ANOMALY": "Unusual pricing patterns detected"
        }
        
        public_issues = []
        for flag, count in sorted(flag_counts.items(), key=lambda x: x[1], reverse=True):
            if flag in flag_descriptions:
                public_issues.append({
                    "issue": flag_descriptions[flag],
                    "occurrences": count,
                    "technical_flag": flag
                })
        
        return public_issues[:10]  # Top 10 issues
    
    def _generate_county_summary(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Generate county-level summary for public report"""
        
        county_data = {}
        
        for score in risk_scores:
            if score.tender and score.tender.contracting_authority:
                county = score.tender.contracting_authority.county
                if county:
                    if county not in county_data:
                        county_data[county] = {
                            "total_tenders": 0,
                            "high_risk_tenders": 0,
                            "total_value": 0
                        }
                    
                    county_data[county]["total_tenders"] += 1
                    if score.risk_level == "HIGH":
                        county_data[county]["high_risk_tenders"] += 1
                    
                    if score.tender.estimated_value:
                        county_data[county]["total_value"] += float(score.tender.estimated_value)
        
        # Calculate percentages
        for county, data in county_data.items():
            data["high_risk_percentage"] = (data["high_risk_tenders"] / data["total_tenders"]) * 100
        
        return county_data
    
    def _analyze_market_opportunities(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze market opportunities for business intelligence"""
        
        # Markets with high competition issues
        low_competition_markets = []
        
        for score in risk_scores:
            if "SINGLE_BIDDER" in score.risk_flags and score.tender:
                cpv_code = score.tender.cpv_code
                if cpv_code:
                    low_competition_markets.append({
                        "cpv_code": cpv_code,
                        "tender_title": score.tender.title,
                        "estimated_value": float(score.tender.estimated_value) if score.tender.estimated_value else None,
                        "contracting_authority": score.tender.contracting_authority.name if score.tender.contracting_authority else None
                    })
        
        return {
            "low_competition_opportunities": low_competition_markets[:20],
            "total_opportunities": len(low_competition_markets)
        }
    
    def _analyze_competition_patterns(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze competition patterns"""
        
        # Simplified competition analysis
        high_competition_flags = sum(
            1 for score in risk_scores 
            if "HIGH_WIN_RATE" in score.risk_flags
        )
        
        single_bidder_flags = sum(
            1 for score in risk_scores 
            if "SINGLE_BIDDER" in score.risk_flags
        )
        
        return {
            "market_concentration_issues": high_competition_flags,
            "low_competition_tenders": single_bidder_flags,
            "competition_health_score": max(0, 100 - (single_bidder_flags / len(risk_scores)) * 100)
        }
    
    def _analyze_sector_patterns(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze patterns by sector (CPV codes)"""
        
        sector_risks = {}
        
        for score in risk_scores:
            if score.tender and score.tender.cpv_code:
                cpv_parent = score.tender.cpv_code[:4]  # Parent CPV
                if cpv_parent not in sector_risks:
                    sector_risks[cpv_parent] = []
                sector_risks[cpv_parent].append(float(score.overall_risk_score))
        
        sector_analysis = {}
        for cpv, scores in sector_risks.items():
            if len(scores) >= 3:
                sector_analysis[cpv] = {
                    "avg_risk_score": sum(scores) / len(scores),
                    "tender_count": len(scores),
                    "high_risk_count": sum(1 for s in scores if s >= 70)
                }
        
        return sector_analysis
    
    def _analyze_authority_patterns(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze authority patterns for business intelligence"""
        
        return self._analyze_contracting_authorities(risk_scores, db)
    
    def _analyze_procurement_trends(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze procurement trends"""
        
        return self._analyze_temporal_patterns(risk_scores)
    
    def _generate_business_recommendations(self, risk_scores: List[TenderRiskScore], db: Session) -> List[str]:
        """Generate business recommendations"""
        
        recommendations = []
        
        single_bidder_rate = sum(1 for score in risk_scores if "SINGLE_BIDDER" in score.risk_flags) / len(risk_scores)
        
        if single_bidder_rate > 0.2:
            recommendations.append("Consider targeting markets with low competition")
        
        recommendations.append("Monitor high-risk tenders for potential market entry opportunities")
        recommendations.append("Analyze successful bidders' strategies in concentrated markets")
        
        return recommendations
    
    def _categorize_compliance_violations(self, risk_scores: List[TenderRiskScore]) -> Dict[str, Any]:
        """Categorize compliance violations"""
        
        violations = {
            "competition_violations": [],
            "pricing_violations": [],
            "procedural_violations": [],
            "geographic_violations": []
        }
        
        for score in risk_scores:
            if score.risk_level == "HIGH":
                if "SINGLE_BIDDER" in score.risk_flags:
                    violations["competition_violations"].append(str(score.tender_id))
                if "PRICE_ANOMALY" in score.risk_flags:
                    violations["pricing_violations"].append(str(score.tender_id))
                if "LOCAL_MARKET_DOMINANCE" in score.risk_flags:
                    violations["geographic_violations"].append(str(score.tender_id))
        
        return violations
    
    def _analyze_authority_compliance(self, risk_scores: List[TenderRiskScore], db: Session) -> Dict[str, Any]:
        """Analyze authority compliance"""
        
        return self._analyze_contracting_authorities(risk_scores, db)
    
    def _identify_systemic_issues(self, risk_scores: List[TenderRiskScore], db: Session) -> List[Dict[str, Any]]:
        """Identify systemic issues"""
        
        issues = []
        
        # High rate of single bidder tenders
        single_bidder_rate = sum(1 for score in risk_scores if "SINGLE_BIDDER" in score.risk_flags) / len(risk_scores)
        if single_bidder_rate > 0.3:
            issues.append({
                "issue": "High rate of single bidder tenders",
                "severity": "HIGH",
                "rate": single_bidder_rate,
                "description": "Indicates potential barriers to competition"
            })
        
        return issues
    
    def _generate_regulatory_recommendations(self, risk_scores: List[TenderRiskScore], db: Session) -> List[str]:
        """Generate regulatory recommendations"""
        
        recommendations = []
        
        high_risk_count = sum(1 for score in risk_scores if score.risk_level == "HIGH")
        if high_risk_count > 0:
            recommendations.append("Conduct detailed investigations of high-risk tenders")
            recommendations.append("Implement enhanced monitoring for flagged contracting authorities")
        
        return recommendations
    
    def _get_legal_framework_context(self) -> Dict[str, Any]:
        """Get legal framework context"""
        
        return {
            "applicable_laws": [
                "Law 98/2016 on public procurement",
                "Law 99/2016 on sectoral procurement",
                "Emergency Ordinance 13/2015 on public contracts"
            ],
            "regulatory_bodies": [
                "National Agency for Public Procurement (ANAP)",
                "National Anti-corruption Directorate (DNA)",
                "Court of Accounts"
            ]
        }
    
    def get_available_reports(self) -> List[Dict[str, Any]]:
        """Get list of available report types"""
        
        return [
            {
                "name": "executive_summary",
                "description": "High-level overview for executive leadership",
                "target_audience": "C-level executives, senior management"
            },
            {
                "name": "detailed_risk_report",
                "description": "Comprehensive risk analysis for analysts",
                "target_audience": "Risk analysts, compliance officers"
            },
            {
                "name": "public_transparency_report",
                "description": "Public-friendly transparency report",
                "target_audience": "Citizens, media, civil society"
            },
            {
                "name": "business_intelligence_report",
                "description": "Market intelligence for business participants",
                "target_audience": "Companies, business analysts"
            },
            {
                "name": "compliance_report",
                "description": "Regulatory compliance analysis",
                "target_audience": "Regulatory bodies, oversight agencies"
            }
        ]