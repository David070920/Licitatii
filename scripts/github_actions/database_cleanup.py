#!/usr/bin/env python3
"""
Database Cleanup Script for GitHub Actions
Maintains database within 1GB Railway free tier limit
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseCleanup:
    """Database maintenance and cleanup for Railway free tier"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.api_token = os.getenv('API_TOKEN', '')
        
        # Cleanup policies (retention in days)
        self.retention_policies = {
            'audit_logs': 30,           # Audit logs: 30 days
            'api_requests': 7,          # API request logs: 7 days
            'temp_uploads': 1,          # Temporary uploads: 1 day
            'cached_reports': 14,       # Cached reports: 14 days
            'old_sync_logs': 21,        # Sync operation logs: 21 days
            'error_logs': 60,           # Error logs: 60 days (keep longer for analysis)
        }
        
        # Tables that might not exist yet but we'll try to clean
        self.optional_tables = [
            'temp_uploads', 'cached_reports', 'old_sync_logs'
        ]
    
    async def get_database_stats(self, conn) -> Dict:
        """Get current database size and table statistics"""
        try:
            # Database size
            db_size_query = """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size_pretty,
                    pg_database_size(current_database()) as size_bytes
            """
            db_size = await conn.fetchrow(db_size_query)
            
            # Table sizes
            table_sizes_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes
                FROM pg_tables 
                LEFT JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """
            table_stats = await conn.fetch(table_sizes_query)
            
            # Record counts for main tables
            main_tables = ['tenders', 'users', 'audit_logs', 'api_requests']
            record_counts = {}
            
            for table in main_tables:
                try:
                    count = await conn.fetchval(f"SELECT count(*) FROM {table}")
                    record_counts[table] = count
                except:
                    record_counts[table] = 0  # Table might not exist
            
            return {
                'database_size': {
                    'pretty': db_size['size_pretty'],
                    'bytes': db_size['size_bytes']
                },
                'table_stats': [dict(row) for row in table_stats],
                'record_counts': record_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {'error': str(e)}
    
    async def cleanup_by_retention_policy(self, conn) -> Dict:
        """Clean up old records based on retention policies"""
        cleanup_results = {}
        
        for table, retention_days in self.retention_policies.items():
            try:
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                # Check if table exists
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table)
                
                if not table_exists:
                    if table not in self.optional_tables:
                        logger.warning(f"Table {table} does not exist")
                    cleanup_results[table] = {'skipped': True, 'reason': 'table_not_found'}
                    continue
                
                # Determine date column
                date_columns = ['created_at', 'timestamp', 'date_created', 'logged_at']
                date_column = None
                
                for col in date_columns:
                    col_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_name = $1 AND column_name = $2
                        )
                    """, table, col)
                    
                    if col_exists:
                        date_column = col
                        break
                
                if not date_column:
                    logger.warning(f"No date column found for table {table}")
                    cleanup_results[table] = {'skipped': True, 'reason': 'no_date_column'}
                    continue
                
                # Delete old records
                delete_query = f"DELETE FROM {table} WHERE {date_column} < $1"
                result = await conn.execute(delete_query, cutoff_date)
                
                # Extract number of deleted rows from result
                deleted_count = int(result.split()[-1]) if result.startswith('DELETE') else 0
                
                cleanup_results[table] = {
                    'deleted_count': deleted_count,
                    'cutoff_date': cutoff_date.isoformat(),
                    'retention_days': retention_days
                }
                
                if deleted_count > 0:
                    logger.info(f"Cleaned {deleted_count} old records from {table}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup table {table}: {str(e)}")
                cleanup_results[table] = {'error': str(e)}
        
        return cleanup_results
    
    async def optimize_database(self, conn) -> Dict:
        """Run database optimization commands"""
        optimization_results = {}
        
        try:
            # Vacuum and analyze main tables
            main_tables = ['tenders', 'users', 'audit_logs']
            
            for table in main_tables:
                try:
                    # Check if table exists
                    table_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = $1
                        )
                    """, table)
                    
                    if table_exists:
                        # VACUUM and ANALYZE
                        await conn.execute(f"VACUUM ANALYZE {table}")
                        optimization_results[table] = {'optimized': True}
                        logger.info(f"Optimized table {table}")
                    else:
                        optimization_results[table] = {'skipped': True, 'reason': 'table_not_found'}
                        
                except Exception as e:
                    logger.error(f"Failed to optimize table {table}: {str(e)}")
                    optimization_results[table] = {'error': str(e)}
            
            # Update table statistics
            await conn.execute("ANALYZE")
            logger.info("Updated database statistics")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Database optimization failed: {str(e)}")
            return {'error': str(e)}
    
    async def archive_old_data(self, conn) -> Dict:
        """Archive very old data to reduce database size"""
        archive_results = {}
        
        try:
            # Archive tenders older than 2 years to JSON format
            archive_cutoff = datetime.now() - timedelta(days=730)  # 2 years
            
            # Check if tenders table exists
            tenders_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'tenders'
                )
            """)
            
            if tenders_exists:
                # Count old tenders
                old_tenders_count = await conn.fetchval("""
                    SELECT count(*) FROM tenders 
                    WHERE created_at < $1
                """, archive_cutoff)
                
                if old_tenders_count > 0:
                    # Create archived_data table if it doesn't exist
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS archived_data (
                            id SERIAL PRIMARY KEY,
                            data_type VARCHAR(50),
                            archived_at TIMESTAMP DEFAULT NOW(),
                            record_count INTEGER,
                            data_json JSONB
                        )
                    """)
                    
                    # Archive in batches to avoid memory issues
                    batch_size = 100
                    archived_count = 0
                    
                    while old_tenders_count > 0:
                        # Get batch of old tenders
                        old_tenders = await conn.fetch("""
                            SELECT * FROM tenders 
                            WHERE created_at < $1 
                            ORDER BY created_at
                            LIMIT $2
                        """, archive_cutoff, batch_size)
                        
                        if not old_tenders:
                            break
                        
                        # Convert to JSON and archive
                        tenders_data = [dict(tender) for tender in old_tenders]
                        
                        # Convert datetime objects to strings for JSON serialization
                        for tender in tenders_data:
                            for key, value in tender.items():
                                if isinstance(value, datetime):
                                    tender[key] = value.isoformat()
                        
                        await conn.execute("""
                            INSERT INTO archived_data (data_type, record_count, data_json)
                            VALUES ('old_tenders', $1, $2)
                        """, len(tenders_data), tenders_data)
                        
                        # Delete the archived tenders
                        tender_ids = [tender['id'] for tender in old_tenders]
                        await conn.execute("""
                            DELETE FROM tenders WHERE id = ANY($1)
                        """, tender_ids)
                        
                        archived_count += len(tender_ids)
                        old_tenders_count -= len(tender_ids)
                        
                        logger.info(f"Archived {archived_count} old tenders...")
                    
                    archive_results['tenders'] = {
                        'archived_count': archived_count,
                        'cutoff_date': archive_cutoff.isoformat()
                    }
                else:
                    archive_results['tenders'] = {'archived_count': 0, 'reason': 'no_old_data'}
            else:
                archive_results['tenders'] = {'skipped': True, 'reason': 'table_not_found'}
            
            return archive_results
            
        except Exception as e:
            logger.error(f"Data archiving failed: {str(e)}")
            return {'error': str(e)}
    
    async def run_cleanup(self) -> Dict:
        """Main cleanup execution"""
        logger.info("Starting database cleanup and maintenance")
        
        try:
            import asyncpg
            conn = await asyncpg.connect(self.database_url)
            
            try:
                # Get initial database stats
                initial_stats = await self.get_database_stats(conn)
                logger.info(f"Initial database size: {initial_stats.get('database_size', {}).get('pretty', 'Unknown')}")
                
                # Perform cleanup operations
                cleanup_results = await self.cleanup_by_retention_policy(conn)
                optimization_results = await self.optimize_database(conn)
                archive_results = await self.archive_old_data(conn)
                
                # Get final database stats
                final_stats = await self.get_database_stats(conn)
                logger.info(f"Final database size: {final_stats.get('database_size', {}).get('pretty', 'Unknown')}")
                
                # Calculate space saved
                initial_bytes = initial_stats.get('database_size', {}).get('bytes', 0)
                final_bytes = final_stats.get('database_size', {}).get('bytes', 0)
                space_saved = initial_bytes - final_bytes
                
                return {
                    'success': True,
                    'initial_size': initial_stats.get('database_size', {}),
                    'final_size': final_stats.get('database_size', {}),
                    'space_saved_bytes': space_saved,
                    'cleanup_results': cleanup_results,
                    'optimization_results': optimization_results,
                    'archive_results': archive_results,
                    'timestamp': datetime.now().isoformat()
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Database cleanup failed: {str(e)}")
            return {'success': False, 'error': str(e)}

async def main():
    """Main execution function"""
    cleanup = DatabaseCleanup()
    
    try:
        result = await cleanup.run_cleanup()
        
        if result.get('success'):
            logger.info("✅ Database cleanup completed successfully")
            
            # Print summary
            initial_size = result.get('initial_size', {}).get('pretty', 'Unknown')
            final_size = result.get('final_size', {}).get('pretty', 'Unknown')
            space_saved = result.get('space_saved_bytes', 0)
            
            print(f"DATABASE_CLEANUP_RESULT=success")
            print(f"INITIAL_SIZE={initial_size}")
            print(f"FINAL_SIZE={final_size}")
            print(f"SPACE_SAVED_BYTES={space_saved}")
            
            # Count total cleaned records
            cleanup_results = result.get('cleanup_results', {})
            total_deleted = sum(
                r.get('deleted_count', 0) 
                for r in cleanup_results.values() 
                if isinstance(r, dict)
            )
            print(f"TOTAL_RECORDS_DELETED={total_deleted}")
            
        else:
            logger.error(f"❌ Database cleanup failed: {result.get('error')}")
            print(f"DATABASE_CLEANUP_RESULT=failed")
            print(f"ERROR={result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Critical error in database cleanup: {str(e)}")
        print(f"DATABASE_CLEANUP_RESULT=error")
        print(f"ERROR={str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())