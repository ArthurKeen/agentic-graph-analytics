#!/usr/bin/env python3
"""
Check for and clean up leftover GAE engines
"""

from graph_analytics_ai.gae_connection import GAEManager


def main():
    # Initialize GAE manager
    gae = GAEManager()

    print("🔍 Checking for running GAE engines...\n")

    # List all engines
    engines = gae.list_engines()

    if not engines:
        print("✅ No engines found - all clean!")
        return

    print(f"Found {len(engines)} engine(s):\n")
    for engine in engines:
        engine_id = engine.get("id", "unknown")
        size = engine.get("size", "unknown")
        status = engine.get("status", "unknown")

        print(f"  Engine ID: {engine_id}")
        print(f"  Size: {size}")
        print(f"  Status: {status}")
        print()

    # Ask user if they want to delete
    response = input("\n🗑️  Delete all engines? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        print("\nDeleting engines...")
        for engine in engines:
            engine_id = engine.get("id")
            print(f"  Deleting {engine_id}...")
            try:
                gae.delete_engine(engine_id)
                print(f"  ✓ Deleted {engine_id}")
            except Exception as e:
                print(f"  ✗ Failed to delete {engine_id}: {e}")
        print("\n✅ Cleanup complete!")
    else:
        print("\n⏭️  Skipping deletion")


if __name__ == "__main__":
    main()
