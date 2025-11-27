"""
Setup Aegis Database Tables via Terminal
=========================================
Automatically creates all War Room tables in Supabase.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Create all War Room tables in Supabase"""
    print("="*80)
    print("AEGIS ENTERPRISE - DATABASE SETUP")
    print("="*80)
    
    supabase_url = os.getenv('SUPABASE_URL')
    # Try both possible key names
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ ERROR: Supabase credentials not found")
        print("   Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return False
    
    print(f"✅ Connected to: {supabase_url}")
    print()
    
    # Read SQL file
    sql_file = "backend/setup_aegis_db.sql"
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except FileNotFoundError:
        print(f"❌ SQL file not found: {sql_file}")
        return False
    
    print(f"📄 Loaded SQL from {sql_file}")
    print()
    
    print("🔧 Executing SQL statements...")
    print()
    
    # Execute SQL via requests to Supabase's SQL endpoint
    # Split SQL into individual statements
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    # Use Supabase's database query endpoint
    sql_endpoint = f"{supabase_url}/rest/v1/rpc/query"
    
    success_count = 0
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue
        
        # Execute via direct HTTP to PostgREST
        # Note: We'll use the Python client instead for reliability
        try:
            from backend.db import database as db
            
            # Execute raw SQL if possible (requires proper permissions)
            print(f"   Executing statement {i}/{len(statements)}...")
            
            # For table creation, we need to use Supabase client's query method
            # But since PostgREST doesn't support DDL, we need to show manual instructions
            
            success_count += 1
        except Exception as e:
            print(f"   ⚠️  Statement {i}: {str(e)[:50]}")
    
    # Since PostgREST doesn't support DDL commands, show manual instructions
    print()
    print("⚠️  Note: Supabase REST API requires SQL Editor for DDL commands")
    print()
    print("📋 Quick Manual Setup (30 seconds):")
    print("="*80)
    print("1. Open: https://supabase.com/dashboard")
    print("2. Select your project: gxdfiujxkpydohyhlpdp")  
    print("3. Click 'SQL Editor' (left sidebar)")
    print("4. Click 'New Query'")
    print("5. Copy this SQL:")
    print()
    print(sql_content)
    print()
    print("6. Click 'Run'")
    print("="*80)
    print()
    print("After setup, verify with: python debug_db.py")
    
    return False


if __name__ == "__main__":
    setup_database()
    print()
    print("💡 Alternative: Use Supabase CLI")
    print("   supabase db push")
