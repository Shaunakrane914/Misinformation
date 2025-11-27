"""
Debug Script: Database Connectivity Check
==========================================
Verifies Supabase connection and War Room table access.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database_connection():
    """Check if we can connect to Supabase and access War Room tables."""
    print("="*80)
    print("AEGIS ENTERPRISE - DATABASE CONNECTIVITY CHECK")
    print("="*80)
    
    try:
        from backend.db import database as db
        
        # Check if Supabase is configured
        if not db.supabase:
            print("❌ ERROR: Supabase client not initialized")
            print("   Check your SUPABASE_URL and SUPABASE_KEY in .env")
            return False
        
        print("✅ Supabase client initialized")
        print(f"   URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
        print()
        
        # Test each War Room table
        tables = ["active_signals", "verified_threats", "deployed_measures"]
        
        for table_name in tables:
            try:
                response = db.supabase.table(table_name).select("*").limit(1).execute()
                count_response = db.supabase.table(table_name).select("*", count="exact").execute()
                total_rows = count_response.count if hasattr(count_response, 'count') else len(count_response.data or [])
                
                print(f"✅ Table '{table_name}' accessible")
                print(f"   Total rows: {total_rows}")
                
            except Exception as e:
                print(f"❌ Table '{table_name}' error: {str(e)}")
                print(f"   You may need to run setup_aegis_db.sql")
                return False
        
        print()
        print("="*80)
        print("✅ ALL CHECKS PASSED - Database is ready")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
        print("="*80)
        return False


if __name__ == "__main__":
    success = check_database_connection()
    exit(0 if success else 1)
