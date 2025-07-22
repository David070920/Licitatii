#!/usr/bin/env python3
"""
Report Generation Script for GitHub Actions
Generates risk analysis reports and dashboard data
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate reports and dashboard data for the Romanian Procurement Platform"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.api_base_url = os.getenv('API_BASE_URL', 'https://api.procurement-platform.me')
        self.api_token = os.getenv('API_TOKEN', '')
    
    async def generate_risk_summary_report(self, conn) -> Dict:
        """Generate risk analysis summary report"""
        try:
            # Overall risk statistics
            risk_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_tenders,
                    COUNT(CASE WHEN risk_score > 0.7 THEN 1 END) as high_risk,
                    COUNT(CASE WHEN risk_score BETWEEN 0.4 AND 0.7 THEN 1 END) as medium_risk,
                    COUNT(CASE WHEN risk_score < 0.4 THEN 1 END) as low_risk,
                    AVG(risk_score) as avg_risk_score,
                    MAX(risk_score) as max_risk_score,
                    COUNT(CASE WHEN risk_analysis_date >= NOW() - INTERVAL '7 days' THEN 1 END) as analyzed_this_week
                FROM tenders 
                WHERE risk_score IS NOT NULL
            """)
            
            # Top risk factors
            risk_factors_query = """
                SELECT 
                    unnest(risk_factors) as risk_factor,
                    COUNT(*) as frequency
                FROM tenders 
                WHERE risk_factors IS NOT NULL 
                AND risk_factors != '{}'
                AND risk_analysis_date >= NOW() - INTERVAL '30 days'
                GROUP BY unnest(risk_factors)
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """
            risk_factors = await conn.fetch(risk_factors_query)
            
            # High-risk tenders by authority
            high_risk_authorities = await conn.fetch("""
                SELECT 
                    contracting_authority,
                    COUNT(*) as high_risk_count,
                    AVG(risk_score) as avg_risk_score,
                    SUM(estimated_value) as total_value
                FROM tenders 
                WHERE risk_score > 0.7
                AND contracting_authority IS NOT NULL
                GROUP BY contracting_authority
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, AVG(risk_score) DESC
                LIMIT 15
            """)
            
            # Recent high-risk tenders
            recent_high_risk = await conn.fetch("""
                SELECT 
                    id, title, contracting_authority, winner_name,
                    estimated_value, risk_score, risk_factors,
                    publication_date, award_date
                FROM tenders 
                WHERE risk_score > 0.6
                AND risk_analysis_date >= NOW() - INTERVAL '7 days'
                ORDER BY risk_score DESC, estimated_value DESC
                LIMIT 20
            """)
            
            return {
                'overall_stats': dict(risk_stats) if risk_stats else {},
                'risk_factors': [dict(row) for row in risk_factors],
                'high_risk_authorities': [dict(row) for row in high_risk_authorities],
                'recent_high_risk_tenders': [dict(row) for row in recent_high_risk],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate risk summary report: {str(e)}")
            return {'error': str(e)}
    
    async def generate_platform_statistics(self, conn) -> Dict:
        """Generate platform usage and data statistics"""
        try:
            # Data volume statistics
            data_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_tenders,
                    COUNT(CASE WHEN source = 'sicap' THEN 1 END) as sicap_tenders,
                    COUNT(CASE WHEN source = 'anrmap' THEN 1 END) as anrmap_tenders,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as added_last_30_days,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as added_last_7_days,
                    COUNT(CASE WHEN updated_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as updated_last_24h,
                    SUM(estimated_value) as total_contract_value,
                    AVG(estimated_value) as avg_contract_value,
                    MAX(estimated_value) as max_contract_value,
                    COUNT(DISTINCT contracting_authority) as unique_authorities,
                    COUNT(DISTINCT winner_name) as unique_winners
                FROM tenders
            """)
            
            # Sync status and data freshness
            sync_status = await conn.fetch("""
                SELECT 
                    source,
                    last_sync,
                    records_processed,
                    status,
                    notes,
                    updated_at
                FROM sync_status 
                ORDER BY updated_at DESC
            """)
            
            # Top contracting authorities by volume
            top_authorities = await conn.fetch("""
                SELECT 
                    contracting_authority,
                    COUNT(*) as tender_count,
                    SUM(estimated_value) as total_value,
                    AVG(estimated_value) as avg_value,
                    AVG(risk_score) as avg_risk_score
                FROM tenders 
                WHERE contracting_authority IS NOT NULL
                GROUP BY contracting_authority
                ORDER BY COUNT(*) DESC
                LIMIT 20
            """)
            
            # Monthly trend data
            monthly_trends = await conn.fetch("""
                SELECT 
                    date_trunc('month', publication_date) as month,
                    COUNT(*) as tender_count,
                    SUM(estimated_value) as total_value,
                    AVG(estimated_value) as avg_value,
                    COUNT(DISTINCT contracting_authority) as unique_authorities
                FROM tenders 
                WHERE publication_date >= NOW() - INTERVAL '12 months'
                GROUP BY date_trunc('month', publication_date)
                ORDER BY month DESC
            """)
            
            return {
                'data_volume': dict(data_stats) if data_stats else {},
                'sync_status': [dict(row) for row in sync_status],
                'top_authorities': [dict(row) for row in top_authorities],
                'monthly_trends': [dict(row) for row in monthly_trends],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate platform statistics: {str(e)}")
            return {'error': str(e)}
    
    async def save_report_cache(self, conn, report_type: str, report_data: Dict):
        """Save generated report to cache table for quick API access"""
        try:
            # Create reports cache table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_reports (
                    id SERIAL PRIMARY KEY,
                    report_type VARCHAR(100) NOT NULL,
                    generated_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    report_data JSONB NOT NULL,
                    UNIQUE(report_type)
                )
            """)
            
            # Set expiration based on report type
            if report_type == 'risk_summary':
                expires_at = datetime.now() + timedelta(hours=6)  # Risk reports every 6 hours
            elif report_type == 'platform_stats':
                expires_at = datetime.now() + timedelta(hours=12)  # Stats every 12 hours
            else:
                expires_at = datetime.now() + timedelta(hours=24)  # Others daily
            
            # Insert or update report
            await conn.execute("""
                INSERT INTO cached_reports (report_type, report_data, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (report_type) DO UPDATE SET
                    report_data = $2,
                    generated_at = NOW(),
                    expires_at = $3
            """, report_type, json.dumps(report_data, default=str), expires_at)
            
            logger.info(f"Cached {report_type} report until {expires_at}")
            
        except Exception as e:
            logger.warning(f"Could not cache report {report_type}: {str(e)}")
    
    async def update_dashboard_metrics(self, conn, risk_report: Dict, stats_report: Dict):
        """Update dashboard metrics for quick API access"""
        try:
            # Create dashboard metrics table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100) UNIQUE NOT NULL,
                    metric_value NUMERIC,
                    metric_text VARCHAR(500),
                    last_updated TIMESTAMP DEFAULT NOW(),
                    category VARCHAR(50)
                )
            """)
            
            # Extract key metrics
            risk_stats = risk_report.get('overall_stats', {})
            data_stats = stats_report.get('data_volume', {})
            
            metrics_to_update = [
                ('total_tenders', data_stats.get('total_tenders', 0), None, 'data'),
                ('high_risk_tenders', risk_stats.get('high_risk', 0), None, 'risk'),
                ('avg_risk_score', risk_stats.get('avg_risk_score', 0), None, 'risk'),
                ('total_contract_value', data_stats.get('total_contract_value', 0), None, 'data'),
                ('unique_authorities', data_stats.get('unique_authorities', 0), None, 'data'),
                ('added_last_7_days', data_stats.get('added_last_7_days', 0), None, 'data'),
                ('platform_health', None, 'operational', 'system'),
                ('last_risk_analysis', None, datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'system')
            ]
            
            for metric_name, metric_value, metric_text, category in metrics_to_update:
                await conn.execute("""
                    INSERT INTO dashboard_metrics (metric_name, metric_value, metric_text, category)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (metric_name) DO UPDATE SET
                        metric_value = COALESCE($2, dashboard_metrics.metric_value),
                        metric_text = COALESCE($3, dashboard_metrics.metric_text),
                        last_updated = NOW(),
                        category = $4
                """, metric_name, metric_value, metric_text, category)
            
            logger.info("Updated dashboard metrics")
            
        except Exception as e:
            logger.warning(f"Could not update dashboard metrics: {str(e)}")
    
    async def generate_reports(self) -> Dict:
        """Main report generation execution"""
        logger.info("Starting report generation")
        
        try:
            import asyncpg
            conn = await asyncpg.connect(self.database_url)
            
            try:
                # Generate reports
                logger.info("Generating risk summary report...")
                risk_report = await self.generate_risk_summary_report(conn)
                
                logger.info("Generating platform statistics...")
                stats_report = await self.generate_platform_statistics(conn)
                
                # Check for errors
                if 'error' in risk_report:
                    logger.error(f"Risk report error: {risk_report['error']}")
                if 'error' in stats_report:
                    logger.error(f"Stats report error: {stats_report['error']}")
                
                # Cache reports for API access
                if 'error' not in risk_report:
                    await self.save_report_cache(conn, 'risk_summary', risk_report)
                
                if 'error' not in stats_report:
                    await self.save_report_cache(conn, 'platform_stats', stats_report)
                
                # Update dashboard metrics
                if 'error' not in risk_report and 'error' not in stats_report:
                    await self.update_dashboard_metrics(conn, risk_report, stats_report)
                
                # Clean old cached reports (keep only last 5 of each type)
                await conn.execute("""
                    DELETE FROM cached_reports 
                    WHERE generated_at < NOW() - INTERVAL '7 days'
                """)
                
                return {
                    'success': True,
                    'risk_report': risk_report,
                    'stats_report': stats_report,
                    'generated_at': datetime.now().isoformat()
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return {'success': False, 'error': str(e)}

async def main():
    """Main execution function"""
    generator = ReportGenerator()
    
    try:
        result = await generator.generate_reports()
        
        if result.get('success'):
            logger.info("✅ Report generation completed successfully")
            
            risk_report = result.get('risk_report', {})
            stats_report = result.get('stats_report', {})
            
            # Extract key metrics for output
            total_tenders = stats_report.get('data_volume', {}).get('total_tenders', 0)
            high_risk_count = risk_report.get('overall_stats', {}).get('high_risk', 0)
            avg_risk_score = risk_report.get('overall_stats', {}).get('avg_risk_score', 0)
            
            print(f"REPORT_GENERATION_RESULT=success")
            print(f"TOTAL_TENDERS_ANALYZED={total_tenders}")
            print(f"HIGH_RISK_TENDERS={high_risk_count}")
            print(f"AVERAGE_RISK_SCORE={avg_risk_score:.3f}" if avg_risk_score else "AVERAGE_RISK_SCORE=0")
            
            # Check for any errors in individual reports
            has_errors = 'error' in risk_report or 'error' in stats_report
            print(f"REPORT_ERRORS={'true' if has_errors else 'false'}")
            
        else:
            logger.error(f"❌ Report generation failed: {result.get('error')}")
            print(f"REPORT_GENERATION_RESULT=failed")
            print(f"ERROR={result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Critical error in report generation: {str(e)}")
        print(f"REPORT_GENERATION_RESULT=error")
        print(f"ERROR={str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())