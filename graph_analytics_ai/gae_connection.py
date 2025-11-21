"""
Graph Analytics Engine (GAE) Connection

Unified interface for both Arango Managed Platform (AMP) and self-managed deployments.
"""

import os
import requests
import time
import subprocess
import warnings
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from .config import get_gae_config, get_arango_config, DeploymentMode
from .constants import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_JOB_TIMEOUT,
    DEFAULT_MAX_SUPERSTEPS,
    DEFAULT_DAMPING_FACTOR,
    DEFAULT_START_LABEL_ATTRIBUTE,
    DEFAULT_PARALLELISM,
    DEFAULT_BATCH_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_ENGINE_API_TIMEOUT,
    DEFAULT_RETRY_DELAY,
    COMPLETED_STATES,
    FAILED_STATES,
    ICON_SUCCESS,
    ICON_ERROR,
    ICON_WARNING,
    API_VERSION_PREFIX,
    TOKEN_LIFETIME_HOURS,
    TOKEN_REFRESH_THRESHOLD_HOURS
)


class GAEConnectionBase(ABC):
    """Base class for GAE connections."""
    
    @abstractmethod
    def deploy_engine(self, size_id: str = 'e4', type_id: str = 'gral') -> Dict[str, Any]:
        """Deploy a new GAE engine."""
        pass
    
    @abstractmethod
    def delete_engine(self, engine_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete an engine."""
        pass
    
    @abstractmethod
    def load_graph(self, database: str, 
                   vertex_collections: Optional[List[str]] = None,
                   edge_collections: Optional[List[str]] = None,
                   graph_name: Optional[str] = None,
                   vertex_attributes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load graph data into the engine.
        
        Args:
            database: Database name
            vertex_collections: List of vertex collection names (required if graph_name not provided)
            edge_collections: List of edge collection names (required if graph_name not provided)
            graph_name: Named graph to load (alternative to specifying collections)
            vertex_attributes: Optional list of vertex attributes to load
            
        Returns:
            Dictionary with job_id, graph_id, and id fields
        """
        pass
    
    @abstractmethod
    def run_pagerank(self, graph_id: str, damping_factor: float = DEFAULT_DAMPING_FACTOR,
                     maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run PageRank algorithm."""
        pass
    
    @abstractmethod
    def run_wcc(self, graph_id: str) -> Dict[str, Any]:
        """Run Weakly Connected Components."""
        pass
    
    @abstractmethod
    def run_scc(self, graph_id: str) -> Dict[str, Any]:
        """Run Strongly Connected Components."""
        pass
    
    @abstractmethod
    def run_label_propagation(self, graph_id: str, start_label_attribute: str = DEFAULT_START_LABEL_ATTRIBUTE,
                             synchronous: bool = False, random_tiebreak: bool = False,
                             maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run Label Propagation."""
        pass
    
    @abstractmethod
    def store_results(self, target_collection: str,
                     job_ids: List[str], attribute_names: List[str],
                     database: Optional[str] = None,
                     parallelism: int = DEFAULT_PARALLELISM, batch_size: int = DEFAULT_BATCH_SIZE) -> Dict[str, Any]:
        """Store job results back to ArangoDB."""
        pass
    
    @abstractmethod
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        pass
    
    @abstractmethod
    def get_graph(self, graph_id: str) -> Dict[str, Any]:
        """Get graph details."""
        pass


class GAEManager(GAEConnectionBase):
    """
    Manager for Graph Analytics Engine operations on Arango Managed Platform (AMP).
    
    Uses API keys and oasisctl for token management.
    """
    
    # Token lifetime in hours (ArangoGraph tokens expire after 24 hours)
    # Imported from constants module
    TOKEN_LIFETIME_HOURS = TOKEN_LIFETIME_HOURS
    # Refresh token proactively when it's this close to expiry
    TOKEN_REFRESH_THRESHOLD_HOURS = TOKEN_REFRESH_THRESHOLD_HOURS
    
    def __init__(self, auto_refresh: bool = True):
        """
        Initialize GAE Manager with credentials from environment.
        
        Args:
            auto_refresh: Enable automatic token refresh (default: True)
        """
        # Get configuration from environment
        config = get_gae_config()
        
        if config['deployment_mode'] != DeploymentMode.AMP.value:
            raise ValueError(
                f"GAEManager requires AMP deployment mode, "
                f"but got: {config['deployment_mode']}"
            )
        
        self.api_key_id = config['api_key_id']
        self.api_key_secret = config['api_key_secret']
        self.deployment_url = config['deployment_url']
        self.gae_port = config['gae_port']
        
        # Management API base URL
        self.base_url = f"{self.deployment_url}:{self.gae_port}/graph-analytics/api/graphanalytics/v1"
        
        # Token management
        self.auto_refresh = auto_refresh
        self.access_token = None
        self.token_created_at = None
        
        # Get or generate access token
        self._initialize_token(config)
        
        # Current engine info
        self.current_engine_id = None
        self.current_engine_url = None
    
    def _initialize_token(self, config: Dict[str, str]) -> None:
        """Initialize access token from environment or generate a new one."""
        # Try to use existing token from environment
        token = config.get('access_token', '')
        if token:
            print("Using existing access token from environment")
            self.access_token = token
            self.token_created_at = datetime.now()
        else:
            # Generate new token
            print("No token found in environment, generating new token...")
            self._refresh_token()
    
    def _refresh_token(self) -> None:
        """Generate a new access token using oasisctl."""
        print("Refreshing access token...")
        
        # Validate API key format (basic validation to prevent command injection)
        if not self.api_key_id or not isinstance(self.api_key_id, str):
            raise ValueError("Invalid API key ID format")
        if not self.api_key_secret or not isinstance(self.api_key_secret, str):
            raise ValueError("Invalid API key secret format")
        
        # Sanitize: ensure no shell metacharacters
        if any(char in self.api_key_id for char in [';', '&', '|', '`', '$', '(', ')', '<', '>']):
            raise ValueError("API key ID contains invalid characters")
        if any(char in self.api_key_secret for char in [';', '&', '|', '`', '$', '(', ')', '<', '>']):
            raise ValueError("API key secret contains invalid characters")
        
        try:
            # Call oasisctl to generate token (using list format prevents shell injection)
            result = subprocess.run(
                [
                    'oasisctl', 'login',
                    '--key-id', self.api_key_id,
                    '--key-secret', self.api_key_secret
                ],
                capture_output=True,
                text=True,
                check=True,
                shell=False  # Explicitly disable shell
            )
            
            # Extract token from stdout
            token = result.stdout.strip()
            
            if not token:
                raise RuntimeError("oasisctl returned empty token")
            
            self.access_token = token
            self.token_created_at = datetime.now()
            print(f"✓ Token refreshed successfully at {self.token_created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to generate token: {e.stderr}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e
        except FileNotFoundError:
            raise RuntimeError(
                "oasisctl not found. Please install it:\n"
                "  macOS: brew install arangodb/tap/oasisctl\n"
                "  Other: https://github.com/arangodb-managed/oasisctl/releases"
            )
    
    def _is_token_expired(self) -> bool:
        """Check if the token is expired or close to expiry."""
        if not self.token_created_at:
            return True
        
        age = datetime.now() - self.token_created_at
        threshold = timedelta(hours=self.TOKEN_LIFETIME_HOURS - self.TOKEN_REFRESH_THRESHOLD_HOURS)
        
        return age >= threshold
    
    def _ensure_token_valid(self) -> None:
        """Ensure the access token is valid, refreshing if necessary."""
        if not self.auto_refresh:
            return
        
        if self._is_token_expired():
            age_hours = (datetime.now() - self.token_created_at).total_seconds() / 3600 if self.token_created_at else 0
            print(f"Token is {age_hours:.1f} hours old, refreshing...")
            self._refresh_token()
    
    def _api_request_with_retry(self, method: str, url: str, 
                                headers: Dict[str, str],
                                json_data: Optional[Dict] = None,
                                max_retries: int = 1) -> requests.Response:
        """Make an API request with automatic retry on 401 errors."""
        for attempt in range(max_retries + 1):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=json_data)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response
                
            except requests.HTTPError as e:
                # Check if it's a 401 error and we can retry
                if e.response.status_code == 401 and attempt < max_retries and self.auto_refresh:
                    print("Token expired (401 error), refreshing and retrying...")
                    self._refresh_token()
                    # Update headers with new token
                    headers['Authorization'] = f'bearer {self.access_token}'
                    continue
                else:
                    raise
        
        raise RuntimeError("Request failed after all retry attempts")
    
    def _management_headers(self) -> Dict[str, str]:
        """Get headers for Management API requests."""
        return {
            'Authorization': f'bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def _engine_headers(self) -> Dict[str, str]:
        """Get headers for Engine API requests."""
        return {
            'Authorization': f'bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_api_version(self) -> Dict[str, Any]:
        """Get the Management API version."""
        self._ensure_token_valid()
        url = f"{self.base_url}/api-version"
        response = self._api_request_with_retry('GET', url, self._management_headers())
        return response.json()
    
    def list_engine_sizes(self) -> List[Dict[str, Any]]:
        """List available engine sizes."""
        self._ensure_token_valid()
        url = f"{self.base_url}/enginesizes"
        response = self._api_request_with_retry('GET', url, self._management_headers())
        return response.json().get('items', [])
    
    def list_engines(self) -> List[Dict[str, Any]]:
        """List all deployed engines."""
        self._ensure_token_valid()
        url = f"{self.base_url}/engines"
        response = self._api_request_with_retry('GET', url, self._management_headers())
        return response.json().get('items', [])
    
    def deploy_engine(self, size_id: str = 'e4', type_id: str = 'gral') -> Dict[str, Any]:
        """Deploy a new Graph Analytics Engine."""
        self._ensure_token_valid()
        url = f"{self.base_url}/engines"
        payload = {
            'type_id': type_id,
            'size_id': size_id
        }
        
        print(f"Deploying {type_id} engine with size {size_id}...")
        response = self._api_request_with_retry('POST', url, self._management_headers(), json_data=payload)
        
        engine_info = response.json()
        self.current_engine_id = engine_info.get('id')
        
        # Wait for engine to be ready
        print("Waiting for engine to start...")
        engine_details = self._wait_for_engine_ready(self.current_engine_id)
        
        self.current_engine_url = engine_details['status']['endpoint']
        print(f"✓ Engine deployed successfully: {self.current_engine_id}")
        print(f"  Engine URL: {self.current_engine_url}")
        
        # Additional wait for API endpoints to be ready
        self._wait_for_engine_api_ready()
        
        return engine_details
    
    def delete_engine(self, engine_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete an engine."""
        if engine_id is None:
            engine_id = self.current_engine_id
        
        if engine_id is None:
            raise ValueError("No engine ID specified and no current engine set")
        
        self._ensure_token_valid()
        url = f"{self.base_url}/engines/{engine_id}"
        print(f"Deleting engine {engine_id}...")
        response = self._api_request_with_retry('DELETE', url, self._management_headers())
        
        if engine_id == self.current_engine_id:
            self.current_engine_id = None
            self.current_engine_url = None
        
        print("✓ Engine deleted successfully")
        return response.json() if response.text else {}
    
    def _wait_for_engine_ready(self, engine_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for engine to be in ready state."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            engine = self.get_engine(engine_id)
            status = engine.get('status', {})
            
            if status.get('is_started') and status.get('succeeded'):
                return engine
            
            time.sleep(2)
        
        raise TimeoutError(f"Engine {engine_id} did not start within {timeout} seconds")
    
    def get_engine(self, engine_id: str) -> Dict[str, Any]:
        """Get details about a specific engine."""
        self._ensure_token_valid()
        url = f"{self.base_url}/engines/{engine_id}"
        response = self._api_request_with_retry('GET', url, self._management_headers())
        return response.json()
    
    def _wait_for_engine_api_ready(self, timeout: int = DEFAULT_ENGINE_API_TIMEOUT, retry_delay: int = DEFAULT_RETRY_DELAY) -> None:
        """Wait for engine API endpoints to be ready."""
        print("Waiting for engine API to be ready...")
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < timeout:
            try:
                self.get_engine_version()
                print("✓ Engine API is ready")
                return
            except Exception as e:
                last_error = e
                time.sleep(retry_delay)
        
        raise TimeoutError(
            f"Engine API did not become ready within {timeout} seconds. "
            f"Last error: {last_error}"
        )
    
    def _engine_api_call(self, endpoint: str, method: str = 'GET', 
                        data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a call to the Engine API."""
        if not self.current_engine_url:
            raise ValueError(
                "No engine URL set. Deploy an engine first or set current_engine_url"
            )
        
        self._ensure_token_valid()
        url = f"{self.current_engine_url}/{endpoint}"
        response = self._api_request_with_retry(method, url, self._engine_headers(), json_data=data)
        return response.json() if response.text else {}
    
    def get_engine_version(self) -> Dict[str, Any]:
        """Get the Engine API version."""
        return self._engine_api_call('v1/version')
    
    def load_graph(self, database: str,
                   vertex_collections: Optional[List[str]] = None,
                   edge_collections: Optional[List[str]] = None,
                   graph_name: Optional[str] = None,
                   vertex_attributes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load graph data from ArangoDB into the GAE.
        
        Note: AMP may not support named graphs. If graph_name is provided and not supported,
        an error will be raised.
        
        Args:
            database: Database name
            vertex_collections: List of vertex collection names (required if graph_name not provided)
            edge_collections: List of edge collection names (required if graph_name not provided)
            graph_name: Named graph to load (may not be supported by AMP)
            vertex_attributes: Optional list of vertex attributes to load
        """
        if not graph_name and not (vertex_collections and edge_collections):
            raise ValueError(
                "Must specify either graph_name or both vertex_collections and edge_collections"
            )
        
        payload = {
            'database': database
        }
        
        if graph_name:
            payload['graph_name'] = graph_name
            print(f"Loading named graph '{graph_name}' from database '{database}'...")
        else:
            payload['vertex_collections'] = vertex_collections
            payload['edge_collections'] = edge_collections
            print(f"Loading graph from database '{database}': "
                  f"{len(vertex_collections)} vertex collections, "
                  f"{len(edge_collections)} edge collections")
        
        if vertex_attributes:
            payload['vertex_attributes'] = vertex_attributes
        
        result = self._engine_api_call('v1/loaddata', method='POST', data=payload)
        print(f"✓ Graph loaded: {result.get('graph_id')}")
        return result
    
    def run_pagerank(self, graph_id: str, damping_factor: float = DEFAULT_DAMPING_FACTOR,
                     maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run PageRank algorithm on a graph."""
        payload = {
            'graph_id': graph_id,
            'damping_factor': damping_factor,
            'maximum_supersteps': maximum_supersteps
        }
        
        print(f"Running PageRank on graph {graph_id}...")
        result = self._engine_api_call('v1/pagerank', method='POST', data=payload)
        print(f"✓ PageRank job started: {result.get('job_id')}")
        return result
    
    def run_wcc(self, graph_id: str) -> Dict[str, Any]:
        """Run Weakly Connected Components on a graph."""
        payload = {'graph_id': graph_id}
        
        print(f"Running WCC on graph {graph_id}...")
        result = self._engine_api_call('v1/wcc', method='POST', data=payload)
        print(f"✓ WCC job started: {result.get('job_id')}")
        return result
    
    def run_scc(self, graph_id: str) -> Dict[str, Any]:
        """Run Strongly Connected Components on a graph."""
        payload = {'graph_id': graph_id}
        
        print(f"Running SCC on graph {graph_id}...")
        result = self._engine_api_call('v1/scc', method='POST', data=payload)
        print(f"✓ SCC job started: {result.get('job_id')}")
        return result
    
    def run_label_propagation(self, graph_id: str, start_label_attribute: str = DEFAULT_START_LABEL_ATTRIBUTE,
                             synchronous: bool = False, random_tiebreak: bool = False,
                             maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run Label Propagation (community detection) on a graph."""
        payload = {
            'graph_id': graph_id,
            'start_label_attribute': start_label_attribute,
            'synchronous': synchronous,
            'random_tiebreak': random_tiebreak,
            'maximum_supersteps': maximum_supersteps
        }
        
        print(f"Running Label Propagation on graph {graph_id}...")
        result = self._engine_api_call('v1/labelpropagation', method='POST', data=payload)
        print(f"✓ Label Propagation job started: {result.get('job_id')}")
        return result
    
    def store_results(self, target_collection: str,
                     job_ids: List[str], attribute_names: List[str],
                     database: Optional[str] = None,
                     parallelism: int = DEFAULT_PARALLELISM, batch_size: int = DEFAULT_BATCH_SIZE) -> Dict[str, Any]:
        """
        Store job results back to ArangoDB.
        
        Args:
            target_collection: Collection to store results in
            job_ids: List of job IDs to store
            attribute_names: List of attribute names for each job
            database: Database name (required for AMP)
            parallelism: Degree of parallelism
            batch_size: Batch size for writing
        """
        if not database:
            raise ValueError("database parameter is required for AMP deployments")
        
        payload = {
            'database': database,
            'target_collection': target_collection,
            'job_ids': job_ids,
            'attribute_names': attribute_names,
            'parallelism': parallelism,
            'batch_size': batch_size
        }
        
        print(f"Storing {len(job_ids)} job results to {database}.{target_collection}...")
        result = self._engine_api_call('v1/storeresults', method='POST', data=payload)
        print("✓ Results stored successfully")
        return result
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get details about a specific job."""
        return self._engine_api_call(f'v1/jobs/{job_id}')
    
    def get_graph(self, graph_id: str) -> Dict[str, Any]:
        """Get details about a specific graph."""
        return self._engine_api_call(f'v1/graphs/{graph_id}')


class GenAIGAEConnection(GAEConnectionBase):
    """
    Manager for ArangoDB Graph Analytics Engine via GenAI Platform (self-managed).
    
    Uses JWT tokens from ArangoDB for authentication.
    """
    
    def __init__(
        self,
        db_endpoint: Optional[str] = None,
        db_name: Optional[str] = None,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = False
    ):
        """
        Initialize GenAI GAE Connection.
        
        Args:
            db_endpoint: ArangoDB endpoint (e.g., https://host:8529)
            db_name: Database name
            db_user: Database username
            db_password: Database password
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates (False for self-signed)
        """
        # Get config from environment or parameters
        arango_config = get_arango_config()
        
        self.db_endpoint = (db_endpoint or arango_config['endpoint']).rstrip('/')
        self.db_name = db_name or arango_config['database']
        self.db_user = db_user or arango_config['user']
        self.db_password = db_password or arango_config['password']
        
        self.timeout = timeout
        if verify_ssl is False:
            verify_ssl_str = os.getenv('ARANGO_VERIFY_SSL', 'false').lower()
            verify_ssl = verify_ssl_str in ('true', '1', 'yes')
        self.verify_ssl = verify_ssl
        
        # Security warning if SSL verification is disabled
        if not self.verify_ssl:
            warnings.warn(
                "SSL verification is disabled. This may allow man-in-the-middle attacks. "
                "Only disable SSL verification in trusted environments.",
                UserWarning
            )
        
        # Will be populated after authentication
        self.jwt_token: Optional[str] = None
        self.engine_id: Optional[str] = None
        
        # Validate required credentials
        if not self.db_endpoint or not self.db_password:
            raise ValueError(
                "Database credentials are required. Set ARANGO_ENDPOINT and ARANGO_PASSWORD"
            )
        
        # Validate endpoint format - warn if missing port (common issue from Dima's experience)
        if self.db_endpoint and self.db_endpoint.startswith('http'):
            # Extract hostname part (after protocol)
            host_part = self.db_endpoint.split('://', 1)[-1].split('/', 1)[0]
            # Check if port is missing (no colon in hostname part)
            if ':' not in host_part:
                import warnings
                warnings.warn(
                    f"ARANGO_ENDPOINT appears to be missing the port number.\n"
                    f"  Current: {self.db_endpoint}\n"
                    f"  Expected: {self.db_endpoint}:8529\n"
                    f"  If you get 401 errors, add :8529 to your endpoint URL.",
                    UserWarning
                )
    
    def _get_jwt_token(self) -> str:
        """Get JWT session token from ArangoDB."""
        print("Getting JWT token from ArangoDB...")
        
        auth_url = f"{self.db_endpoint}/_open/auth"
        payload = {
            "username": self.db_user,
            "password": self.db_password
        }
        
        try:
            response = requests.post(
                auth_url,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            data = response.json()
            token = data.get('jwt')
            
            if not token:
                raise ValueError("No JWT token in response")
            
            self.jwt_token = token
            print("JWT token obtained")
            return token
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"Authentication failed (401 Unauthorized)")
                print(f"   URL: {auth_url}")
                print(f"   This usually means:")
                print(f"   1. Wrong username or password")
                print(f"   2. Endpoint URL is incorrect (missing port :8529?)")
                print(f"   3. Network/VPN access issue")
                print(f"   4. Password may have extra spaces (check .env file)")
                
                # Check for missing port
                if ':8529' not in self.db_endpoint:
                    print(f"\n   WARNING: Your endpoint '{self.db_endpoint}' is missing port :8529")
                    print(f"   It should be: {self.db_endpoint}:8529")
                    print(f"   This is the #1 cause of 401 errors!")
                
                # Check for password formatting issues
                if self.db_password:
                    if self.db_password.startswith(' ') or self.db_password.endswith(' '):
                        print(f"\n   WARNING: Password appears to have leading/trailing spaces")
                        print(f"   Remove spaces from ARANGO_PASSWORD in .env file")
                
                print(f"\n   Troubleshooting steps:")
                print(f"   1. Verify endpoint includes :8529 port")
                print(f"   2. Check credentials match exactly (no extra spaces)")
                print(f"   3. Verify credentials work in ArangoDB web UI")
                print(f"   4. Check network/VPN connectivity")
            raise
        except Exception as e:
            print(f"Failed to get JWT token: {e}")
            # Check for missing port in any error
            if ':8529' not in self.db_endpoint:
                print(f"\n   TIP: Check if your endpoint includes port :8529")
                print(f"   Current: {self.db_endpoint}")
                print(f"   Should be: {self.db_endpoint}:8529")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with JWT authentication."""
        if not self.jwt_token:
            self._get_jwt_token()
        
        return {
            'Authorization': f'bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }
    
    def start_engine(self) -> str:
        """Start a new GAE service via GenAI platform."""
        print("Starting GAE service...")
        
        url = f"{self.db_endpoint}/gen-ai/v1/graphanalytics"
        headers = self._get_headers()
        
        try:
            response = requests.post(
                url,
                json={},
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            data = response.json()
            service_info = data.get('serviceInfo', {})
            service_id = service_info.get('serviceId')
            
            if not service_id or service_id == "null":
                raise RuntimeError("Failed to start engine")
            
            self.engine_id = service_id
            print(f"Engine started successfully")
            print(f"   Service ID: {service_id}")
            
            return service_id
            
        except Exception as e:
            print(f"Failed to start engine: {e}")
            raise
    
    def deploy_engine(self, size_id: str = 'e4', type_id: str = 'gral') -> Dict[str, Any]:
        """Deploy engine (alias for start_engine for compatibility)."""
        service_id = self.start_engine()
        return {
            'id': service_id,
            'status': {
                'is_started': True,
                'succeeded': True
            }
        }
    
    def stop_engine(self, service_id: Optional[str] = None) -> bool:
        """Stop a GAE service."""
        service_id = service_id or self.engine_id
        if not service_id:
            print("No service ID provided")
            return False
        
        print(f"Stopping GAE service {service_id}...")
        
        url = f"{self.db_endpoint}/gen-ai/v1/service/{service_id}"
        headers = self._get_headers()
        
        try:
            response = requests.delete(
                url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            print(f"Engine stopped successfully")
            if service_id == self.engine_id:
                self.engine_id = None
            return True
            
        except Exception as e:
            print(f"Failed to stop engine: {e}")
            return False
    
    def delete_engine(self, engine_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete engine (alias for stop_engine)."""
        service_id = engine_id or self.engine_id
        if self.stop_engine(service_id):
            return {"status": "deleted"}
        raise RuntimeError(f"Failed to delete engine {service_id}")
    
    def _get_engine_url(self) -> str:
        """Get the engine API base URL."""
        if not self.engine_id:
            raise ValueError("No engine running. Call start_engine() first.")
        
        # Extract short ID from full service ID (e.g., "arangodb-gral-hkhti" -> "hkhti")
        short_id = self.engine_id.split('-')[-1]
        
        # GenAI Platform: /gral/<short_id> path
        return f"{self.db_endpoint}/gral/{short_id}"
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the GAE engine API.
        
        Args:
            method: HTTP method ('GET', 'POST', 'DELETE')
            endpoint: API endpoint (e.g., 'v1/pagerank', 'v1/graphs')
            payload: Optional JSON payload for POST requests
            success_message: Optional success message to print (can use {job_id} placeholder)
            error_message: Optional error message prefix
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.HTTPError: If request fails
        """
        if not self.engine_id:
            self.start_engine()
        
        engine_url = self._get_engine_url()
        url = f"{engine_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            if method == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            elif method == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            elif method == 'DELETE':
                response = requests.delete(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            result = response.json() if response.text else {}
            
            # Format success message with job_id if present
            if success_message:
                job_id = result.get('job_id', result.get('id', 'N/A'))
                formatted_msg = success_message.format(job_id=job_id) if '{job_id}' in success_message else success_message
                print(f"{ICON_SUCCESS} {formatted_msg}")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            error_msg = error_message or f"Request failed"
            print(f"{ICON_ERROR} {error_msg}: {e}")
            if e.response is not None and e.response.text:
                print(f"   Response: {e.response.text[:200]}")
            raise
        except Exception as e:
            error_msg = error_message or f"Request failed"
            print(f"{ICON_ERROR} {error_msg}: {e}")
            raise
    
    def _normalize_job_response(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize job response to have consistent 'id' field.
        
        Args:
            job: Job response dictionary
            
        Returns:
            Normalized job dictionary with 'id' field
        """
        # GenAI Platform returns 'job_id', normalize to 'id' for consistency
        if 'job_id' in job and 'id' not in job:
            job['id'] = job['job_id']
        return job
    
    def load_graph(self, database: Optional[str] = None,
                   vertex_collections: Optional[List[str]] = None,
                   edge_collections: Optional[List[str]] = None,
                   graph_name: Optional[str] = None,
                   vertex_attributes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load graph data into the engine.
        
        Supports both named graphs and collection-based loading.
        
        Args:
            database: Database name (uses self.db_name if not provided)
            vertex_collections: List of vertex collection names (required if graph_name not provided)
            edge_collections: List of edge collection names (required if graph_name not provided)
            graph_name: Named graph to load (alternative to specifying collections)
            vertex_attributes: Optional list of vertex attributes to load
            
        Returns:
            Dictionary with job_id, graph_id, and id fields
        """
        if not graph_name and not (vertex_collections and edge_collections):
            raise ValueError(
                "Must specify either graph_name or both vertex_collections and edge_collections"
            )
        
        if not self.engine_id:
            self.start_engine()
        
        engine_url = self._get_engine_url()
        url = f"{engine_url}/v1/loaddata"
        headers = self._get_headers()
        
        # Use provided database or self.db_name
        db = database or self.db_name
        payload = {"database": db}
        
        if graph_name:
            payload["graph_name"] = graph_name
            print(f"Loading named graph: {graph_name} from database '{db}'")
        else:
            payload["vertex_collections"] = vertex_collections
            payload["edge_collections"] = edge_collections
            print(f"Loading graph from database '{db}': "
                  f"{len(vertex_collections)} vertex collections, "
                  f"{len(edge_collections)} edge collections")
        
        if vertex_attributes:
            payload["vertex_attributes"] = vertex_attributes
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}loaddata",
            payload=payload,
            success_message="Load data job submitted",
            error_message="Failed to load graph"
        )
        
        # Extract and display job_id and graph_id
        job_id = job.get('job_id')
        graph_id = job.get('graph_id')
        if job_id and graph_id:
            print(f"   job_id={job_id}, graph_id={graph_id}")
        
        return self._normalize_job_response(job)
    
    def run_pagerank(self, graph_id: str, damping_factor: float = DEFAULT_DAMPING_FACTOR,
                     maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run PageRank algorithm."""
        print(f"Running PageRank on graph {graph_id}...")
        
        payload = {
            "graph_id": graph_id,
            "damping_factor": damping_factor,
            "maximum_supersteps": maximum_supersteps
        }
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}pagerank",
            payload=payload,
            success_message="PageRank job submitted: {job_id}",
            error_message="Failed to run PageRank"
        )
        
        return self._normalize_job_response(job)
    
    def run_wcc(self, graph_id: str) -> Dict[str, Any]:
        """Run Weakly Connected Components algorithm."""
        print(f"Running WCC on graph {graph_id}...")
        
        payload = {"graph_id": graph_id}
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}wcc",
            payload=payload,
            success_message="WCC job submitted: {job_id}",
            error_message="Failed to run WCC"
        )
        
        return self._normalize_job_response(job)
    
    def run_scc(self, graph_id: str) -> Dict[str, Any]:
        """Run Strongly Connected Components algorithm."""
        print(f"Running SCC on graph {graph_id}...")
        
        payload = {"graph_id": graph_id}
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}scc",
            payload=payload,
            success_message="SCC job submitted: {job_id}",
            error_message="Failed to run SCC"
        )
        
        return self._normalize_job_response(job)
    
    def run_label_propagation(self, graph_id: str, 
                             start_label_attribute: str = DEFAULT_START_LABEL_ATTRIBUTE,
                             synchronous: bool = False, random_tiebreak: bool = False,
                             maximum_supersteps: int = DEFAULT_MAX_SUPERSTEPS) -> Dict[str, Any]:
        """Run Label Propagation (community detection)."""
        print(f"Running Label Propagation on graph {graph_id}...")
        
        payload = {
            "graph_id": graph_id,
            "start_label_attribute": start_label_attribute,
            "synchronous": synchronous,
            "random_tiebreak": random_tiebreak,
            "maximum_supersteps": maximum_supersteps
        }
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}labelpropagation",
            payload=payload,
            success_message="Label Propagation job submitted: {job_id}",
            error_message="Failed to run Label Propagation"
        )
        
        return self._normalize_job_response(job)
    
    def store_results(self, target_collection: str,
                     job_ids: List[str], attribute_names: List[str],
                     database: Optional[str] = None,
                     parallelism: int = DEFAULT_PARALLELISM, 
                     batch_size: int = DEFAULT_BATCH_SIZE) -> Dict[str, Any]:
        """
        Store job results to database.
        
        Args:
            target_collection: Collection to store results in
            job_ids: List of job IDs to store
            attribute_names: List of attribute names for each job
            database: Database name (uses self.db_name if not provided)
            parallelism: Degree of parallelism
            batch_size: Batch size for writing
        """
        if not self.engine_id:
            self.start_engine()
        
        # Use provided database or self.db_name
        db = database or self.db_name
        
        engine_url = self._get_engine_url()
        url = f"{engine_url}/v1/storeresults"
        headers = self._get_headers()
        
        payload = {
            "database": db,
            "target_collection": target_collection,
            "job_ids": job_ids,
            "attribute_names": attribute_names,
            "parallelism": parallelism,
            "batch_size": batch_size
        }
        
        print(f"Storing results to {db}.{target_collection}...")
        
        job = self._make_request(
            method='POST',
            endpoint=f"{API_VERSION_PREFIX}storeresults",
            payload=payload,
            success_message="Store results job submitted: {job_id}",
            error_message="Failed to store results"
        )
        
        return self._normalize_job_response(job)
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get status of a job."""
        try:
            job = self._make_request(
                method='GET',
                endpoint=f"{API_VERSION_PREFIX}jobs/{job_id}",
                error_message=f"Failed to get job {job_id} status"
            )
            return job
        except Exception:
            # Return empty dict on error (backward compatibility)
            return {}
    
    def list_services(self) -> List[Dict[str, Any]]:
        """
        List all running GenAI services.
        
        Returns:
            List of service information dictionaries
        """
        url = f"{self.db_endpoint}/gen-ai/v1/list_services"
        headers = self._get_headers()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()
            # Response has structure: {"services": [...]}
            return data.get('services', [])
        except Exception as e:
            print(f"Error listing services: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test connection to GenAI GAE.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get JWT token
            self._get_jwt_token()
            
            # Try to list services (lightweight operation)
            services = self.list_services()
            print("Connection test successful")
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def list_graphs(self) -> List[Dict[str, Any]]:
        """
        List all graphs loaded in the GAE.
        
        Returns:
            List of graph information dictionaries
        """
        if not self.engine_id:
            raise ValueError("No engine running. Call start_engine() first.")
        
        try:
            graphs = self._make_request(
                method='GET',
                endpoint=f"{API_VERSION_PREFIX}graphs",
                error_message="Failed to list graphs"
            )
            return graphs if isinstance(graphs, list) else []
        except Exception as e:
            print(f"Failed to list graphs: {e}")
            raise
    
    def delete_graph(self, graph_id: str) -> Dict[str, Any]:
        """
        Delete a loaded graph from GAE engine memory.
        
        Args:
            graph_id: Graph ID to delete
            
        Returns:
            Deletion response dictionary
        """
        if not self.engine_id:
            raise ValueError("No engine running. Call start_engine() first.")
        
        result = self._make_request(
            method='DELETE',
            endpoint=f"{API_VERSION_PREFIX}graphs/{graph_id}",
            success_message=f"Graph {graph_id} deleted successfully",
            error_message=f"Failed to delete graph {graph_id}"
        )
        
        # Return empty dict if no content, otherwise return result
        return result if result else {"status": "deleted"}
    
    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        max_wait: int = DEFAULT_JOB_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Wait for a job to complete.
        
        Args:
            job_id: Job ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait before timing out
            
        Returns:
            Final job status dictionary
            
        Raises:
            TimeoutError: If job doesn't complete within max_wait seconds
            RuntimeError: If job fails
        """
        print(f"Waiting for job {job_id}...")
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")
            
            job = self.get_job(job_id)
            status = job.get('status', {})
            state = status.get('state', job.get('state', 'unknown'))
            
            if state in COMPLETED_STATES:
                print(f"{ICON_SUCCESS} Job {job_id} completed in {int(elapsed)}s")
                return job
            elif state in FAILED_STATES:
                error_msg = status.get('error', job.get('error', 'Unknown error'))
                raise RuntimeError(f"Job {job_id} failed: {error_msg}")
            
            # Show progress for long-running jobs
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                print(f"  Job still running... ({int(elapsed)}s elapsed)")
            
            time.sleep(poll_interval)
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        List all jobs on the GAE.
        
        Returns:
            List of job information dictionaries
        """
        if not self.engine_id:
            raise ValueError("No engine running. Call start_engine() first.")
        
        jobs = self._make_request(
            method='GET',
            endpoint=f"{API_VERSION_PREFIX}jobs",
            error_message="Failed to list jobs"
        )
        
        return jobs if isinstance(jobs, list) else []
    
    def get_graph(self, graph_id: str) -> Dict[str, Any]:
        """Get graph details."""
        try:
            graph = self._make_request(
                method='GET',
                endpoint=f"{API_VERSION_PREFIX}graphs/{graph_id}",
                error_message=f"Failed to get graph {graph_id}"
            )
            return graph
        except Exception:
            # Return empty dict on error (backward compatibility)
            return {}


def get_gae_connection() -> GAEConnectionBase:
    """
    Factory function to get the appropriate GAE connection based on configuration.
    
    Returns:
        GAEConnectionBase: Either GAEManager (AMP) or GenAIGAEConnection (self-managed)
    """
    config = get_gae_config()
    
    if config['deployment_mode'] == DeploymentMode.AMP.value:
        return GAEManager()
    else:
        return GenAIGAEConnection()

