#!/usr/bin/env python3
"""
Test Database Connection

Run this script in each project to verify the correct database is configured.
"""

import os
import sys
from pathlib import Path

LIBRARY_TEST_DATABASE = "graph-analytics-ai"


def test_connection():
    """Test database connection and display connection info."""

    print("=" * 70)
    print("DATABASE CONNECTION TEST")
    print("=" * 70)

    current_dir = Path.cwd()
    print(f"\n📁 Current Directory: {current_dir}")

    # Load .env first; the configured database tells us where we're going.
    env_file = current_dir / ".env"
    if not env_file.exists():
        print(f"\n❌ ERROR: .env file not found at {env_file}")
        print("   Create .env file with database credentials")
        return False
    print("\n✅ .env file found")

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("\n❌ ERROR: python-dotenv not installed")
        print("   Run: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"\n❌ ERROR loading .env: {e}")
        return False

    configured_db = os.getenv("ARANGO_DATABASE")
    endpoint = os.getenv("ARANGO_ENDPOINT")
    user = os.getenv("ARANGO_USER")

    in_library_checkout = "agentic-graph-analytics" in str(current_dir)
    project_type = "LIBRARY PROJECT" if in_library_checkout else "CUSTOMER PROJECT"

    print(f"🏷️  Project Type: {project_type}")
    print(f"🎯 Configured Database: {configured_db}")

    print("\n📋 Environment Configuration:")
    print(f"   Database: {configured_db}")
    print(f"   Endpoint: {endpoint}")
    print(f"   User: {user}")

    # Informational hint only — running the library checkout against a non-test
    # database is legitimate (e.g. demoing a customer dataset). We no longer
    # treat this as a failure.
    if in_library_checkout and configured_db != LIBRARY_TEST_DATABASE:
        print(
            f"\nℹ️  Note: this is the library checkout, but .env points at "
            f"'{configured_db}' instead of the default test DB "
            f"'{LIBRARY_TEST_DATABASE}'. That's fine for demoing a customer "
            f"dataset; switch back to '{LIBRARY_TEST_DATABASE}' for library "
            f"unit tests."
        )

    print("\n" + "=" * 70)
    print("ATTEMPTING CONNECTION...")
    print("=" * 70)

    try:
        from graph_analytics_ai.db_connection import get_db_connection

        db = get_db_connection()
        print("\n✅ Successfully connected to ArangoDB!")
        print(f"   Database Name: {db.name}")
        print(f"   Collections: {len(db.collections())}")

        collections = db.collections()
        if collections:
            print("\n   Sample Collections:")
            for col in collections[:5]:
                print(f"      - {col['name']}")

        if db.name != configured_db:
            print(
                f"\n⚠️  WARNING: Connected to '{db.name}' but .env requested "
                f"'{configured_db}'. Check your configuration."
            )
            return False

        print(f"\n✅ Connection verified against configured database: {db.name}")
        return True

    except ImportError as e:
        print("\n❌ ERROR: Cannot import graph_analytics_ai library")
        print(f"   {e}")
        print("\n   Install the library:")
        print("   pip install -e ../agentic-graph-analytics")
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

