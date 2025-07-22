#!/usr/bin/env python3
"""
Storage Monitor Script for GitHub Actions
Monitors Railway database usage and sends alerts when approaching limits
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

class StorageMonitor:
    """Monitor database storage usage for Railway free tier (1GB limit)"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.api_base_url = os.getenv('API_BASE_URL', 'https://api.procurement-platform.me')
        
        # Alert thresholds
        self.warning_threshold = 0.75  # 75% of 1GB
        self.critical_threshold = 0.90  # 90% of 1GB
        self.max_storage_bytes = 1024 * 1024 * 1024  # 1GB
    
    async def get_storage_metrics(self, conn) -> Dict:
        """Get comprehensive storage metrics"""
        try:
            # Database size
            db_size_query = """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size_pretty,
                    pg_database_size(current_database()) as size_bytes
            """
            db_size = await conn.fetchrow(db_size_query)
            
            # Table sizes with detailed metrics
            table_metrics_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size_pretty,
                    pg_relation_size(schemaname||'.'||tablename) as table_size_bytes,
                    n_tup_ins as total_inserts,
                    n_tup_upd as total_updates,
                    n_tup_del as total_deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_tables 
                LEFT JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """
            table_metrics = await conn.fetch(table_metrics_query)
            
            # Growth analysis - check size changes over time
            growth_analysis = await self.analyze_growth_patterns(conn)
            
            # Index usage and size
            index_metrics_query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size_pretty,
                    pg_relation_size(indexname::regclass) as index_size_bytes
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(indexname::regclass) DESC
                LIMIT 10
            """
            index_metrics = await conn.fetch(index_metrics_query)
            
            # Calculate utilization
            current_size_bytes = db_size['size_bytes']
            utilization_percent = (current_size_bytes / self.max_storage_bytes) * 100
            
            return {
                'database': {
                    'size_pretty': db_size['size_pretty'],
                    'size_bytes': current_size_bytes,
                    'size_mb': round(current_size_bytes / (1024 * 1024), 2),
                    'size_gb': round(current_size_bytes / (1024 * 1024 * 1024), 3),
                    'utilization_percent': round(utilization_percent, 2),
                    'limit_gb': 1.0,
                    'remaining_bytes': self.max_storage_bytes - current_size_bytes,
                    'remaining_mb': round((self.max_storage_bytes - current_size_bytes) / (1024 * 1024), 2)
                },
                'tables': [dict(row) for row in table_metrics],
                'indexes': [dict(row) for row in index_metrics],
                'growth_analysis': growth_analysis,
                'alerts': self.generate_storage_alerts(utilization_percent, growth_analysis),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {str(e)}")
            return {'error': str(e)}
    
    async def analyze_growth_patterns(self, conn) -> Dict:
        """Analyze database growth patterns"""
        try:
            # Get record counts from main tables over time (if we have historical data)
            current_counts = {}
            tables_to_check = ['tenders', 'users', 'audit_logs', 'api_requests']
            
            for table in tables_to_check:
                try:
                    # Current count
                    current_count = await conn.fetchval(f"SELECT count(*) FROM {table}")
                    current_counts[table] = current_count
                    
                    # Growth over last 7 days (if created_at column exists)
                    weekly_growth = await conn.fetchval(f"""
                        SELECT count(*) FROM {table} 
                        WHERE created_at > NOW() - INTERVAL '7 days'
                    """)
                    current_counts[f"{table}_weekly_growth"] = weekly_growth or 0
                    
                except Exception:
                    # Table might not exist or might not have created_at column
                    current_counts[table] = 0
                    current_counts[f"{table}_weekly_growth"] = 0
            
            # Calculate daily growth rates
            daily_growth_estimates = {}
            for table in tables_to_check:
                weekly_growth = current_counts.get(f"{table}_weekly_growth", 0)
                daily_growth_estimates[table] = round(weekly_growth / 7, 2)
            
            # Estimate time until storage limit based on growth
            total_daily_records = sum(daily_growth_estimates.values())
            
            # Rough estimate: assume average 1KB per record
            daily_growth_bytes = total_daily_records * 1024
            current_size = await conn.fetchval("SELECT pg_database_size(current_database())")
            remaining_bytes = self.max_storage_bytes - current_size
            
            if daily_growth_bytes > 0:
                days_until_full = remaining_bytes / daily_growth_bytes
            else:
                days_until_full = float('inf')
            
            return {
                'current_counts': current_counts,
                'daily_growth_estimates': daily_growth_estimates,
                'estimated_daily_growth_bytes': daily_growth_bytes,
                'estimated_days_until_full': round(days_until_full, 1) if days_until_full != float('inf') else None
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze growth patterns: {str(e)}")
            return {'error': str(e)}
    
    def generate_storage_alerts(self, utilization_percent: float, growth_analysis: Dict) -> List[Dict]:
        """Generate storage alerts based on usage and growth"""
        alerts = []
        
        # Utilization alerts
        if utilization_percent >= self.critical_threshold * 100:
            alerts.append({
                'level': 'critical',
                'type': 'storage_utilization',
                'message': f'Database at {utilization_percent:.1f}% capacity - IMMEDIATE ACTION REQUIRED',
                'recommendation': 'Upgrade to Railway Pro immediately or run emergency cleanup'
            })
        elif utilization_percent >= self.warning_threshold * 100:
            alerts.append({
                'level': 'warning',
                'type': 'storage_utilization',
                'message': f'Database at {utilization_percent:.1f}% capacity - upgrade recommended soon',
                'recommendation': 'Plan upgrade to Railway Pro within 1-2 weeks'
            })
        
        # Growth-based alerts
        days_until_full = growth_analysis.get('estimated_days_until_full')
        if days_until_full and days_until_full < 30:
            if days_until_full < 7:
                alerts.append({
                    'level': 'critical',
                    'type': 'growth_projection',
                    'message': f'Database projected to be full in {days_until_full:.1f} days',
                    'recommendation': 'Immediate upgrade or aggressive cleanup required'
                })
            elif days_until_full < 14:
                alerts.append({
                    'level': 'warning',
                    'type': 'growth_projection',
                    'message': f'Database projected to be full in {days_until_full:.1f} days',
                    'recommendation': 'Schedule upgrade within 1 week'
                })
        
        return alerts
    
    async def send_slack_report(self, metrics: Dict):
        """Send storage report to Slack"""
        if not self.slack_webhook:
            logger.info("No Slack webhook configured, skipping notification")
            return
        
        try:
            import requests
            
            db = metrics['database']
            alerts = metrics['alerts']
            
            # Determine alert color
            if any(alert['level'] == 'critical' for alert in alerts):
                color = 'danger'
                emoji = '🚨'
            elif any(alert['level'] == 'warning' for alert in alerts):
                color = 'warning'
                emoji = '⚠️'
            else:
                color = 'good'
                emoji = '✅'
            
            # Build top tables list
            top_tables = metrics['tables'][:5]
            table_list = '\n'.join([
                f"• {table['tablename']}: {table['size_pretty']} ({table.get('live_rows', 0):,} rows)"
                for table in top_tables
            ])
            
            # Build alert messages
            alert_messages = []
            for alert in alerts:
                level_emoji = '🔥' if alert['level'] == 'critical' else '⚠️'
                alert_messages.append(f"{level_emoji} {alert['message']}")
            
            alert_text = '\n'.join(alert_messages) if alert_messages else 'No alerts'
            
            # Growth info
            growth = metrics.get('growth_analysis', {})
            days_until_full = growth.get('estimated_days_until_full')
            growth_text = f"Projected full in: {days_until_full:.1f} days" if days_until_full else "Growth analysis unavailable"
            
            payload = {
                "text": f"{emoji} Database Storage Report - Romanian Procurement Platform",
                "attachments": [
                    {
                        "color": color,
                        "title": "Storage Utilization Report",
                        "fields": [
                            {"title": "Current Size", "value": f"{db['size_pretty']} ({db['utilization_percent']:.1f}%)", "short": True},
                            {"title": "Remaining Space", "value": f"{db['remaining_mb']:.1f} MB", "short": True},
                            {"title": "Growth Rate", "value": f"{growth.get('estimated_daily_growth_bytes', 0) / 1024:.1f} KB/day", "short": True},
                            {"title": "Time Until Full", "value": growth_text, "short": True}
                        ]
                    },
                    {
                        "color": color,
                        "title": "Largest Tables",
                        "text": table_list,
                        "short": False
                    },
                    {
                        "color": color if alerts else "good",
                        "title": "Alerts & Recommendations",
                        "text": alert_text,
                        "short": False
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Storage report sent to Slack successfully")
            else:
                logger.warning(f"Failed to send Slack notification: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    
    async def save_metrics_history(self, conn, metrics: Dict):
        """Save storage metrics for historical analysis"""
        try:
            # Create storage_metrics table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_metrics (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP DEFAULT NOW(),
                    database_size_bytes BIGINT,
                    utilization_percent DECIMAL(5,2),
                    table_count INTEGER,
                    largest_table VARCHAR(100),
                    largest_table_size_bytes BIGINT,
                    metrics_json JSONB
                )
            """)
            
            # Insert current metrics
            db = metrics['database']
            tables = metrics['tables']
            largest_table = tables[0] if tables else {}
            
            await conn.execute("""
                INSERT INTO storage_metrics (
                    database_size_bytes, utilization_percent, table_count,
                    largest_table, largest_table_size_bytes, metrics_json
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
                db['size_bytes'],
                db['utilization_percent'],
                len(tables),
                largest_table.get('tablename'),
                largest_table.get('size_bytes', 0),
                json.dumps(metrics, default=str)  # default=str handles datetime objects
            )
            
            # Keep only last 30 days of metrics to save space
            await conn.execute("""
                DELETE FROM storage_metrics 
                WHERE recorded_at < NOW() - INTERVAL '30 days'
            """)
            
            logger.info("Storage metrics saved to history")
            
        except Exception as e:
            logger.warning(f"Could not save metrics history: {str(e)}")
    
    async def run_monitoring(self) -> Dict:
        """Main monitoring execution"""
        logger.info("Starting storage monitoring")
        
        try:
            import asyncpg
            conn = await asyncpg.connect(self.database_url)
            
            try:
                # Get storage metrics
                metrics = await self.get_storage_metrics(conn)
                
                if 'error' in metrics:
                    return {'success': False, 'error': metrics['error']}
                
                # Save metrics history
                await self.save_metrics_history(conn, metrics)
                
                # Send Slack report
                await self.send_slack_report(metrics)
                
                # Log summary
                db = metrics['database']
                alerts = metrics['alerts']
                
                logger.info(f"Database size: {db['size_pretty']} ({db['utilization_percent']:.1f}% of 1GB)")
                logger.info(f"Remaining space: {db['remaining_mb']:.1f} MB")
                
                if alerts:
                    logger.warning(f"Generated {len(alerts)} alerts")
                    for alert in alerts:
                        logger.warning(f"- {alert['level'].upper()}: {alert['message']}")
                else:
                    logger.info("No storage alerts")
                
                return {
                    'success': True,
                    'metrics': metrics,
                    'alerts_count': len(alerts)
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Storage monitoring failed: {str(e)}")
            return {'success': False, 'error': str(e)}

async def main():
    """Main execution function"""
    monitor = StorageMonitor()
    
    try:
        result = await monitor.run_monitoring()
        
        if result.get('success'):
            logger.info("✅ Storage monitoring completed successfully")
            
            metrics = result.get('metrics', {})
            db = metrics.get('database', {})
            alerts_count = result.get('alerts_count', 0)
            
            print(f"STORAGE_MONITOR_RESULT=success")
            print(f"DATABASE_SIZE_GB={db.get('size_gb', 0)}")
            print(f"UTILIZATION_PERCENT={db.get('utilization_percent', 0)}")
            print(f"REMAINING_MB={db.get('remaining_mb', 0)}")
            print(f"ALERTS_COUNT={alerts_count}")
            
        else:
            logger.error(f"❌ Storage monitoring failed: {result.get('error')}")
            print(f"STORAGE_MONITOR_RESULT=failed")
            print(f"ERROR={result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Critical error in storage monitoring: {str(e)}")
        print(f"STORAGE_MONITOR_RESULT=error")
        print(f"ERROR={str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())