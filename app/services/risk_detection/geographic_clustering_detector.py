"""
Geographic Clustering Detection Algorithm

This module implements risk detection for unusual geographic patterns in procurement,
including local monopolies and suspicious clustering of awards.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from app.db.models import Tender, TenderBid, TenderAward, Company, ContractingAuthority, CPVCode
from .base import BaseRiskDetector, RiskDetectionResult, RiskDetectionConfig


class GeographicClusteringDetector(BaseRiskDetector):
    """Detector for geographic clustering patterns and local monopolies"""
    
    def __init__(self, config: RiskDetectionConfig):
        super().__init__(config)
        self.algorithm_name = "Geographic Clustering Detection"
        self.algorithm_version = "1.0.0"
        
        # Romanian counties for reference
        self.romanian_counties = [
            "ALBA", "ARAD", "ARGEȘ", "BACĂU", "BIHOR", "BISTRIȚA-NĂSĂUD", "BOTOȘANI",
            "BRĂILA", "BRAȘOV", "BUZĂU", "CARAȘ-SEVERIN", "CĂLĂRAȘI", "CLUJ", "CONSTANȚA",
            "COVASNA", "DÂMBOVIȚA", "DOLJ", "GALAȚI", "GIURGIU", "GORJ", "HARGHITA",
            "HUNEDOARA", "IALOMIȚA", "IAȘI", "ILFOV", "MARAMUREȘ", "MEHEDINȚI", "MUREȘ",
            "NEAMȚ", "OLT", "PRAHOVA", "SĂLAJ", "SATU MARE", "SIBIU", "SUCEAVA",
            "TELEORMAN", "TIMIȘ", "TULCEA", "VÂLCEA", "VASLUI", "VRANCEA", "BUCUREȘTI"
        ]
    
    def analyze_tender(self, tender: Tender, db: Session) -> RiskDetectionResult:
        """Analyze a tender for geographic clustering patterns"""
        
        if not tender.contracting_authority or not tender.contracting_authority.county:
            return RiskDetectionResult(
                risk_score=0.0,
                risk_level="MINIMAL",
                risk_flags=["NO_GEOGRAPHIC_DATA"],
                detailed_analysis={
                    "algorithm": self.algorithm_name,
                    "analysis_type": "single_tender",
                    "reason": "No geographic data available"
                }
            )
        
        authority = tender.contracting_authority
        risk_flags = []
        risk_factors = {}
        
        # Analyze local market concentration
        local_concentration = self._analyze_local_market_concentration(
            tender, authority, db, risk_factors
        )
        
        # Analyze cross-regional patterns
        cross_regional = self._analyze_cross_regional_patterns(
            tender, authority, db, risk_factors
        )
        
        # Analyze bidder geographic distribution
        bidder_distribution = self._analyze_bidder_geographic_distribution(
            tender, authority, db, risk_factors
        )
        
        # Analyze winner geographic patterns
        winner_patterns = self._analyze_winner_geographic_patterns(
            tender, authority, db, risk_factors
        )
        
        # Calculate risk score
        risk_score = self._calculate_geographic_risk_score(
            local_concentration,
            cross_regional,
            bidder_distribution,
            winner_patterns,
            risk_factors
        )
        
        # Generate risk flags
        risk_flags = self._generate_geographic_flags(
            local_concentration,
            cross_regional,
            bidder_distribution,
            winner_patterns,
            risk_factors
        )
        
        detailed_analysis = {
            "contracting_authority": {
                "county": authority.county,
                "city": authority.city,
                "name": authority.name
            },
            "local_concentration": local_concentration,
            "cross_regional_patterns": cross_regional,
            "bidder_distribution": bidder_distribution,
            "winner_patterns": winner_patterns,
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
        """Analyze batch of tenders for geographic clustering patterns"""
        
        results = []
        
        # Pre-calculate regional statistics for efficiency
        regional_stats = self._calculate_regional_statistics(tenders, db)
        
        # Group tenders by county for better analysis
        county_groups = defaultdict(list)
        for tender in tenders:
            if tender.contracting_authority and tender.contracting_authority.county:
                county_groups[tender.contracting_authority.county].append(tender)
        
        for county, county_tenders in county_groups.items():
            # Analyze county-level patterns
            county_patterns = self._analyze_county_patterns(county_tenders, db)
            
            for tender in county_tenders:
                result = self.analyze_tender(tender, db)
                
                # Enhance with county and regional context
                result.detailed_analysis["county_patterns"] = county_patterns
                result.detailed_analysis["regional_stats"] = regional_stats.get(county, {})
                
                results.append(result)
        
        return results
    
    def _analyze_local_market_concentration(self, tender: Tender, authority: ContractingAuthority,
                                          db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze local market concentration in the same county"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        # Get all tenders in the same county
        local_tenders = db.query(Tender).join(ContractingAuthority).filter(
            and_(
                ContractingAuthority.county == authority.county,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        ).all()
        
        if len(local_tenders) < self.config.min_sample_size_geographic_analysis:
            return {
                "analysis": "insufficient_local_data",
                "local_tender_count": len(local_tenders)
            }
        
        # Analyze local winners
        local_winners = defaultdict(int)
        local_winner_values = defaultdict(float)
        total_local_value = 0
        
        for local_tender in local_tenders:
            winning_bid = next((bid for bid in local_tender.bids if bid.is_winner), None)
            if winning_bid and winning_bid.company:
                local_winners[winning_bid.company.id] += 1
                
                if winning_bid.bid_amount:
                    value = float(winning_bid.bid_amount)
                    local_winner_values[winning_bid.company.id] += value
                    total_local_value += value
        
        # Calculate concentration metrics
        total_local_contracts = len([t for t in local_tenders if any(b.is_winner for b in t.bids)])
        
        if total_local_contracts == 0:
            return {"analysis": "no_local_winners"}
        
        # Market concentration
        market_shares = [count / total_local_contracts for count in local_winners.values()]
        hhi = sum(share ** 2 for share in market_shares)
        
        # Top player analysis
        top_winner_id = max(local_winners.keys(), key=lambda x: local_winners[x]) if local_winners else None
        top_winner_share = max(local_winners.values()) / total_local_contracts if local_winners else 0
        top_winner_value_share = 0
        
        if top_winner_id and total_local_value > 0:
            top_winner_value_share = local_winner_values[top_winner_id] / total_local_value
        
        # Check if current tender winner is the top local winner
        current_winner_id = None
        winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
        if winning_bid and winning_bid.company:
            current_winner_id = winning_bid.company.id
        
        is_top_local_winner = current_winner_id == top_winner_id
        
        analysis = {
            "total_local_tenders": len(local_tenders),
            "total_local_contracts": total_local_contracts,
            "unique_local_winners": len(local_winners),
            "hhi": hhi,
            "top_winner_share": top_winner_share,
            "top_winner_value_share": top_winner_value_share,
            "is_top_local_winner": is_top_local_winner,
            "local_winner_distribution": dict(local_winners)
        }
        
        # Set risk factors
        if top_winner_share > 0.6:
            risk_factors["local_market_dominance"] = True
        
        if hhi > 0.25:
            risk_factors["high_local_concentration"] = True
        
        if is_top_local_winner and top_winner_share > 0.4:
            risk_factors["current_winner_dominates_locally"] = True
        
        return analysis
    
    def _analyze_cross_regional_patterns(self, tender: Tender, authority: ContractingAuthority,
                                       db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cross-regional bidding and winning patterns"""
        
        # Get current tender's winning company
        winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
        if not winning_bid or not winning_bid.company:
            return {"analysis": "no_winner_identified"}
        
        winning_company = winning_bid.company
        
        # Get company's geographic distribution of wins
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        company_awards = db.query(TenderAward).join(Tender).join(ContractingAuthority).filter(
            and_(
                TenderAward.company_id == winning_company.id,
                TenderAward.award_date >= cutoff_date,
                ContractingAuthority.county.isnot(None)
            )
        ).all()
        
        if not company_awards:
            return {"analysis": "no_company_geographic_data"}
        
        # Count awards by county
        county_awards = defaultdict(int)
        for award in company_awards:
            if award.tender and award.tender.contracting_authority:
                county = award.tender.contracting_authority.county
                county_awards[county] += 1
        
        # Calculate metrics
        total_awards = len(company_awards)
        unique_counties = len(county_awards)
        home_county_awards = county_awards.get(authority.county, 0)
        home_county_share = home_county_awards / total_awards if total_awards > 0 else 0
        
        # Analyze geographic spread
        max_county_awards = max(county_awards.values()) if county_awards else 0
        geographic_concentration = max_county_awards / total_awards if total_awards > 0 else 0
        
        # Compare with company's registered address
        company_home_county = winning_company.county if hasattr(winning_company, 'county') else None
        is_local_company = company_home_county == authority.county if company_home_county else None
        
        analysis = {
            "total_awards": total_awards,
            "unique_counties": unique_counties,
            "home_county_awards": home_county_awards,
            "home_county_share": home_county_share,
            "geographic_concentration": geographic_concentration,
            "is_local_company": is_local_company,
            "county_distribution": dict(county_awards)
        }
        
        # Set risk factors
        if unique_counties == 1 and total_awards > 3:
            risk_factors["single_county_operation"] = True
        
        if home_county_share > 0.8 and total_awards > 5:
            risk_factors["high_local_concentration"] = True
        
        if not is_local_company and home_county_share > 0.6:
            risk_factors["non_local_company_dominance"] = True
        
        return analysis
    
    def _analyze_bidder_geographic_distribution(self, tender: Tender, authority: ContractingAuthority,
                                              db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze geographic distribution of bidders"""
        
        # Get bidder companies with geographic info
        bidder_companies = []
        for bid in tender.bids:
            if bid.company:
                bidder_companies.append(bid.company)
        
        if not bidder_companies:
            return {"analysis": "no_bidders"}
        
        # Get geographic info for bidders (from their recent awards)
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        bidder_counties = {}
        for company in bidder_companies:
            # Get company's most frequent county of operation
            company_awards = db.query(TenderAward).join(Tender).join(ContractingAuthority).filter(
                and_(
                    TenderAward.company_id == company.id,
                    TenderAward.award_date >= cutoff_date,
                    ContractingAuthority.county.isnot(None)
                )
            ).all()
            
            if company_awards:
                county_counts = defaultdict(int)
                for award in company_awards:
                    if award.tender and award.tender.contracting_authority:
                        county_counts[award.tender.contracting_authority.county] += 1
                
                # Most frequent county
                most_frequent_county = max(county_counts.keys(), key=lambda x: county_counts[x])
                bidder_counties[company.id] = most_frequent_county
        
        # Analyze bidder distribution
        total_bidders = len(bidder_companies)
        local_bidders = sum(1 for county in bidder_counties.values() if county == authority.county)
        local_bidder_rate = local_bidders / total_bidders if total_bidders > 0 else 0
        
        # Count unique counties represented
        unique_bidder_counties = len(set(bidder_counties.values()))
        
        analysis = {
            "total_bidders": total_bidders,
            "local_bidders": local_bidders,
            "local_bidder_rate": local_bidder_rate,
            "unique_bidder_counties": unique_bidder_counties,
            "bidder_county_distribution": dict(Counter(bidder_counties.values()))
        }
        
        # Set risk factors
        if local_bidder_rate > 0.8 and total_bidders > 2:
            risk_factors["predominantly_local_bidders"] = True
        
        if unique_bidder_counties == 1 and total_bidders > 2:
            risk_factors["single_county_bidders"] = True
        
        return analysis
    
    def _analyze_winner_geographic_patterns(self, tender: Tender, authority: ContractingAuthority,
                                          db: Session, risk_factors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze geographic patterns of winners in similar tenders"""
        
        # Get similar tenders (same CPV code)
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        similar_tenders = db.query(Tender).filter(
            and_(
                Tender.cpv_code == tender.cpv_code,
                Tender.publication_date >= cutoff_date,
                Tender.id != tender.id
            )
        ).all()
        
        if len(similar_tenders) < self.config.min_sample_size_geographic_analysis:
            return {
                "analysis": "insufficient_similar_tenders",
                "similar_tender_count": len(similar_tenders)
            }
        
        # Analyze winner patterns by county
        winner_patterns = defaultdict(lambda: defaultdict(int))
        
        for similar_tender in similar_tenders:
            if (similar_tender.contracting_authority and 
                similar_tender.contracting_authority.county):
                
                authority_county = similar_tender.contracting_authority.county
                winning_bid = next((bid for bid in similar_tender.bids if bid.is_winner), None)
                
                if winning_bid and winning_bid.company:
                    # Get winner's primary county
                    winner_awards = db.query(TenderAward).join(Tender).join(ContractingAuthority).filter(
                        and_(
                            TenderAward.company_id == winning_bid.company.id,
                            TenderAward.award_date >= cutoff_date,
                            ContractingAuthority.county.isnot(None)
                        )
                    ).all()
                    
                    if winner_awards:
                        county_counts = defaultdict(int)
                        for award in winner_awards:
                            if award.tender and award.tender.contracting_authority:
                                county_counts[award.tender.contracting_authority.county] += 1
                        
                        winner_primary_county = max(county_counts.keys(), key=lambda x: county_counts[x])
                        winner_patterns[authority_county][winner_primary_county] += 1
        
        # Calculate local winner rates by county
        county_local_rates = {}
        for auth_county, winner_counties in winner_patterns.items():
            total_winners = sum(winner_counties.values())
            local_winners = winner_counties.get(auth_county, 0)
            local_rate = local_winners / total_winners if total_winners > 0 else 0
            county_local_rates[auth_county] = local_rate
        
        # Current tender's county local rate
        current_county_local_rate = county_local_rates.get(authority.county, 0)
        
        # Overall industry local rate
        all_local_rates = list(county_local_rates.values())
        avg_local_rate = np.mean(all_local_rates) if all_local_rates else 0
        
        analysis = {
            "similar_tender_count": len(similar_tenders),
            "county_local_rates": county_local_rates,
            "current_county_local_rate": current_county_local_rate,
            "avg_local_rate": avg_local_rate,
            "winner_patterns": {k: dict(v) for k, v in winner_patterns.items()}
        }
        
        # Set risk factors
        if current_county_local_rate > 0.8:
            risk_factors["high_local_winner_rate"] = True
        
        if current_county_local_rate > avg_local_rate * 1.5:
            risk_factors["above_average_local_rate"] = True
        
        return analysis
    
    def _calculate_geographic_risk_score(self, local_concentration: Dict[str, Any],
                                       cross_regional: Dict[str, Any],
                                       bidder_distribution: Dict[str, Any],
                                       winner_patterns: Dict[str, Any],
                                       risk_factors: Dict[str, Any]) -> float:
        """Calculate geographic clustering risk score"""
        
        score = 0.0
        
        # Local market concentration
        if local_concentration.get("top_winner_share", 0) > 0.6:
            score += 30.0
        elif local_concentration.get("top_winner_share", 0) > 0.4:
            score += 20.0
        
        hhi = local_concentration.get("hhi", 0)
        if hhi > 0.25:
            score += 25.0
        elif hhi > 0.15:
            score += 15.0
        
        # Cross-regional patterns
        if cross_regional.get("unique_counties", 0) == 1:
            score += 20.0
        
        if cross_regional.get("home_county_share", 0) > 0.8:
            score += 15.0
        
        # Bidder distribution
        if bidder_distribution.get("local_bidder_rate", 0) > 0.8:
            score += 15.0
        
        if bidder_distribution.get("unique_bidder_counties", 0) == 1:
            score += 10.0
        
        # Winner patterns
        if winner_patterns.get("current_county_local_rate", 0) > 0.8:
            score += 20.0
        
        avg_local_rate = winner_patterns.get("avg_local_rate", 0)
        current_rate = winner_patterns.get("current_county_local_rate", 0)
        if avg_local_rate > 0 and current_rate > avg_local_rate * 1.5:
            score += 15.0
        
        return min(100.0, score)
    
    def _generate_geographic_flags(self, local_concentration: Dict[str, Any],
                                 cross_regional: Dict[str, Any],
                                 bidder_distribution: Dict[str, Any],
                                 winner_patterns: Dict[str, Any],
                                 risk_factors: Dict[str, Any]) -> List[str]:
        """Generate risk flags for geographic patterns"""
        
        flags = []
        
        if risk_factors.get("local_market_dominance"):
            flags.append("LOCAL_MARKET_DOMINANCE")
        
        if risk_factors.get("high_local_concentration"):
            flags.append("HIGH_LOCAL_CONCENTRATION")
        
        if risk_factors.get("current_winner_dominates_locally"):
            flags.append("CURRENT_WINNER_DOMINATES_LOCALLY")
        
        if risk_factors.get("single_county_operation"):
            flags.append("SINGLE_COUNTY_OPERATION")
        
        if risk_factors.get("non_local_company_dominance"):
            flags.append("NON_LOCAL_COMPANY_DOMINANCE")
        
        if risk_factors.get("predominantly_local_bidders"):
            flags.append("PREDOMINANTLY_LOCAL_BIDDERS")
        
        if risk_factors.get("single_county_bidders"):
            flags.append("SINGLE_COUNTY_BIDDERS")
        
        if risk_factors.get("high_local_winner_rate"):
            flags.append("HIGH_LOCAL_WINNER_RATE")
        
        if risk_factors.get("above_average_local_rate"):
            flags.append("ABOVE_AVERAGE_LOCAL_RATE")
        
        return flags
    
    def _calculate_regional_statistics(self, tenders: List[Tender], db: Session) -> Dict[str, Dict[str, Any]]:
        """Calculate regional statistics for batch processing"""
        
        stats = {}
        
        # Group tenders by county
        county_groups = defaultdict(list)
        for tender in tenders:
            if tender.contracting_authority and tender.contracting_authority.county:
                county_groups[tender.contracting_authority.county].append(tender)
        
        for county, county_tenders in county_groups.items():
            county_stats = {
                "tender_count": len(county_tenders),
                "unique_authorities": len(set(t.contracting_authority.id for t in county_tenders)),
                "avg_bid_count": np.mean([len(t.bids) for t in county_tenders]),
                "local_winner_rate": 0.0
            }
            
            # Calculate local winner rate
            local_winners = 0
            total_winners = 0
            
            for tender in county_tenders:
                winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
                if winning_bid and winning_bid.company:
                    total_winners += 1
                    # Check if winner is local (simplified check)
                    if winning_bid.company.county == county:
                        local_winners += 1
            
            if total_winners > 0:
                county_stats["local_winner_rate"] = local_winners / total_winners
            
            stats[county] = county_stats
        
        return stats
    
    def _analyze_county_patterns(self, county_tenders: List[Tender], db: Session) -> Dict[str, Any]:
        """Analyze patterns within a county"""
        
        if not county_tenders:
            return {}
        
        # Winner concentration
        winners = defaultdict(int)
        for tender in county_tenders:
            winning_bid = next((bid for bid in tender.bids if bid.is_winner), None)
            if winning_bid and winning_bid.company:
                winners[winning_bid.company.id] += 1
        
        total_contracts = len(winners)
        unique_winners = len(set(winners.keys()))
        
        # Market concentration
        if total_contracts > 0:
            market_shares = [count / total_contracts for count in winners.values()]
            hhi = sum(share ** 2 for share in market_shares)
            top_winner_share = max(winners.values()) / total_contracts if winners else 0
        else:
            hhi = 0
            top_winner_share = 0
        
        return {
            "total_contracts": total_contracts,
            "unique_winners": unique_winners,
            "hhi": hhi,
            "top_winner_share": top_winner_share,
            "winner_distribution": dict(winners)
        }
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm"""
        return {
            "name": self.algorithm_name,
            "version": self.algorithm_version,
            "description": "Detects suspicious geographic patterns and local monopolies in procurement",
            "risk_factors": [
                "Local market concentration",
                "Cross-regional patterns",
                "Bidder geographic distribution",
                "Winner geographic patterns",
                "County-level market dominance"
            ],
            "parameters": {
                "geographic_clustering_threshold": self.config.geographic_clustering_threshold,
                "weight": self.config.geographic_clustering_weight,
                "min_sample_size": self.config.min_sample_size_geographic_analysis
            }
        }