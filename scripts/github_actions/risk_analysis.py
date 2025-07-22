#!/usr/bin/env python3
"""
Risk Analysis Script for GitHub Actions
Performs batch risk analysis on tender data with time constraints
"""

import os
import sys
import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitHubActionsRiskAnalysis:
    """Risk analysis optimized for GitHub Actions environment"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.api_base_url = os.getenv('API_BASE_URL', 'https://api.procurement-platform.me')
        self.api_token = os.getenv('API_TOKEN', '')
        self.sentry_dsn = os.getenv('SENTRY_DSN')
        
        # Limits for GitHub Actions
        self.max_execution_time = 18 * 60  # 18 minutes for risk analysis
        self.max_tenders_per_run = 500
        self.batch_size = 25
        
        self.start_time = datetime.now()
        
        # Initialize Sentry if available
        if self.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.init(dsn=self.sentry_dsn, environment="github_actions")
            except ImportError:
                logger.warning("Sentry SDK not available")
    
    def should_continue(self) -> bool:
        """Check if we should continue processing (time limit check)"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed < self.max_execution_time
    
    async def trigger_api_analysis(self) -> Dict:
        """Trigger risk analysis via API endpoint"""
        try:
            headers = {}
            if self.api_token:
                headers['Authorization'] = f'Bearer {self.api_token}'
            
            payload = {
                "analysis_type": "batch_risk_analysis",
                "max_tenders": self.max_tenders_per_run,
                "batch_size": self.batch_size,
                "github_actions": True,
                "timeout_minutes": 15
            }
            
            logger.info(f"Triggering risk analysis via API")
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/admin/trigger-risk-analysis",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Risk analysis API response: {result}")
                    return result
                else:
                    error_msg = f"Risk analysis API failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                    
        except Exception as e:
            logger.error(f"Exception during API risk analysis: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def fallback_direct_analysis(self) -> Dict:
        """Fallback to direct risk analysis if API is unavailable"""
        logger.info("Attempting fallback direct risk analysis")
        
        try:
            import asyncpg
            import numpy as np
            
            conn = await asyncpg.connect(self.database_url)
            
            try:
                # Get tenders that need risk analysis (recently added or updated)
                cutoff_date = datetime.now() - timedelta(hours=24)
                
                tenders_query = """
                    SELECT id, title, estimated_value, contracting_authority, 
                           winner_name, participants_count, publication_date,
                           award_date, cpv_code
                    FROM tenders 
                    WHERE (updated_at > $1 OR risk_score IS NULL)
                    AND status IN ('awarded', 'completed')
                    ORDER BY updated_at DESC
                    LIMIT $2
                """
                
                tenders = await conn.fetch(tenders_query, cutoff_date, self.max_tenders_per_run)
                logger.info(f"Found {len(tenders)} tenders for risk analysis")
                
                if not tenders:
                    return {"success": True, "analyzed_count": 0, "message": "No tenders need analysis"}
                
                analyzed_count = 0
                risk_scores_updated = 0
                
                # Process tenders in batches
                for i in range(0, len(tenders), self.batch_size):
                    if not self.should_continue():
                        logger.warning("Time limit approaching, stopping analysis")
                        break
                    
                    batch = tenders[i:i + self.batch_size]
                    
                    # Analyze batch
                    batch_results = await self.analyze_tender_batch(conn, batch)
                    analyzed_count += len(batch)
                    risk_scores_updated += batch_results['updated_count']
                    
                    logger.info(f"Analyzed {analyzed_count}/{len(tenders)} tenders")
                
                # Update analysis timestamp
                await conn.execute(
                    """
                    INSERT INTO sync_status (source, last_sync, records_processed, status, notes)
                    VALUES ('risk_analysis', $1, $2, 'completed', 'GitHub Actions risk analysis')
                    ON CONFLICT (source) DO UPDATE SET
                        last_sync = $1,
                        records_processed = $2,
                        status = 'completed',
                        notes = 'GitHub Actions risk analysis',
                        updated_at = NOW()
                    """,
                    datetime.now(),
                    analyzed_count
                )
                
                return {
                    "success": True,
                    "method": "direct_analysis",
                    "analyzed_count": analyzed_count,
                    "risk_scores_updated": risk_scores_updated,
                    "total_available": len(tenders)
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Fallback risk analysis failed: {str(e)}")
            return {"success": False, "error": str(e), "method": "direct_analysis"}
    
    async def analyze_tender_batch(self, conn, batch: List) -> Dict:
        """Analyze a batch of tenders for risk factors"""
        updated_count = 0
        
        for tender in batch:
            try:
                risk_score = await self.calculate_risk_score(tender)
                risk_factors = await self.identify_risk_factors(tender)
                
                # Update tender with risk analysis
                await conn.execute(
                    """
                    UPDATE tenders 
                    SET risk_score = $1, 
                        risk_factors = $2,
                        risk_analysis_date = $3
                    WHERE id = $4
                    """,
                    risk_score,
                    risk_factors,
                    datetime.now(),
                    tender['id']
                )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze tender {tender['id']}: {str(e)}")
                continue
        
        return {"updated_count": updated_count}
    
    async def calculate_risk_score(self, tender: Dict) -> float:
        """Calculate risk score for a tender (simplified algorithm)"""
        risk_score = 0.0
        
        try:
            # Single bidder risk
            if tender.get('participants_count', 0) <= 1:
                risk_score += 0.3
            
            # High value risk
            estimated_value = tender.get('estimated_value', 0) or 0
            if estimated_value > 1000000:  # Over 1M EUR
                risk_score += 0.2
            
            # Quick award risk (awarded within 1 day of publication)
            if tender.get('publication_date') and tender.get('award_date'):
                pub_date = tender['publication_date']
                award_date = tender['award_date']
                if isinstance(pub_date, datetime) and isinstance(award_date, datetime):
                    days_diff = (award_date - pub_date).days
                    if days_diff <= 1:
                        risk_score += 0.25
            
            # Authority concentration risk (simplified check)
            authority = tender.get('contracting_authority', '').lower()
            if any(keyword in authority for keyword in ['local', 'municipal', 'comuna']):
                risk_score += 0.1
            
            # CPV code risk (construction and IT services often have higher risk)
            cpv_code = tender.get('cpv_code', '')
            if cpv_code.startswith(('45', '72', '48')):  # Construction, IT, Software
                risk_score += 0.15
            
            # Cap at 1.0
            risk_score = min(risk_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Error calculating risk score: {str(e)}")
            risk_score = 0.0
        
        return round(risk_score, 3)
    
    async def identify_risk_factors(self, tender: Dict) -> List[str]:
        """Identify specific risk factors for a tender"""
        factors = []
        
        try:
            if tender.get('participants_count', 0) <= 1:
                factors.append('single_bidder')
            
            estimated_value = tender.get('estimated_value', 0) or 0
            if estimated_value > 1000000:
                factors.append('high_value')
            
            if tender.get('publication_date') and tender.get('award_date'):
                pub_date = tender['publication_date']
                award_date = tender['award_date']
                if isinstance(pub_date, datetime) and isinstance(award_date, datetime):
                    days_diff = (award_date - pub_date).days
                    if days_diff <= 1:
                        factors.append('quick_award')
            
            winner = tender.get('winner_name', '').lower()
            if any(keyword in winner for keyword in ['srl', 'sa', 'pfa']):
                # Check for potential shell companies (very basic check)
                if len(winner.split()) <= 3:
                    factors.append('potential_shell_company')
            
        except Exception as e:
            logger.warning(f"Error identifying risk factors: {str(e)}")
        
        return factors
    
    async def run_analysis(self) -> Dict:
        """Main analysis execution"""
        logger.info("Starting risk analysis")
        
        # Try API analysis first
        result = await self.trigger_api_analysis()
        
        if result.get("success"):
            logger.info("Risk analysis completed successfully via API")
            return result
        
        logger.warning("API analysis failed, attempting fallback method")
        
        # Fallback to direct analysis if API fails
        result = await self.fallback_direct_analysis()
        
        if result.get("success"):
            logger.info("Risk analysis completed successfully via fallback")
        else:
            logger.error("All analysis methods failed")
        
        return result

async def main():
    """Main execution function"""
    analysis_runner = GitHubActionsRiskAnalysis()
    
    try:
        result = await analysis_runner.run_analysis()
        
        # Log final result
        if result.get("success"):
            logger.info(f"✅ Risk analysis successful: {result}")
            
            # Report metrics
            analyzed = result.get("analyzed_count", 0)
            updated = result.get("risk_scores_updated", 0)
            method = result.get("method", "api")
            
            print(f"RISK_ANALYSIS_RESULT=success")
            print(f"RISK_TENDERS_ANALYZED={analyzed}")
            print(f"RISK_SCORES_UPDATED={updated}")
            print(f"RISK_ANALYSIS_METHOD={method}")
            
        else:
            logger.error(f"❌ Risk analysis failed: {result}")
            print(f"RISK_ANALYSIS_RESULT=failed")
            print(f"RISK_ANALYSIS_ERROR={result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Critical error in risk analysis: {str(e)}")
        print(f"RISK_ANALYSIS_RESULT=error")
        print(f"RISK_ANALYSIS_ERROR={str(e)}")
        
        # Send to Sentry if available
        if analysis_runner.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(e)
            except:
                pass
        
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())