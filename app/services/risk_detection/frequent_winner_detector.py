"""
Frequent Winner Patterns Detection Algorithm

This module implements risk detection for companies that win contracts
suspiciously often, indicating potential monopolistic behavior or corruption.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import numpy as np
from collections import defaultdict

from app.db.models import Tender, TenderBid, TenderAward, Company, ContractingAuthority, CPVCode
from .base import BaseRiskDetector, RiskDetectionResult, RiskDetectionConfig, RiskAnalysisUtils


class FrequentWinnerDetector(BaseRiskDetector):
    """Detector for frequent winner patterns and market concentration"""
    
    def __init__(self, config: RiskDetectionConfig):
        super().__init__(config)
        self.algorithm_name = "Frequent Winner Detection"
        self.algorithm_version = "1.0.0"
    
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Analyze a tender for frequent winner patterns"""
        
        # Get winning company
        winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
        
        if not winning_bid or not winning_bid.company:
            return RiskDetectionResult(
                risk_score=0.0,
                risk_level="MINIMAL",
                risk_flags=["NO_WINNER_IDENTIFIED"],
                detailed_analysis={
                    "algorithm": self.algorithm_name,
                    "analysis_type": "single_tender",
                    "reason": "No winning company identified"
                }
            )
        
        winning_company = winning_bid.company
        risk_flags = []
        risk_factors = {}
        
        # Analyze winner frequency patterns
        frequency_analysis = self._analyze_winner_frequency(
            winning_company, tender, db, risk_factors
        )
        
        # Analyze market concentration
        concentration_analysis = self._analyze_market_concentration(
            winning_company, tender, db, risk_factors
        )
        
        # Analyze geographic concentration
        geographic_analysis = self._analyze_geographic_concentration(
            winning_company, tender, db, risk_factors
        )
        
        # Analyze CPV specialization
        cpv_analysis = self._analyze_cpv_specialization(
            winning_company, tender, db, risk_factors
        )
        
        # Calculate risk score
        risk_score = self._calculate_frequent_winner_risk_score(
            frequency_analysis,
            concentration_analysis,
            geographic_analysis,
            cpv_analysis,
            risk_factors
        )
        
        # Generate risk flags
        risk_flags = self._generate_frequent_winner_flags(
            frequency_analysis,
            concentration_analysis,
            geographic_analysis,
            cpv_analysis,
            risk_factors
        )
        
        detailed_analysis = {
            "winning_company": {
                "id": winning_company.id,
                "name": winning_company.name,
                "cui": winning_company.cui
            },
            "frequency_analysis": frequency_analysis,
            "concentration_analysis": concentration_analysis,
            "geographic_analysis": geographic_analysis,
            "cpv_analysis": cpv_analysis,
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
        """Analyze batch of tenders for frequent winner patterns"""
        
        results = []
        
        # Get all winning companies in batch
        winning_companies = set()
        for tender in tenders:
            winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
            if winning_bid and winning_bid.company:
                winning_companies.add(winning_bid.company.id)
        
        # Pre-calculate market statistics for efficiency
        market_stats = self._calculate_batch_market_stats(tenders, db)
        
        for tender in tenders:
            result = self.analyze_tender(tender, db)
            
            # Enhance with batch context
            if result.detailed_analysis.get("winning_company"):
                company_id = result.detailed_analysis["winning_company"]["id"]
                if company_id in market_stats:
                    result.detailed_analysis["batch_market_stats"] = market_stats[company_id]
            
            results.append(result)
        
        return results
    
    def _analyze_winner_frequency(self, company: Company, tender: Tender, 
                                db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how frequently a company wins contracts"""
        
        # Get time windows for analysis
        current_date = datetime.utcnow()
        one_year_ago = current_date - timedelta(days=365)
        six_months_ago = current_date - timedelta(days=180)
        
        # Get all awards for this company
        recent_awards = db.query(TenderAward).join(Company).filter(
            and_(
                Company.id == company.id,
                TenderAward.award_date >= one_year_ago,
                TenderAward.tender_id != tender.id
            )
        ).all()
        
        # Get all tenders this company participated in
        recent_bids = db.query(TenderBid).join(Company).filter(
            and_(
                Company.id == company.id,
                TenderBid.bid_date >= one_year_ago,
                TenderBid.tender_id != tender.id
            )
        ).all()
        
        # Calculate win rate
        total_bids = len(recent_bids)
        total_wins = len(recent_awards)
        win_rate = total_wins / total_bids if total_bids > 0 else 0
        
        # Calculate recent activity
        recent_awards_6m = [a for a in recent_awards if a.award_date >= six_months_ago]
        recent_bids_6m = [b for b in recent_bids if b.bid_date >= six_months_ago]
        
        recent_win_rate = len(recent_awards_6m) / len(recent_bids_6m) if recent_bids_6m else 0
        
        # Calculate value concentration
        award_values = [float(a.awarded_amount) for a in recent_awards if a.awarded_amount]
        total_value = sum(award_values)
        avg_award_value = np.mean(award_values) if award_values else 0
        
        # Get industry benchmarks
        industry_benchmarks = self._get_industry_benchmarks(company, db)
        
        analysis = {
            "total_bids_12m": total_bids,
            "total_wins_12m": total_wins,
            "win_rate_12m": win_rate,
            "recent_bids_6m": len(recent_bids_6m),
            "recent_wins_6m": len(recent_awards_6m),
            "recent_win_rate_6m": recent_win_rate,
            "total_value_12m": total_value,
            "avg_award_value": avg_award_value,
            "industry_benchmarks": industry_benchmarks
        }
        
        # Set risk factors
        if win_rate > self.config.frequent_winner_threshold:
            risk_factors["high_win_rate"] = True
        
        if recent_win_rate > 0.8:
            risk_factors["very_high_recent_win_rate"] = True
        
        if (industry_benchmarks.get("avg_win_rate", 0) > 0 and 
            win_rate > industry_benchmarks["avg_win_rate"] * 2):
            risk_factors["win_rate_above_industry_average"] = True
        
        return analysis
    
    def _analyze_market_concentration(self, company: Company, tender: Tender,
                                    db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market concentration for this company"""
        
        # Get market context based on CPV code and contracting authority
        market_tenders = self._get_market_tenders(tender, db)
        
        if len(market_tenders) < self.config.min_sample_size_frequency_analysis:
            return {"analysis": "insufficient_market_data", "market_size": len(market_tenders)}
        
        # Calculate market share
        company_wins = 0
        total_contracts = 0
        total_value = 0
        company_value = 0
        
        winner_counts = defaultdict(int)
        winner_values = defaultdict(float)
        
        for market_tender in market_tenders:
            winning_bid = next((bid for bid in market_tender.bids if bid.is_winner), None)
            if winning_bid and winning_bid.company:
                total_contracts += 1
                winner_counts[winning_bid.company.id] += 1
                
                if winning_bid.bid_amount:
                    value = float(winning_bid.bid_amount)
                    total_value += value
                    winner_values[winning_bid.company.id] += value
                    
                    if winning_bid.company.id == company.id:
                        company_value += value
                
                if winning_bid.company.id == company.id:
                    company_wins += 1
        
        # Calculate market share metrics
        market_share_count = company_wins / total_contracts if total_contracts > 0 else 0
        market_share_value = company_value / total_value if total_value > 0 else 0
        
        # Calculate market concentration (HHI)
        hhi = RiskAnalysisUtils.calculate_market_concentration(
            [winner_id for winner_id, count in winner_counts.items() for _ in range(count)]
        )
        
        # Calculate dominant player threshold
        sorted_winners = sorted(winner_counts.items(), key=lambda x: x[1], reverse=True)
        top_3_share = sum(count for _, count in sorted_winners[:3]) / total_contracts if total_contracts > 0 else 0
        
        analysis = {
            "market_size": len(market_tenders),
            "total_contracts": total_contracts,
            "company_wins": company_wins,
            "market_share_count": market_share_count,
            "market_share_value": market_share_value,
            "total_market_value": total_value,
            "company_total_value": company_value,
            "hhi": hhi,
            "top_3_market_share": top_3_share,
            "unique_winners": len(winner_counts)
        }
        
        # Set risk factors
        if market_share_count > 0.5:
            risk_factors["dominant_market_position"] = True
        
        if market_share_count > 0.3:
            risk_factors["strong_market_position"] = True
        
        if hhi > 0.25:  # Highly concentrated market
            risk_factors["highly_concentrated_market"] = True
        
        return analysis
    
    def _analyze_geographic_concentration(self, company: Company, tender: Tender,
                                        db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze geographic concentration of wins"""
        
        # Get company's recent wins with geographic info
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        company_awards = db.query(TenderAward).join(Tender).join(ContractingAuthority).filter(
            and_(
                TenderAward.company_id == company.id,
                TenderAward.award_date >= cutoff_date,
                ContractingAuthority.county.isnot(None)
            )
        ).all()
        
        if not company_awards:
            return {"analysis": "no_geographic_data"}
        
        # Count wins by county and city
        county_counts = defaultdict(int)
        city_counts = defaultdict(int)
        
        for award in company_awards:
            if award.tender and award.tender.contracting_authority:
                authority = award.tender.contracting_authority
                if authority.county:
                    county_counts[authority.county] += 1
                if authority.city:
                    city_counts[authority.city] += 1
        
        total_awards = len(company_awards)
        
        # Calculate concentration metrics
        top_county_share = max(county_counts.values()) / total_awards if county_counts else 0
        top_city_share = max(city_counts.values()) / total_awards if city_counts else 0
        
        # Calculate geographic diversity
        unique_counties = len(county_counts)
        unique_cities = len(city_counts)
        
        analysis = {
            "total_awards": total_awards,
            "unique_counties": unique_counties,
            "unique_cities": unique_cities,
            "top_county_share": top_county_share,
            "top_city_share": top_city_share,
            "county_distribution": dict(county_counts),
            "city_distribution": dict(city_counts)
        }
        
        # Set risk factors
        if top_county_share > 0.7:
            risk_factors["high_geographic_concentration"] = True
        
        if unique_counties == 1 and total_awards > 5:
            risk_factors["single_county_concentration"] = True
        
        return analysis
    
    def _analyze_cpv_specialization(self, company: Company, tender: Tender,
                                   db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CPV code specialization patterns"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        # Get company's recent awards with CPV codes
        company_awards = db.query(TenderAward).join(Tender).filter(
            and_(
                TenderAward.company_id == company.id,
                TenderAward.award_date >= cutoff_date,
                Tender.cpv_code.isnot(None)
            )
        ).all()
        
        if not company_awards:
            return {"analysis": "no_cpv_data"}
        
        # Count awards by CPV categories
        cpv_counts = defaultdict(int)
        cpv_parent_counts = defaultdict(int)
        
        for award in company_awards:
            if award.tender and award.tender.cpv_code:
                cpv_code = award.tender.cpv_code
                cpv_counts[cpv_code] += 1
                
                # Parent CPV (first 4 digits)
                parent_cpv = cpv_code[:4] if len(cpv_code) >= 4 else cpv_code
                cpv_parent_counts[parent_cpv] += 1
        
        total_awards = len(company_awards)
        
        # Calculate specialization metrics
        top_cpv_share = max(cpv_counts.values()) / total_awards if cpv_counts else 0
        top_parent_cpv_share = max(cpv_parent_counts.values()) / total_awards if cpv_parent_counts else 0
        
        # Calculate diversity
        unique_cpvs = len(cpv_counts)
        unique_parent_cpvs = len(cpv_parent_counts)
        
        analysis = {
            "total_awards": total_awards,
            "unique_cpvs": unique_cpvs,
            "unique_parent_cpvs": unique_parent_cpvs,
            "top_cpv_share": top_cpv_share,
            "top_parent_cpv_share": top_parent_cpv_share,
            "cpv_distribution": dict(cpv_counts),
            "parent_cpv_distribution": dict(cpv_parent_counts)
        }
        
        # Set risk factors
        if top_cpv_share > 0.8:
            risk_factors["high_cpv_specialization"] = True
        
        if unique_parent_cpvs == 1 and total_awards > 5:
            risk_factors["single_category_specialization"] = True
        
        return analysis
    
    def _get_market_tenders(self, tender: Tender, db: Session) -> List[Tender]:
        """Get tenders in the same market for comparison"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=365 * 2)
        
        # Define market based on CPV code and optionally contracting authority
        market_query = db.query(Tender).filter(
            and_(
                Tender.cpv_code == tender.cpv_code,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        )
        
        market_tenders = market_query.all()
        
        # If market is too small, expand to parent CPV
        if len(market_tenders) < self.config.min_sample_size_frequency_analysis and tender.cpv_code:
            parent_cpv = tender.cpv_code[:6]
            
            expanded_query = db.query(Tender).filter(
                and_(
                    Tender.cpv_code.like(f"{parent_cpv}%"),
                    Tender.publication_date >= cutoff_date,
                    Tender.id != tender.id
                )
            )
            
            market_tenders = expanded_query.all()
        
        return market_tenders
    
    def _get_industry_benchmarks(self, company: Company, db: Session) -> Dict[str, Any]:
        """Get industry benchmarks for win rates"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        # Get all companies' win rates in similar markets
        all_bids = db.query(TenderBid).join(Tender).filter(
            and_(
                TenderBid.bid_date >= cutoff_date,
                TenderBid.company_id != company.id
            )
        ).all()
        
        if not all_bids:
            return {}
        
        # Calculate win rates for all companies
        company_stats = defaultdict(lambda: {"bids": 0, "wins": 0})
        
        for bid in all_bids:
            company_stats[bid.company_id]["bids"] += 1
            if bid.is_winner:
                company_stats[bid.company_id]["wins"] += 1
        
        # Calculate industry statistics
        win_rates = []
        for stats in company_stats.values():
            if stats["bids"] > 0:
                win_rates.append(stats["wins"] / stats["bids"])
        
        if not win_rates:
            return {}
        
        return {
            "avg_win_rate": np.mean(win_rates),
            "median_win_rate": np.median(win_rates),
            "std_win_rate": np.std(win_rates),
            "sample_size": len(win_rates)
        }
    
    def _calculate_frequent_winner_risk_score(self, frequency_analysis: Dict[str, Any],
                                            concentration_analysis: Dict[str, Any],
                                            geographic_analysis: Dict[str, Any],
                                            cpv_analysis: Dict[str, Any],
                                            risk_factors: Dict[str, Any]) -> float:
        """Calculate risk score for frequent winner patterns"""
        
        score = 0.0
        
        # Frequency-based scoring
        win_rate = frequency_analysis.get("win_rate_12m", 0)
        if win_rate > 0.8:
            score += 40.0
        elif win_rate > 0.6:
            score += 30.0
        elif win_rate > 0.4:
            score += 20.0
        
        # Recent activity boost
        recent_win_rate = frequency_analysis.get("recent_win_rate_6m", 0)
        if recent_win_rate > 0.9:
            score += 20.0
        elif recent_win_rate > 0.7:
            score += 15.0
        
        # Market concentration scoring
        market_share = concentration_analysis.get("market_share_count", 0)
        if market_share > 0.5:
            score += 35.0
        elif market_share > 0.3:
            score += 25.0
        elif market_share > 0.2:
            score += 15.0
        
        # Market concentration (HHI)
        hhi = concentration_analysis.get("hhi", 0)
        if hhi > 0.25:
            score += 20.0
        elif hhi > 0.15:
            score += 10.0
        
        # Geographic concentration
        top_county_share = geographic_analysis.get("top_county_share", 0)
        if top_county_share > 0.8:
            score += 15.0
        elif top_county_share > 0.6:
            score += 10.0
        
        # CPV specialization
        top_cpv_share = cpv_analysis.get("top_cpv_share", 0)
        if top_cpv_share > 0.8:
            score += 10.0
        
        return min(100.0, score)
    
    def _generate_frequent_winner_flags(self, frequency_analysis: Dict[str, Any],
                                      concentration_analysis: Dict[str, Any],
                                      geographic_analysis: Dict[str, Any],
                                      cpv_analysis: Dict[str, Any],
                                      risk_factors: Dict[str, Any]) -> List[str]:
        """Generate risk flags for frequent winner patterns"""
        
        flags = []
        
        if risk_factors.get("high_win_rate"):
            flags.append("HIGH_WIN_RATE")
        
        if risk_factors.get("very_high_recent_win_rate"):
            flags.append("VERY_HIGH_RECENT_WIN_RATE")
        
        if risk_factors.get("win_rate_above_industry_average"):
            flags.append("WIN_RATE_ABOVE_INDUSTRY_AVERAGE")
        
        if risk_factors.get("dominant_market_position"):
            flags.append("DOMINANT_MARKET_POSITION")
        
        if risk_factors.get("strong_market_position"):
            flags.append("STRONG_MARKET_POSITION")
        
        if risk_factors.get("highly_concentrated_market"):
            flags.append("HIGHLY_CONCENTRATED_MARKET")
        
        if risk_factors.get("high_geographic_concentration"):
            flags.append("HIGH_GEOGRAPHIC_CONCENTRATION")
        
        if risk_factors.get("single_county_concentration"):
            flags.append("SINGLE_COUNTY_CONCENTRATION")
        
        if risk_factors.get("high_cpv_specialization"):
            flags.append("HIGH_CPV_SPECIALIZATION")
        
        if risk_factors.get("single_category_specialization"):
            flags.append("SINGLE_CATEGORY_SPECIALIZATION")
        
        return flags
    
    def _calculate_batch_market_stats(self, tenders: List[Tender], db: Session) -> Dict[int, Dict[str, Any]]:
        """Calculate market statistics for batch processing"""
        
        stats = {}
        
        # Group tenders by winning company
        company_tenders = defaultdict(list)
        for tender in tenders:
            winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
            if winning_bid and winning_bid.company:
                company_tenders[winning_bid.company.id].append(tender)
        
        # Calculate stats for each company
        for company_id, company_tender_list in company_tenders.items():
            stats[company_id] = {
                "batch_wins": len(company_tender_list),
                "batch_win_rate": len(company_tender_list) / len(tenders),
                "batch_total_value": sum(
                    float(bid.bid_amount) for tender in company_tender_list
                    for bid in tender.bids if bid.is_winner and bid.bid_amount
                )
            }
        
        return stats
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm"""
        return {
            "name": self.algorithm_name,
            "version": self.algorithm_version,
            "description": "Detects companies with suspiciously high win rates and market concentration",
            "risk_factors": [
                "High win rates",
                "Market concentration",
                "Geographic concentration", 
                "CPV specialization",
                "Industry benchmark comparison"
            ],
            "parameters": {
                "frequent_winner_threshold": self.config.frequent_winner_threshold,
                "weight": self.config.frequent_winner_weight,
                "min_sample_size": self.config.min_sample_size_frequency_analysis
            }
        }