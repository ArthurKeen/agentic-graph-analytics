#!/usr/bin/env python3
"""
Test Database Connection

Run this script in each project to verify the correct database is configured.
"""

import os
import sys
from pathlib import Path

def test_connection():
    """Test database connection and display connection info."""
    
    print("=" * 70)
    print("DATABASE CONNECTION TEST")
    print("=" * 70)
    
    # Show current directory
    current_dir = Path.cwd()
    print(f"\n📁 Current Directory: {current_dir}")
    
    # Determine which project we're in
    if "graph-analytics-ai-platform" in str(current_dir):
        project_type = "LIBRARY PROJECT"
        expected_db = "graph-analytics-ai"
    else:
        project_type = "CUSTOMER PROJECT"
        # For customer projects, read expected database from .env
        from dotenv import load_dotenv
        load_dotenv()
        expected_db = os.getenv("ARANGO_DATABASE", "unknown")
    
    print(f"🏷️  Project Type: {project_type}")
    print(f"🎯 Expected Database: {expected_db}")
    
    # Check if .env exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        print(f"\n❌ ERROR: .env file not found at {env_file}")
        print("   Create .env file with database credentials")
        return False
    
    print("\n✅ .env file found")
    
    # Load environment and check configuration
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        database = os.getenv("ARANGO_DATABASE")
        endpoint = os.getenv("ARANGO_ENDPOINT")
        user = os.getenv("ARANGO_USER")
        
        print("\n📋 Environment Configuration:")
        print(f"   Database: {database}")
        print(f"   Endpoint: {endpoint}")
        print(f"   User: {user}")
        
        # Verify correct database
        if database != expected_db:
            print(f"\n⚠️  WARNING: Connected to '{database}' but expected '{expected_db}'")
            if project_type == "LIBRARY PROJECT":
                print("   This project should use TEST credentials!")
            else:
                print("   This project should use CUSTOMER PRODUCTION credentials!")
        else:
            print("\n✅ Correct database configured!")
        
    except ImportError:
        print("\n❌ ERROR: python-dotenv not installed")
        print("   Run: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"\n❌ ERROR loading .env: {e}")
        return False
    
    # Try to connect
    print("\n" + "=" * 70)
    print("ATTEMPTING CONNECTION...")
    print("=" * 70)
    
    try:
        from graph_analytics_ai.db_connection import get_db_connection
        
        db = get_db_connection()
        print("\n✅ Successfully connected to ArangoDB!")
        print(f"   Database Name: {db.name}")
        print(f"   Collections: {len(db.collections())}")
        
        # List some collections
        collections = db.collections()
        if collections:
            print("\n   Sample Collections:")
            for col in collections[:5]:
                print(f"      - {col['name']}")
        
        # Verify correct database
        if db.name == expected_db:
            print(f"\n✅ ✅ SUCCESS! Connected to correct database: {db.name}")
            return True
        else:
            print(f"\n⚠️  WARNING: Connected to '{db.name}' but expected '{expected_db}'")
            print("   Check your .env file configuration!")
            return False
            
    except ImportError as e:
        print("\n❌ ERROR: Cannot import graph_analytics_ai library")
        print(f"   {e}")
        print("\n   Install the library:")
        print("   pip install -e ../graph-analytics-ai-platform")
        return False
    except Exception as e:
        print("\n❌ ERROR: Connection failed")
        print(f"   {e}")
        print("\n   Check:")
        print("   1. .env file has correct credentials")
        print("   2. Database endpoint is reachable")
        print("   3. Username/password are correct")
        return False

def main():
    """Run connection test."""
    success = test_connection()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ CONNECTION TEST PASSED")
    else:
        print("❌ CONNECTION TEST FAILED")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

