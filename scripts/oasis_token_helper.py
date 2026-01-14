#!/usr/bin/env python3
"""
OASIS Token Helper

Manages ArangoDB Managed Platform (AMP) authentication tokens with caching
to avoid frequent oasisctl calls that may fail due to certificate issues.

Usage:
    # As a script
    python scripts/oasis_token_helper.py

    # As a module
    from scripts.oasis_token_helper import get_or_refresh_token
    token = get_or_refresh_token()

Environment Variables:
    OASIS_TOKEN: Existing token (bypasses generation)
    OASIS_KEY_ID: API key ID for token generation
    OASIS_KEY_SECRET: API key secret for token generation
    OASIS_TOKEN_CACHE_DIR: Custom cache directory (default: ~/.cache)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Configuration
TOKEN_LIFETIME_HOURS = 24  # AMP tokens expire after 24 hours
REFRESH_THRESHOLD_HOURS = 2  # Refresh 2 hours before expiry
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "oasis"
TOKEN_CACHE_FILE = "token.json"


class TokenHelper:
    """Helper class for managing OASIS tokens."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize token helper.

        Args:
            cache_dir: Directory for token cache (default: ~/.cache/oasis)
        """
        self.cache_dir = cache_dir or Path(os.getenv("OASIS_TOKEN_CACHE_DIR", str(DEFAULT_CACHE_DIR)))
        self.cache_file = self.cache_dir / TOKEN_CACHE_FILE
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cached_token(self) -> Optional[str]:
        """
        Get token from cache if valid.

        Returns:
            Cached token if valid, None otherwise
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            # Validate required fields
            if "token" not in data or "created_at" not in data:
                print("Warning: Invalid cache format, ignoring")
                return None

            # Check if token is still valid
            created = datetime.fromisoformat(data["created_at"])
            age = datetime.now() - created
            max_age = timedelta(hours=TOKEN_LIFETIME_HOURS - REFRESH_THRESHOLD_HOURS)

            if age < max_age:
                hours_remaining = (max_age - age).total_seconds() / 3600
                print(f"Using cached token (expires in {hours_remaining:.1f} hours)")
                return data["token"]
            else:
                print("Cached token expired, generating new token...")
                return None

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Warning: Failed to read cache: {e}")
            return None

    def cache_token(self, token: str) -> None:
        """
        Cache token for future use.

        Args:
            token: Token to cache
        """
        try:
            data = {
                "token": token,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=TOKEN_LIFETIME_HOURS)).isoformat()
            }

            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"Token cached at {self.cache_file}")

        except Exception as e:
            print(f"Warning: Failed to cache token: {e}")

    def generate_token_with_oasisctl(self) -> Optional[str]:
        """
        Generate token using oasisctl CLI.

        Returns:
            Generated token or None if failed
        """
        # Get credentials from environment
        key_id = os.getenv("OASIS_KEY_ID")
        key_secret = os.getenv("OASIS_KEY_SECRET")

        if not key_id or not key_secret:
            print("Error: OASIS_KEY_ID and OASIS_KEY_SECRET environment variables required")
            print("\nSet them with:")
            print("  export OASIS_KEY_ID=your_key_id")
            print("  export OASIS_KEY_SECRET=your_key_secret")
            return None

        print("Generating token with oasisctl...")

        try:
            # Call oasisctl
            result = subprocess.run(
                [
                    "oasisctl",
                    "login",
                    "--key-id", key_id,
                    "--key-secret", key_secret,
                ],
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            )

            token = result.stdout.strip()
            if not token:
                print("Error: oasisctl returned empty token")
                return None

            print("Successfully generated token with oasisctl")
            return token

        except subprocess.CalledProcessError as e:
            print(f"\nError: oasisctl failed: {e.stderr}")
            
            # Check for certificate error
            if "certificate" in e.stderr.lower() or "x509" in e.stderr.lower():
                print("\nCertificate Verification Error Detected!")
                print("This is a known issue on macOS with oasisctl.")
                print("\nQuick fixes:")
                print("  1. Update oasisctl: brew upgrade arangodb/tap/oasisctl")
                print("  2. Use manual token input (see below)")
                print("  3. Set SSL_CERT_FILE environment variable")
                print("\nFor more details, see: docs/ENVIRONMENT_VARIABLES.md")
            
            return None

        except FileNotFoundError:
            print("\nError: oasisctl not found")
            print("\nInstall it with:")
            print("  macOS: brew install arangodb/tap/oasisctl")
            print("  Other: https://github.com/arangodb-managed/oasisctl/releases")
            return None

    def get_token_manual(self) -> Optional[str]:
        """
        Get token via manual input.

        Returns:
            Manually entered token or None
        """
        print("\n" + "="*60)
        print("Manual Token Input")
        print("="*60)
        print("\nTo get a token manually:")
        print("  1. Go to https://cloud.arangodb.com/")
        print("  2. Navigate to: Settings > API Keys")
        print("  3. Generate a token with your API key")
        print("  4. Paste it below")
        print("\nOr run on a different machine:")
        print("  oasisctl login --key-id=<id> --key-secret=<secret>")
        print("\n" + "="*60)

        try:
            token = input("\nPaste your OASIS_TOKEN (or press Ctrl+C to cancel): ").strip()
            if token:
                return token
            else:
                print("No token provided")
                return None
        except KeyboardInterrupt:
            print("\nCancelled")
            return None

    def get_or_refresh_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get valid token, using cache or generating new one.

        Args:
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Valid token or None if all methods failed
        """
        # Check environment variable first
        env_token = os.getenv("OASIS_TOKEN")
        if env_token and not force_refresh:
            print("Using token from OASIS_TOKEN environment variable")
            return env_token

        # Check cache
        if not force_refresh:
            cached_token = self.get_cached_token()
            if cached_token:
                return cached_token

        # Try to generate with oasisctl
        token = self.generate_token_with_oasisctl()

        # If that fails, offer manual input
        if not token:
            print("\nFailed to generate token automatically.")
            use_manual = input("Would you like to enter token manually? [y/N]: ").lower()
            if use_manual == 'y':
                token = self.get_token_manual()

        # Cache the token if we got one
        if token:
            self.cache_token(token)
            return token

        print("\nError: Failed to obtain token")
        return None

    def clear_cache(self) -> None:
        """Clear cached token."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            print(f"Cleared token cache at {self.cache_file}")
        else:
            print("No cached token to clear")

    def show_status(self) -> None:
        """Show current token status."""
        print("\nOASIS Token Status")
        print("="*60)

        # Check environment variable
        env_token = os.getenv("OASIS_TOKEN")
        if env_token:
            print(f"Environment: Set (length: {len(env_token)})")
        else:
            print("Environment: Not set")

        # Check cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
                created = datetime.fromisoformat(data["created_at"])
                age = datetime.now() - created
                hours_old = age.total_seconds() / 3600
                hours_remaining = TOKEN_LIFETIME_HOURS - hours_old

                print(f"Cached Token: Found")
                print(f"  Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Age: {hours_old:.1f} hours")
                print(f"  Expires in: {hours_remaining:.1f} hours")
                print(f"  Status: {'Valid' if hours_remaining > 0 else 'Expired'}")
            except Exception as e:
                print(f"Cached Token: Invalid ({e})")
        else:
            print("Cached Token: Not found")

        print("="*60)


def get_or_refresh_token(force_refresh: bool = False) -> Optional[str]:
    """
    Convenience function to get or refresh token.

    Args:
        force_refresh: Force token refresh even if cached

    Returns:
        Valid token or None
    """
    helper = TokenHelper()
    return helper.get_or_refresh_token(force_refresh=force_refresh)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="OASIS Token Helper - Manage ArangoDB AMP tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get or refresh token
  python scripts/oasis_token_helper.py

  # Force refresh
  python scripts/oasis_token_helper.py --refresh

  # Show status
  python scripts/oasis_token_helper.py --status

  # Clear cache
  python scripts/oasis_token_helper.py --clear

  # Export to environment
  export OASIS_TOKEN=$(python scripts/oasis_token_helper.py --quiet)
        """
    )

    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Force token refresh"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show token status"
    )
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="Clear cached token"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (only output token)"
    )

    args = parser.parse_args()

    helper = TokenHelper()

    # Handle commands
    if args.status:
        helper.show_status()
        return 0

    if args.clear:
        helper.clear_cache()
        return 0

    # Get or refresh token
    token = helper.get_or_refresh_token(force_refresh=args.refresh)

    if token:
        if args.quiet:
            print(token)
        else:
            print("\nSuccess! Token obtained.")
            print("\nTo use in your scripts:")
            print(f"  export OASIS_TOKEN={token[:20]}...")
            print("\nOr run:")
            print("  export OASIS_TOKEN=$(python scripts/oasis_token_helper.py --quiet)")
        return 0
    else:
        if not args.quiet:
            print("\nFailed to obtain token")
        return 1


if __name__ == "__main__":
    sys.exit(main())
