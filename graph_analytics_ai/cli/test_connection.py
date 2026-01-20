#!/usr/bin/env python3
"""
Test Database Connection

Generic utility to test ArangoDB connection and display database information.
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
    
    # Check if .env exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        print(f"\n❌ ERROR: .env file not found at {env_file}")
        print("   Create .env file with database credentials")
        return False
    
    print(f"\n✅ .env file found")
    
    # Load environment and check configuration
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        database = os.getenv("ARANGO_DATABASE")
        endpoint = os.getenv("ARANGO_ENDPOINT")
        user = os.getenv("ARANGO_USER")
        
        print(f"\n📋 Environment Configuration:")
        print(f"   Database: {database}")
        print(f"   Endpoint: {endpoint}")
        print(f"   User: {user}")
        
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
        print(f"\n✅ Successfully connected to ArangoDB!")
        print(f"   Database Name: {db.name}")
        
        # Get collections info
        collections = db.collections()
        system_cols = [c for c in collections if c['name'].startswith('_')]
        user_cols = [c for c in collections if not c['name'].startswith('_')]
        
        print(f"   Total Collections: {len(collections)}")
        print(f"     - User Collections: {len(user_cols)}")
        print(f"     - System Collections: {len(system_cols)}")
        
        # List some user collections
        if user_cols:
            print(f"\n   Sample User Collections:")
            for col in user_cols[:10]:
                print(f"      - {col['name']}")
            if len(user_cols) > 10:
                print(f"      ... and {len(user_cols) - 10} more")
        
        print(f"\n✅ ✅ SUCCESS! Connected to database: {db.name}")
        return True
            
    except ImportError as e:
        print(f"\n❌ ERROR: Cannot import graph_analytics_ai library")
        print(f"   {e}")
        print("\n   Install the library:")
        print("   pip install graph-analytics-ai")
        print("   # Or for local development:")
        print("   pip install -e /path/to/graph-analytics-ai-platform")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: Connection failed")
        print(f"   {e}")
        print("\n   Check:")
        print("   1. .env file has correct credentials")
        print("   2. Database endpoint is reachable")
        print("   3. Username/password are correct")
        print("   4. Database name exists")
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
