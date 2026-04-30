"""
ArangoDB Connection Helper

Provides a unified interface to connect to ArangoDB clusters.
"""

from arango import ArangoClient

from .config import get_arango_config, parse_ssl_verify


def connect_arango_database(
    endpoint,
    username,
    password,
    database,
    verify_ssl=True,
    verify_system=True,
    client_factory=None,
):
    """
    Connect to an explicit ArangoDB database descriptor.

    This helper is intended for UI connection profiles, where the profile is
    stored as non-secret metadata and the password is resolved at runtime from
    a secret reference. It does not read global environment configuration.

    Args:
        endpoint: ArangoDB endpoint URL.
        username: Database username.
        password: Resolved password or token.
        database: Target database name.
        verify_ssl: SSL verification setting, either bool or string.
        verify_system: If True, verify credentials against _system first.
        client_factory: Test seam for injecting an ArangoClient-compatible type.

    Returns:
        StandardDatabase: ArangoDB database connection.
    """
    verify = parse_ssl_verify(verify_ssl) if isinstance(verify_ssl, str) else verify_ssl
    if client_factory is None:
        client_factory = ArangoClient
    client = client_factory(hosts=endpoint)

    if verify_system:
        sys_db = client.db("_system", username=username, password=password, verify=verify)
        try:
            sys_db.version()
            print(f"✓ Successfully connected to ArangoDB at {endpoint}")
        except Exception as e:
            error_msg = str(e).replace(str(password), "***MASKED***")
            error_str = str(e).lower()
            if "401" in error_str or "not authorized" in error_str or "err 11" in error_str:
                enhanced_msg = (
                    f"Failed to connect to ArangoDB: {error_msg}\n\n"
                    f"Authorization Error Detected\n\n"
                    f"This error means the server rejected your credentials or permissions.\n\n"
                    f"Common causes:\n"
                    f"  1. User doesn't have access to _system database (limited users)\n"
                    f"  2. Wrong username or password\n"
                    f"  3. Password has extra spaces (check .env file)\n"
                    f"  4. Endpoint missing port :8529\n\n"
                    f"Troubleshooting:\n"
                    f"  1. Verify credentials in .env file (no spaces, no quotes)\n"
                    f"  2. Check endpoint includes port: ARANGO_ENDPOINT=https://hostname:8529\n"
                    f"  3. Verify credentials work in web UI\n"
                    f"  4. For limited users, connect directly to target database (skip _system)\n"
                )
                raise ConnectionError(enhanced_msg)
            raise ConnectionError(f"Failed to connect to ArangoDB: {error_msg}")

        try:
            available_dbs = sys_db.databases()
            if available_dbs and isinstance(available_dbs[0], dict):
                db_names = [db["name"] for db in available_dbs]
            else:
                db_names = available_dbs
            if database not in db_names:
                raise ValueError(
                    f"Database '{database}' does not exist on this cluster. "
                    f"Available: {db_names}"
                )
        except ValueError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "not authorized" in error_str or "err 11" in error_str:
                print("Warning: Cannot list databases (user may have limited permissions)")
                print(f"   Attempting direct connection to '{database}' database...")
            else:
                print(f"Warning: Could not verify database existence: {e}")

    db = client.db(database, username=username, password=password, verify=verify)
    print(f"✓ Connected to database: {database}")
    return db


def get_db_connection():
    """
    Establish connection to ArangoDB cluster.

    Returns:
        StandardDatabase: ArangoDB database connection

    Raises:
        ValueError: If required credentials are missing
        ConnectionError: If connection fails
    """
    # Get configuration from environment
    config = get_arango_config()

    endpoint = config["endpoint"]
    username = config["user"]
    password = config["password"]
    database = config["database"]
    verify_ssl = parse_ssl_verify(config["verify_ssl"])

    return connect_arango_database(
        endpoint=endpoint,
        username=username,
        password=password,
        database=database,
        verify_ssl=verify_ssl,
    )


def get_connection_info():
    """
    Get connection information without establishing a connection.

    Returns:
        dict: Connection configuration details
    """
    config = get_arango_config()

    return {
        "endpoint": config["endpoint"],
        "database": config["database"],
        "user": config["user"],
        "verify_ssl": config["verify_ssl"],
    }
