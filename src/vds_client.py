"""
VDS Client - OpenVDS integration layer for REAL data access

Enhanced with:
- Mount health checking (VPN/NFS awareness)
- Elasticsearch metadata integration (fast queries without opening VDS files)
- Graceful fallback when ES or mounts unavailable
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
import asyncio
from pathlib import Path
import os
import numpy as np

try:
    import openvds
    HAS_OPENVDS = True
except ImportError:
    openvds = None
    HAS_OPENVDS = False

# Import our new modules
from mount_health import MountHealthChecker, MountHealthStatus
from es_metadata_client import ESMetadataClient
from query_cache import get_cache
from seismic_viz import get_visualizer
from data_integrity import get_integrity_agent

logger = logging.getLogger("vds-client")


class VDSClient:
    """Client for interacting with OpenVDS datasets"""
    
    # Standard seismic dimension conventions
    SAMPLE_DIM = 0      # Time/Depth
    CROSSLINE_DIM = 1   
    INLINE_DIM = 2
    
    def __init__(self):
        self.is_connected = False
        self.available_surveys: List[Dict[str, Any]] = []
        self.vds_handles: Dict[str, Any] = {}  # Cache of open VDS handles
        self.demo_mode = False

        # Path configuration for translating ES paths to host paths
        self.vds_data_path = os.getenv("VDS_DATA_PATH", "").split(":")[0]  # Get first path

        # Mount health checking
        self.mount_health_enabled = os.getenv("MOUNT_HEALTH_CHECK_ENABLED", "true").lower() == "true"
        self.mount_health_checker = MountHealthChecker(
            timeout_seconds=float(os.getenv("MOUNT_HEALTH_CHECK_TIMEOUT", "10")),
            max_retries=int(os.getenv("MOUNT_HEALTH_CHECK_RETRIES", "3"))
        )
        self.mount_health_results: Dict[str, Any] = {}

        # Elasticsearch integration
        self.es_enabled = os.getenv("ES_ENABLED", "true").lower() == "true"
        self.es_client: Optional[ESMetadataClient] = None
        self.use_elasticsearch = False  # Will be set during initialization

        # Query cache for performance
        self.cache = get_cache()

        # API response size limits (prevent huge payloads)
        self.max_data_elements = int(os.getenv("MAX_DATA_ELEMENTS", "100000"))  # ~400KB for float32

    def _safe_coordinate_to_index(
        self,
        axis,
        coordinate: float,
        max_index: int
    ) -> int:
        """
        Safely convert coordinate to sample index with rounding and clamping.

        Args:
            axis: OpenVDS axis descriptor
            coordinate: Coordinate value to convert
            max_index: Maximum valid index (dimension size - 1)

        Returns:
            Clamped index in range [0, max_index]
        """
        # Round to nearest sample (not truncate)
        index = round(axis.coordinateToSampleIndex(float(coordinate)))

        # Clamp to valid range
        return max(0, min(index, max_index))

    def _get_no_value_sentinel(self, layout, channel: int = 0) -> Optional[float]:
        """
        Get the no-value sentinel from VDS channel descriptor.

        VDS may use a specific value (not NaN) to represent missing data.

        Args:
            layout: OpenVDS layout
            channel: Channel number (default 0)

        Returns:
            No-value sentinel, or None if not set
        """
        try:
            channel_descriptor = layout.getChannelDescriptor(channel)
            no_value = channel_descriptor.getNoValue()
            return no_value
        except Exception as e:
            logger.debug(f"Could not get no-value sentinel: {e}")
            return None

    def _count_null_traces(
        self,
        buffer: np.ndarray,
        no_value: Optional[float] = None,
        axis: int = 1
    ) -> int:
        """
        Count null/bad traces in extracted data.

        A trace is null if ALL samples are either NaN or equal to no-value sentinel.

        Args:
            buffer: Data buffer (2D or 3D array)
            no_value: No-value sentinel (if None, only check NaN)
            axis: Axis along which to check (default 1 = samples)

        Returns:
            Count of null traces
        """
        # Check for NaN traces
        nan_mask = np.isnan(buffer).all(axis=axis)

        # Check for no-value traces (if sentinel is set and not NaN)
        if no_value is not None and not np.isnan(no_value):
            # For float no-value, use tolerance
            no_value_mask = np.isclose(buffer, no_value, rtol=1e-5).all(axis=axis)
            null_mask = nan_mask | no_value_mask
        else:
            null_mask = nan_mask

        return int(null_mask.sum())

    async def _safe_wait_for_completion(self, request):
        """
        Safely wait for OpenVDS request completion without blocking event loop.

        OpenVDS waitForCompletion() is a blocking call. We run it in a thread pool
        to avoid blocking the async event loop.

        Args:
            request: OpenVDS request object
        """
        await asyncio.to_thread(request.waitForCompletion)

    def _translate_path(self, es_path: str) -> str:
        """
        Translate Elasticsearch path to actual host path

        ES paths are stored as /vds-data/... (Docker mount path)
        Host paths are /Users/raghu/vds-data/... (actual location)

        Args:
            es_path: Path from Elasticsearch metadata

        Returns:
            Translated path that exists on the host filesystem
        """
        if not es_path:
            return es_path

        # If path starts with /vds-data/, replace with actual VDS_DATA_PATH
        if es_path.startswith("/vds-data/"):
            if self.vds_data_path:
                # Replace /vds-data/ with the configured path
                translated = es_path.replace("/vds-data/", self.vds_data_path.rstrip("/") + "/", 1)
                logger.debug(f"Path translation: {es_path} -> {translated}")
                return translated
            else:
                logger.warning(f"VDS_DATA_PATH not configured, cannot translate: {es_path}")
                return es_path

        # Path doesn't need translation
        return es_path

    async def initialize(self):
        """
        Initialize the VDS client with mount health checking and Elasticsearch

        Initialization flow:
        1. Check mount health
        2. Try Elasticsearch for metadata
        3. Fall back to direct VDS scanning if ES unavailable
        4. Fall back to demo mode if all else fails
        """
        logger.info("Initializing VDS Client...")

        # Step 1: Check mount health
        await self._check_mount_health()

        # Step 2: Try Elasticsearch connection
        if self.es_enabled:
            logger.info("Elasticsearch enabled, attempting connection...")
            self.es_client = ESMetadataClient(
                es_url=os.getenv("ES_URL", "http://elasticsearch:9200"),
                index_name=os.getenv("ES_INDEX", "vds-metadata")
            )
            self.use_elasticsearch = await self.es_client.initialize()

            if self.use_elasticsearch:
                logger.info("✓ Elasticsearch connected - using fast metadata queries")
                # Load surveys from Elasticsearch
                await self._load_surveys_from_es()
                # NOTE: VDS files will be opened on-demand when data extraction is requested
                # Opening all 2858+ files at startup would take too long for MCP protocol
                logger.info("VDS files will be opened on-demand for data extraction")
            else:
                logger.warning("✗ Elasticsearch unavailable - falling back to direct VDS scanning")

        # Step 3: Fall back to direct scanning if ES not available
        if not self.use_elasticsearch:
            if not HAS_OPENVDS:
                logger.warning("OpenVDS library not available, running in demo mode")
                self.demo_mode = True
                self._setup_demo_data()
            else:
                # Check if we're using the mock module
                if hasattr(openvds, '__MOCK_MODULE__'):
                    logger.warning("OpenVDS mock module detected - real OpenVDS not installed, running in demo mode")
                    self.demo_mode = True
                    self._setup_demo_data()
                else:
                    logger.info("OpenVDS library loaded successfully")
                    await self._scan_for_surveys()

                if not self.available_surveys:
                    logger.info("No VDS files found, using demo data")
                    self.demo_mode = True
                    self._setup_demo_data()

        self.is_connected = True
        logger.info(
            f"VDS Client initialized:\n"
            f"  - Demo mode: {self.demo_mode}\n"
            f"  - Elasticsearch: {self.use_elasticsearch}\n"
            f"  - Mount health: {self.mount_health_enabled}\n"
            f"  - Surveys available: {len(self.available_surveys)}"
        )

    async def _check_mount_health(self):
        """Check health of all VDS data mounts"""
        if not self.mount_health_enabled:
            logger.info("Mount health checking disabled")
            return

        vds_paths = os.environ.get("VDS_DATA_PATH", "").split(":")
        if not vds_paths or not vds_paths[0]:
            logger.warning("No VDS_DATA_PATH configured")
            return

        logger.info(f"Checking health of {len(vds_paths)} mount(s)...")

        self.mount_health_results = await self.mount_health_checker.check_multiple_mounts(vds_paths)

        # Log results
        healthy_count = 0
        for path, result in self.mount_health_results.items():
            if result.is_healthy:
                healthy_count += 1
                logger.info(f"✓ {result}")
            else:
                logger.error(f"✗ {result}")
                logger.error(f"  Remediation: {self.mount_health_checker.get_remediation_advice(result)}")

        if healthy_count == 0:
            logger.error("WARNING: No healthy mounts detected! VDS data may be inaccessible.")
        elif healthy_count < len(vds_paths):
            logger.warning(f"WARNING: Only {healthy_count}/{len(vds_paths)} mounts are healthy")

    async def _load_surveys_from_es(self):
        """Load survey metadata from Elasticsearch"""
        if not self.es_client or not self.use_elasticsearch:
            return

        try:
            # Load a reasonable number of surveys for caching
            # We don't need ALL surveys in memory - queries will go to ES directly
            surveys = await self.es_client.list_surveys(max_results=500)
            self.available_surveys = surveys
            logger.info(f"Loaded {len(surveys)} surveys from Elasticsearch (cached sample)")
        except Exception as e:
            logger.error(f"Failed to load surveys from Elasticsearch: {e}")
            self.use_elasticsearch = False

    async def _open_vds_handles_from_metadata(self):
        """
        Open VDS files and cache handles based on metadata from Elasticsearch

        This ensures that even when using ES for metadata, we can still
        extract data from VDS files by having open handles cached.
        """
        if not HAS_OPENVDS or not self.available_surveys:
            return

        opened_count = 0
        failed_count = 0

        for survey in self.available_surveys:
            survey_id = survey.get("id")
            file_path = survey.get("file_path")

            if not file_path or file_path.startswith("demo://"):
                continue

            # Check if file exists and is accessible
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"VDS file not found: {file_path}")
                failed_count += 1
                continue

            try:
                # Open VDS file and cache the handle
                vds_handle = openvds.open(str(file_path))
                if vds_handle:
                    self.vds_handles[survey_id] = vds_handle
                    opened_count += 1
                    logger.debug(f"Opened VDS handle for: {survey_id}")
                else:
                    logger.warning(f"openvds.open returned None for: {file_path}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to open VDS file {file_path}: {e}")
                failed_count += 1

        logger.info(f"VDS handles opened: {opened_count} successful, {failed_count} failed")
    
    def _setup_demo_data(self):
        """Set up demo survey data for testing without real VDS files"""
        self.available_surveys = [
            {
                "id": "demo_gulf_mexico_2023",
                "name": "Gulf of Mexico 3D Survey 2023",
                "region": "Gulf of Mexico",
                "acquisition_date": "2023-06-15",
                "inline_range": [1000, 2500],
                "crossline_range": [500, 1800],
                "sample_range": [0, 4000],
                "sample_interval_ms": 4,
                "data_type": "3D Seismic",
                "file_path": "demo://gulf_mexico_2023.vds"
            },
            {
                "id": "demo_north_sea_2024",
                "name": "North Sea Prospect 4D Monitor",
                "region": "North Sea",
                "acquisition_date": "2024-03-20",
                "inline_range": [800, 1900],
                "crossline_range": [400, 1500],
                "sample_range": [0, 3500],
                "sample_interval_ms": 2,
                "data_type": "4D Seismic",
                "file_path": "demo://north_sea_2024.vds"
            },
            {
                "id": "demo_permian_basin_2022",
                "name": "Permian Basin Survey 2022",
                "region": "Permian Basin",
                "acquisition_date": "2022-11-10",
                "inline_range": [1200, 3000],
                "crossline_range": [600, 2200],
                "sample_range": [0, 5000],
                "sample_interval_ms": 4,
                "data_type": "3D Seismic",
                "file_path": "demo://permian_basin_2022.vds"
            }
        ]
    
    async def _scan_for_surveys(self):
        """Scan for available VDS files and extract real metadata"""
        vds_paths = os.environ.get("VDS_DATA_PATH", "").split(":")
        
        for path_str in vds_paths:
            if not path_str:
                continue
            
            path = Path(path_str)
            if path.exists() and path.is_dir():
                for vds_file in path.glob("**/*.vds"):
                    try:
                        survey_info = await self._extract_survey_info(vds_file)
                        if survey_info:
                            self.available_surveys.append(survey_info)
                    except Exception as e:
                        logger.error(f"Error processing {vds_file}: {e}")
    
    async def _extract_survey_info(self, vds_file: Path) -> Optional[Dict[str, Any]]:
        """Extract REAL metadata from a VDS file using OpenVDS"""
        if not HAS_OPENVDS:
            return None
            
        try:
            # Open the VDS file
            vds_handle = openvds.open(str(vds_file))
            if not vds_handle:
                logger.warning(f"openvds.open returned None for {vds_file}")
                return None

            # Get layout using module-level function
            layout = openvds.getLayout(vds_handle)

            # Check dimensionality
            dimensionality = layout.getDimensionality()
            if dimensionality < 3:
                # Skip 2D files for now - MCP server is designed for 3D+ data
                logger.debug(f"Skipping 2D VDS file: {vds_file}")
                if vds_handle:
                    try:
                        openvds.close(vds_handle)
                    except:
                        pass
                return None

            # Get axis descriptors
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)

            # Extract coordinate ranges
            inline_range = [
                int(inline_axis.getCoordinateMin()),
                int(inline_axis.getCoordinateMax())
            ]
            crossline_range = [
                int(crossline_axis.getCoordinateMin()),
                int(crossline_axis.getCoordinateMax())
            ]
            sample_range = [
                int(sample_axis.getCoordinateMin()),
                int(sample_axis.getCoordinateMax())
            ]
            
            # Create survey name from filename
            survey_name = vds_file.stem.replace("_", " ").title()
            
            survey_info = {
                "id": vds_file.stem,
                "name": survey_name,
                "file_path": str(vds_file),
                "inline_range": inline_range,
                "crossline_range": crossline_range,
                "sample_range": sample_range,
                "inline_axis": inline_axis.getName(),
                "crossline_axis": crossline_axis.getName(),
                "sample_axis": sample_axis.getName(),
                "sample_unit": sample_axis.getUnit(),
                "dimensionality": layout.getDimensionality(),
                "channel_count": layout.getChannelCount(),
                "data_type": "3D Seismic" if layout.getDimensionality() == 3 else f"{layout.getDimensionality()}D Data"
            }
            
            # Store the handle for later use
            self.vds_handles[vds_file.stem] = vds_handle

            logger.info(f"Successfully loaded VDS: {survey_name}")
            return survey_info

        except Exception as e:
            logger.error(f"Failed to extract metadata from {vds_file}: {e}")
            # Close handle if it was opened
            if 'vds_handle' in locals() and vds_handle:
                try:
                    openvds.close(vds_handle)
                except:
                    pass
            return None
    
    def _get_vds_handle(self, survey_id: str) -> Optional[Any]:
        """Get or open a VDS handle for the survey"""
        if survey_id in self.vds_handles:
            return self.vds_handles[survey_id]

        # Find survey and open it
        survey = next((s for s in self.available_surveys if s["id"] == survey_id), None)
        if not survey or survey.get("file_path", "").startswith("demo://"):
            return None

        try:
            # Translate ES path to host path
            file_path = self._translate_path(survey["file_path"])
            logger.info(f"Opening VDS file: {file_path}")
            vds_handle = openvds.open(file_path)
            self.vds_handles[survey_id] = vds_handle
            return vds_handle
        except Exception as e:
            logger.error(f"Failed to open VDS file for {survey_id}: {e}")
            logger.error(f"  Original path: {survey.get('file_path')}")
            logger.error(f"  Translated path: {file_path if 'file_path' in locals() else 'N/A'}")
            return None
    
    async def search_surveys(
        self,
        search_query: Optional[str] = None,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Search surveys with free-text query and filters

        Args:
            search_query: Free-text search (searches file paths and names)
            filter_region: Region filter
            filter_year: Year filter
            max_results: Maximum results (internal limit)
        """
        # Check cache first
        cached = self.cache.get_search_results(
            search_query=search_query,
            filter_region=filter_region,
            filter_year=filter_year,
            max_results=max_results
        )
        if cached is not None:
            logger.info(f"Cache HIT: Returning {len(cached)} cached results")
            return cached

        # Use Elasticsearch for search if available
        if self.use_elasticsearch and self.es_client:
            try:
                results = await self.es_client.search_surveys(
                    search_query=search_query,
                    filter_region=filter_region,
                    filter_year=filter_year,
                    max_results=max_results
                )
                # Cache the results
                self.cache.set_search_results(
                    results,
                    search_query=search_query,
                    filter_region=filter_region,
                    filter_year=filter_year,
                    max_results=max_results
                )
                return results
            except Exception as e:
                logger.error(f"Error searching Elasticsearch: {e}")

        # Fall back to in-memory search
        surveys = self.available_surveys.copy()

        # Apply free-text search
        if search_query:
            search_lower = search_query.lower()
            surveys = [
                s for s in surveys
                if search_lower in s.get("name", "").lower() or
                   search_lower in s.get("file_path", "").lower() or
                   search_lower in s.get("region", "").lower() or
                   search_lower in s.get("data_type", "").lower()
            ]

        # Apply region filter
        if filter_region:
            surveys = [
                s for s in surveys
                if filter_region.lower() in s.get("region", "").lower() or
                   filter_region.lower() in s.get("name", "").lower() or
                   filter_region.lower() in s.get("file_path", "").lower()
            ]

        # Apply year filter
        if filter_year:
            surveys = [
                s for s in surveys
                if str(filter_year) in s.get("acquisition_date", "") or
                   str(filter_year) in s.get("file_path", "")
            ]

        return surveys[:max_results]

    async def list_surveys(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        max_results: int = 50  # Default to 50 to keep response under 1MB
    ) -> List[Dict[str, Any]]:
        """
        List available surveys with optional filtering

        Uses Elasticsearch if available for fast queries,
        otherwise filters in-memory cached surveys

        Args:
            filter_region: Optional region filter
            filter_year: Optional year filter
            max_results: Maximum number of results (default 50, max 200)
        """
        # Cap max_results to prevent MCP message size issues (>1MB)
        max_results = min(max_results, 200)

        # Use Elasticsearch for filtering if available
        if self.use_elasticsearch and self.es_client:
            try:
                return await self.es_client.list_surveys(
                    filter_region=filter_region,
                    filter_year=filter_year,
                    max_results=max_results
                )
            except Exception as e:
                logger.error(f"Error querying Elasticsearch, falling back to cached data: {e}")

        # Fall back to in-memory filtering
        surveys = self.available_surveys.copy()

        if filter_region:
            surveys = [
                s for s in surveys
                if filter_region.lower() in s.get("region", "").lower() or
                   filter_region.lower() in s.get("name", "").lower() or
                   filter_region.lower() in s.get("file_path", "").lower()
            ]

        if filter_year:
            surveys = [
                s for s in surveys
                if str(filter_year) in s.get("acquisition_date", "") or
                   str(filter_year) in s.get("file_path", "")
            ]

        # Apply max_results limit
        return surveys[:max_results]

    async def get_survey_statistics(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics about available surveys

        Returns counts, distribution, and sample surveys without loading all data
        """
        # Use Elasticsearch aggregations if available
        if self.use_elasticsearch and self.es_client:
            try:
                return await self.es_client.get_index_stats()
            except Exception as e:
                logger.error(f"Error getting ES stats: {e}")

        # Fall back to in-memory analysis
        surveys = await self.search_surveys(
            filter_region=filter_region,
            filter_year=filter_year,
            max_results=10000
        )

        # Calculate statistics
        total_count = len(surveys)

        # Group by data type
        type_distribution = {}
        for survey in surveys:
            dtype = survey.get("data_type", "Unknown")
            type_distribution[dtype] = type_distribution.get(dtype, 0) + 1

        # Extract unique regions from file paths
        regions = {}
        for survey in surveys:
            path = survey.get("file_path", "")
            # Simple heuristic: extract meaningful path segments
            parts = path.split("/")
            for part in parts:
                if len(part) > 3 and not part.endswith(".vds"):
                    regions[part] = regions.get(part, 0) + 1

        # Get top regions
        top_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_surveys": total_count,
            "filters_applied": {
                "region": filter_region,
                "year": filter_year
            },
            "type_distribution": type_distribution,
            "top_regions": {k: v for k, v in top_regions},
            "sample_surveys": surveys[:5],
            "recommendations": {
                "total_surveys": total_count,
                "suggestion": (
                    "Use search_surveys with filters to narrow down results"
                    if total_count > 100
                    else f"Found {total_count} surveys - use search_surveys to list them"
                )
            }
        }

    async def get_survey_metadata(
        self,
        survey_id: str,
        include_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific survey

        Uses Elasticsearch if available for rich metadata,
        otherwise uses cached survey data
        """
        # Try Elasticsearch first for detailed metadata
        if self.use_elasticsearch and self.es_client:
            try:
                metadata = await self.es_client.get_survey_metadata(
                    survey_id=survey_id,
                    include_stats=include_stats
                )
                if "error" not in metadata:
                    return metadata
                # Fall through to cached data if ES returned error
            except Exception as e:
                logger.error(f"Error getting metadata from Elasticsearch: {e}")

        # Fall back to cached survey data
        survey = next(
            (s for s in self.available_surveys if s["id"] == survey_id),
            None
        )

        if not survey:
            return {"error": f"Survey not found: {survey_id}"}

        metadata = survey.copy()

        # For demo mode surveys, add simulated stats
        if self.demo_mode and include_stats:
            metadata["statistics"] = {
                "amplitude_range": [-1000, 1000],
                "mean_amplitude": 0.5,
                "rms_amplitude": 250.3,
                "total_traces": (
                    (survey["inline_range"][1] - survey["inline_range"][0]) *
                    (survey["crossline_range"][1] - survey["crossline_range"][0])
                ),
                "data_size_gb": 12.5,
                "quality_indicators": {
                    "signal_to_noise_ratio": 8.5,
                    "coverage_percentage": 98.7,
                    "null_trace_percentage": 0.3
                }
            }
            metadata["note"] = "Demo mode - simulated statistics"

        return metadata
    
    async def extract_inline(
        self,
        survey_id: str,
        inline_number: int,
        sample_range: Optional[List[int]] = None,
        return_data: bool = False
    ) -> Dict[str, Any]:
        """
        Extract an inline slice from a survey using REAL OpenVDS data access

        Args:
            survey_id: Survey identifier
            inline_number: Inline number to extract
            sample_range: Optional [start, end] sample range
            return_data: If True, include raw data array in response (for validation)
        """
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
        inline_min, inline_max = survey["inline_range"]
        if not (inline_min <= inline_number <= inline_max):
            return {
                "error": f"Inline {inline_number} out of range [{inline_min}, {inline_max}]"
            }
        
        # If demo mode, return simulated response
        if self.demo_mode or survey.get("file_path", "").startswith("demo://"):
            sample_start, sample_end = sample_range or survey["sample_range"]
            return {
                "survey_id": survey_id,
                "extraction_type": "inline",
                "inline_number": inline_number,
                "sample_range": [sample_start, sample_end],
                "crossline_range": survey["crossline_range"],
                "dimensions": {
                    "crosslines": survey["crossline_range"][1] - survey["crossline_range"][0],
                    "samples": sample_end - sample_start
                },
                "data_summary": {
                    "amplitude_range": [-850, 920],
                    "mean_amplitude": 12.3,
                    "null_traces": 0
                },
                "note": "Demo mode - simulated data"
            }
        
        # REAL DATA EXTRACTION using OpenVDS
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}
            
            # Get layout and access manager using module-level functions
            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Get dimension sizes for clamping
            num_samples_total = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            num_crosslines = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
            num_inlines = layout.getDimensionNumSamples(self.INLINE_DIM)

            # Convert inline number to index with proper rounding and clamping
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            inline_index = self._safe_coordinate_to_index(
                inline_axis, inline_number, num_inlines - 1
            )

            # Define sample range with proper index conversion and clamping
            # User ranges are INCLUSIVE, voxelMax is EXCLUSIVE, so add +1
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            if sample_range:
                sample_start_idx = self._safe_coordinate_to_index(
                    sample_axis, sample_range[0], num_samples_total - 1
                )
                sample_end_idx = self._safe_coordinate_to_index(
                    sample_axis, sample_range[1], num_samples_total - 1
                ) + 1  # Exclusive upper bound
            else:
                sample_start_idx = 0
                sample_end_idx = num_samples_total

            # Validate sample range
            if sample_start_idx >= sample_end_idx:
                return {
                    "error": f"Invalid sample range: start {sample_start_idx} >= end {sample_end_idx}"
                }
            
            # Define voxel range for inline slice (voxelMax is exclusive)
            voxel_min = (sample_start_idx, 0, inline_index)
            voxel_max = (
                sample_end_idx,
                layout.getDimensionNumSamples(self.CROSSLINE_DIM),
                inline_index + 1
            )
            
            # Pre-allocate buffer with REVERSED dimensions for NumPy
            # voxel order is (sample, crossline, inline) but NumPy needs (crossline, sample)
            num_samples = sample_end_idx - sample_start_idx
            buffer = np.empty((num_crosslines, num_samples), dtype=np.float32)

            # Request data extraction
            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )

            # Wait for completion (async-safe - runs in thread pool)
            await self._safe_wait_for_completion(request)

            # Get no-value sentinel for proper null detection
            no_value = self._get_no_value_sentinel(layout, channel=0)
            
            # Calculate statistics from real data
            result = {
                "survey_id": survey_id,
                "extraction_type": "inline",
                "inline_number": inline_number,
                "sample_range": [sample_range[0] if sample_range else survey["sample_range"][0],
                                sample_range[1] if sample_range else survey["sample_range"][1]],
                "crossline_range": survey["crossline_range"],
                "dimensions": {
                    "crosslines": num_crosslines,
                    "samples": num_samples
                },
                "data_summary": {
                    "amplitude_range": [float(buffer.min()), float(buffer.max())],
                    "mean_amplitude": float(buffer.mean()),
                    "std_amplitude": float(buffer.std()),
                    "null_traces": self._count_null_traces(buffer, no_value, axis=1)
                },
                "note": "Real data extracted from VDS file"
            }

            # Optionally include raw data and provenance for validation
            # Check payload size to prevent huge responses
            if return_data:
                total_elements = buffer.size
                if total_elements > self.max_data_elements:
                    logger.warning(
                        f"Data too large for survey={survey_id}, inline={inline_number}: "
                        f"{total_elements} elements (max: {self.max_data_elements}). "
                        f"Not returning raw data."
                    )
                    result["data_warning"] = (
                        f"Data too large ({total_elements} elements, "
                        f"max {self.max_data_elements}). Raw data not included."
                    )
                else:
                    result["data"] = buffer.tolist()  # Convert to list for JSON serialization

                    # Add provenance tracking (only when data is returned)
                    integrity_agent = get_integrity_agent()
                    source_info = {
                        "vds_file": survey.get("file_path", "unknown"),
                        "survey_id": survey_id,
                        "survey_name": survey.get("name", "unknown")
                    }
                    extraction_params = {
                        "section_type": "inline",
                        "section_number": inline_number,
                        "sample_range": result["sample_range"],
                        "crossline_range": result["crossline_range"]
                    }
                    result["provenance"] = integrity_agent.create_provenance_record(
                        buffer, source_info, extraction_params
                    )

            return result

        except Exception as e:
            logger.error(
                f"Error extracting inline for survey={survey_id}, inline={inline_number}: {e}",
                exc_info=True
            )
            return {"error": f"Data extraction failed: {str(e)}"}
    
    async def extract_crossline(
        self,
        survey_id: str,
        crossline_number: int,
        sample_range: Optional[List[int]] = None,
        return_data: bool = False
    ) -> Dict[str, Any]:
        """
        Extract a crossline slice from a survey using REAL OpenVDS data access

        Args:
            survey_id: Survey identifier
            crossline_number: Crossline number to extract
            sample_range: Optional [start, end] sample range
            return_data: If True, include raw data array in response (for validation)
        """
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
        crossline_min, crossline_max = survey["crossline_range"]
        if not (crossline_min <= crossline_number <= crossline_max):
            return {
                "error": f"Crossline {crossline_number} out of range [{crossline_min}, {crossline_max}]"
            }
        
        # If demo mode, return simulated response
        if self.demo_mode or survey.get("file_path", "").startswith("demo://"):
            sample_start, sample_end = sample_range or survey["sample_range"]
            return {
                "survey_id": survey_id,
                "extraction_type": "crossline",
                "crossline_number": crossline_number,
                "sample_range": [sample_start, sample_end],
                "inline_range": survey["inline_range"],
                "dimensions": {
                    "inlines": survey["inline_range"][1] - survey["inline_range"][0],
                    "samples": sample_end - sample_start
                },
                "data_summary": {
                    "amplitude_range": [-780, 890],
                    "mean_amplitude": 8.7,
                    "null_traces": 0
                },
                "note": "Demo mode - simulated data"
            }
        
        # REAL DATA EXTRACTION using OpenVDS
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            # Get layout and access manager using module-level functions
            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Get dimension sizes for clamping
            num_samples_total = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            num_crosslines = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
            num_inlines = layout.getDimensionNumSamples(self.INLINE_DIM)

            # Convert crossline number to index with proper rounding and clamping
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            crossline_index = self._safe_coordinate_to_index(
                crossline_axis, crossline_number, num_crosslines - 1
            )

            # Define sample range with proper index conversion and clamping
            # User ranges are INCLUSIVE, voxelMax is EXCLUSIVE, so add +1
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            if sample_range:
                sample_start_idx = self._safe_coordinate_to_index(
                    sample_axis, sample_range[0], num_samples_total - 1
                )
                sample_end_idx = self._safe_coordinate_to_index(
                    sample_axis, sample_range[1], num_samples_total - 1
                ) + 1  # Exclusive upper bound
            else:
                sample_start_idx = 0
                sample_end_idx = num_samples_total

            # Validate sample range
            if sample_start_idx >= sample_end_idx:
                return {
                    "error": f"Invalid sample range: start {sample_start_idx} >= end {sample_end_idx}"
                }
            
            # Define voxel range for crossline slice (voxelMax is exclusive)
            voxel_min = (sample_start_idx, crossline_index, 0)
            voxel_max = (
                sample_end_idx,
                crossline_index + 1,
                layout.getDimensionNumSamples(self.INLINE_DIM)
            )
            
            # Pre-allocate buffer with REVERSED dimensions for NumPy
            # voxel order is (sample, crossline, inline) but NumPy needs (inline, sample)
            num_samples = sample_end_idx - sample_start_idx
            buffer = np.empty((num_inlines, num_samples), dtype=np.float32)

            # Request data extraction
            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )

            # Wait for completion (async-safe - runs in thread pool)
            await self._safe_wait_for_completion(request)

            # Get no-value sentinel for proper null detection
            no_value = self._get_no_value_sentinel(layout, channel=0)

            # Calculate statistics from real data
            result = {
                "survey_id": survey_id,
                "extraction_type": "crossline",
                "crossline_number": crossline_number,
                "sample_range": [sample_range[0] if sample_range else survey["sample_range"][0],
                                sample_range[1] if sample_range else survey["sample_range"][1]],
                "inline_range": survey["inline_range"],
                "dimensions": {
                    "inlines": num_inlines,
                    "samples": num_samples
                },
                "data_summary": {
                    "amplitude_range": [float(buffer.min()), float(buffer.max())],
                    "mean_amplitude": float(buffer.mean()),
                    "std_amplitude": float(buffer.std()),
                    "null_traces": self._count_null_traces(buffer, no_value, axis=1)
                },
                "note": "Real data extracted from VDS file"
            }

            # Optionally include raw data and provenance for validation
            # Check payload size to prevent huge responses
            if return_data:
                total_elements = buffer.size
                if total_elements > self.max_data_elements:
                    logger.warning(
                        f"Data too large for survey={survey_id}, crossline={crossline_number}: "
                        f"{total_elements} elements (max: {self.max_data_elements}). "
                        f"Not returning raw data."
                    )
                    result["data_warning"] = (
                        f"Data too large ({total_elements} elements, "
                        f"max {self.max_data_elements}). Raw data not included."
                    )
                else:
                    result["data"] = buffer.tolist()  # Convert to list for JSON serialization

                    # Add provenance tracking (only when data is returned)
                    integrity_agent = get_integrity_agent()
                    source_info = {
                        "vds_file": survey.get("file_path", "unknown"),
                        "survey_id": survey_id,
                        "survey_name": survey.get("name", "unknown")
                    }
                    extraction_params = {
                        "section_type": "crossline",
                        "section_number": crossline_number,
                        "sample_range": result["sample_range"],
                        "inline_range": result["inline_range"]
                    }
                    result["provenance"] = integrity_agent.create_provenance_record(
                        buffer, source_info, extraction_params
                    )

            return result

        except Exception as e:
            logger.error(
                f"Error extracting crossline for survey={survey_id}, crossline={crossline_number}: {e}",
                exc_info=True
            )
            return {"error": f"Data extraction failed: {str(e)}"}
    
    async def extract_volume_subset(
        self,
        survey_id: str,
        inline_range: List[int],
        crossline_range: List[int],
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract a volumetric subset from a survey using REAL OpenVDS data access"""
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
        # If demo mode, return simulated response
        if self.demo_mode or survey.get("file_path", "").startswith("demo://"):
            sample_start, sample_end = sample_range or survey["sample_range"]
            inline_count = inline_range[1] - inline_range[0]
            crossline_count = crossline_range[1] - crossline_range[0]
            sample_count = sample_end - sample_start
            volume_size_mb = (inline_count * crossline_count * sample_count * 4) / (1024 * 1024)
            
            return {
                "survey_id": survey_id,
                "extraction_type": "volume_subset",
                "inline_range": inline_range,
                "crossline_range": crossline_range,
                "sample_range": [sample_start, sample_end],
                "dimensions": {
                    "inlines": inline_count,
                    "crosslines": crossline_count,
                    "samples": sample_count
                },
                "volume_statistics": {
                    "total_traces": inline_count * crossline_count,
                    "estimated_size_mb": round(volume_size_mb, 2),
                    "amplitude_range": [-920, 1050],
                    "mean_amplitude": 15.2
                },
                "note": "Demo mode - simulated data"
            }
        
        # REAL DATA EXTRACTION using OpenVDS
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            # Get layout and access manager using module-level functions
            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Convert ranges to indices with proper rounding
            # User ranges are INCLUSIVE, voxelMax is EXCLUSIVE, so add +1
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            
            inline_start_idx = int(inline_axis.coordinateToSampleIndex(float(inline_range[0])))
            inline_end_idx = int(inline_axis.coordinateToSampleIndex(float(inline_range[1]))) + 1
            crossline_start_idx = int(crossline_axis.coordinateToSampleIndex(float(crossline_range[0])))
            crossline_end_idx = int(crossline_axis.coordinateToSampleIndex(float(crossline_range[1]))) + 1
            
            if sample_range:
                sample_start_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[0])))
                sample_end_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[1]))) + 1
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            
            # Define voxel range (voxelMax is exclusive)
            voxel_min = (sample_start_idx, crossline_start_idx, inline_start_idx)
            voxel_max = (sample_end_idx, crossline_end_idx, inline_end_idx)
            
            # Calculate dimensions
            num_samples = sample_end_idx - sample_start_idx
            num_crosslines = crossline_end_idx - crossline_start_idx
            num_inlines = inline_end_idx - inline_start_idx
            
            # Pre-allocate buffer with REVERSED dimensions for NumPy
            # voxel order is (sample, crossline, inline) but NumPy needs (inline, crossline, sample)
            buffer = np.empty((num_inlines, num_crosslines, num_samples), dtype=np.float32)
            
            # Request data extraction
            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )
            
            # Wait for completion (async-safe - runs in thread pool)
            await self._safe_wait_for_completion(request)
            
            # Calculate statistics
            volume_size_mb = buffer.nbytes / (1024 * 1024)
            
            return {
                "survey_id": survey_id,
                "extraction_type": "volume_subset",
                "inline_range": inline_range,
                "crossline_range": crossline_range,
                "sample_range": [sample_range[0] if sample_range else survey["sample_range"][0],
                                sample_range[1] if sample_range else survey["sample_range"][1]],
                "dimensions": {
                    "inlines": num_inlines,
                    "crosslines": num_crosslines,
                    "samples": num_samples
                },
                "volume_statistics": {
                    "total_traces": num_inlines * num_crosslines,
                    "actual_size_mb": round(volume_size_mb, 2),
                    "amplitude_range": [float(buffer.min()), float(buffer.max())],
                    "mean_amplitude": float(buffer.mean()),
                    "std_amplitude": float(buffer.std())
                },
                "note": "Real data extracted from VDS file"
            }
            
        except Exception as e:
            logger.error(f"Error extracting volume: {e}")
            return {"error": f"Data extraction failed: {str(e)}"}
    
    async def extract_inline_image(
        self,
        survey_id: str,
        inline_number: int,
        sample_range: Optional[List[int]] = None,
        colormap: str = 'seismic',
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """
        Extract inline and generate seismic image

        Args:
            survey_id: Survey identifier
            inline_number: Inline number to extract
            sample_range: Optional [start, end] sample range
            colormap: 'seismic' (red-white-blue), 'gray', or 'petrel'
            clip_percentile: Amplitude clipping percentile (default 99%)

        Returns:
            Dict with image_data (PNG bytes) and metadata
        """
        # First extract the data
        extraction_result = await self.extract_inline(survey_id, inline_number, sample_range)

        if "error" in extraction_result:
            return extraction_result

        # If demo mode, return simulated image info
        if extraction_result.get("note") == "Demo mode - simulated data":
            return {
                **extraction_result,
                "visualization": "Image generation not available in demo mode",
                "suggestion": "Connect to real VDS data to generate seismic images"
            }

        # Extract the data again to get the NumPy buffer (we need to refactor this)
        # For now, let's get the data by re-extracting
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Get the survey metadata for ranges
            survey = await self.get_survey_metadata(survey_id, include_stats=False)

            # Convert inline number to index
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            inline_index = int(inline_axis.coordinateToSampleIndex(float(inline_number)))

            # Define sample range
            if sample_range:
                sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
                sample_start_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[0])))
                sample_end_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[1]))) + 1
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
                sample_range = survey["sample_range"]

            # Define voxel range
            voxel_min = (sample_start_idx, 0, inline_index)
            voxel_max = (
                sample_end_idx,
                layout.getDimensionNumSamples(self.CROSSLINE_DIM),
                inline_index + 1
            )

            # Extract data
            num_crosslines = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
            num_samples = sample_end_idx - sample_start_idx
            buffer = np.empty((num_crosslines, num_samples), dtype=np.float32)

            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )
            request.waitForCompletion()

            # Generate visualization
            visualizer = get_visualizer()
            img_bytes = visualizer.create_inline_image(
                data=buffer,
                inline_number=inline_number,
                crossline_range=tuple(survey["crossline_range"]),
                sample_range=tuple(sample_range),
                colormap=colormap,
                clip_percentile=clip_percentile
            )

            # Compress if needed
            img_bytes = visualizer.compress_image(img_bytes, max_size_kb=800)

            return {
                **extraction_result,
                "image_data": img_bytes,
                "image_format": "PNG",
                "image_size_kb": len(img_bytes) / 1024,
                "colormap": colormap,
                "clip_percentile": clip_percentile
            }

        except Exception as e:
            logger.error(f"Error generating inline image: {e}")
            return {"error": f"Image generation failed: {str(e)}"}

    async def extract_crossline_image(
        self,
        survey_id: str,
        crossline_number: int,
        sample_range: Optional[List[int]] = None,
        colormap: str = 'seismic',
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """Extract crossline and generate seismic image"""
        # Similar implementation to inline
        extraction_result = await self.extract_crossline(survey_id, crossline_number, sample_range)

        if "error" in extraction_result:
            return extraction_result

        if extraction_result.get("note") == "Demo mode - simulated data":
            return {
                **extraction_result,
                "visualization": "Image generation not available in demo mode"
            }

        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)
            survey = await self.get_survey_metadata(survey_id, include_stats=False)

            # Convert crossline number to index
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            crossline_index = int(crossline_axis.coordinateToSampleIndex(float(crossline_number)))

            # Define sample range
            if sample_range:
                sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
                sample_start_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[0])))
                sample_end_idx = int(sample_axis.coordinateToSampleIndex(float(sample_range[1]))) + 1
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
                sample_range = survey["sample_range"]

            # Define voxel range
            voxel_min = (sample_start_idx, crossline_index, 0)
            voxel_max = (
                sample_end_idx,
                crossline_index + 1,
                layout.getDimensionNumSamples(self.INLINE_DIM)
            )

            # Extract data
            num_inlines = layout.getDimensionNumSamples(self.INLINE_DIM)
            num_samples = sample_end_idx - sample_start_idx
            buffer = np.empty((num_inlines, num_samples), dtype=np.float32)

            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )
            request.waitForCompletion()

            # Generate visualization
            visualizer = get_visualizer()
            img_bytes = visualizer.create_crossline_image(
                data=buffer,
                crossline_number=crossline_number,
                inline_range=tuple(survey["inline_range"]),
                sample_range=tuple(sample_range),
                colormap=colormap,
                clip_percentile=clip_percentile
            )

            img_bytes = visualizer.compress_image(img_bytes, max_size_kb=800)

            return {
                **extraction_result,
                "image_data": img_bytes,
                "image_format": "PNG",
                "image_size_kb": len(img_bytes) / 1024,
                "colormap": colormap,
                "clip_percentile": clip_percentile
            }

        except Exception as e:
            logger.error(f"Error generating crossline image: {e}")
            return {"error": f"Image generation failed: {str(e)}"}

    async def extract_timeslice(
        self,
        survey_id: str,
        time_value: int,
        inline_range: Optional[List[int]] = None,
        crossline_range: Optional[List[int]] = None,
        return_data: bool = False
    ) -> Dict[str, Any]:
        """
        Extract a time/depth slice from a survey

        Args:
            survey_id: Survey identifier
            time_value: Time/depth value to extract
            inline_range: Optional [start, end] inline range
            crossline_range: Optional [start, end] crossline range
            return_data: If True, include raw data array in response (for validation)
        """
        survey = await self.get_survey_metadata(survey_id, include_stats=False)

        if "error" in survey:
            return survey

        # Validate time value
        time_min, time_max = survey["sample_range"]
        if not (time_min <= time_value <= time_max):
            return {
                "error": f"Time value {time_value} out of range [{time_min}, {time_max}]"
            }

        # If demo mode, return simulated response
        if self.demo_mode or survey.get("file_path", "").startswith("demo://"):
            return {
                "survey_id": survey_id,
                "extraction_type": "timeslice",
                "time_value": time_value,
                "inline_range": inline_range or survey["inline_range"],
                "crossline_range": crossline_range or survey["crossline_range"],
                "note": "Demo mode - simulated data"
            }

        # REAL DATA EXTRACTION
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Get dimension sizes for clamping
            num_samples_total = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            num_crosslines_total = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
            num_inlines_total = layout.getDimensionNumSamples(self.INLINE_DIM)

            # Convert time value to sample index with proper rounding and clamping
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            sample_index = self._safe_coordinate_to_index(
                sample_axis, time_value, num_samples_total - 1
            )

            # Define inline and crossline ranges with proper conversion and clamping
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            if inline_range:
                inline_start_idx = self._safe_coordinate_to_index(
                    inline_axis, inline_range[0], num_inlines_total - 1
                )
                inline_end_idx = self._safe_coordinate_to_index(
                    inline_axis, inline_range[1], num_inlines_total - 1
                ) + 1  # Exclusive upper bound
            else:
                inline_start_idx = 0
                inline_end_idx = num_inlines_total
                inline_range = survey["inline_range"]

            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            if crossline_range:
                crossline_start_idx = self._safe_coordinate_to_index(
                    crossline_axis, crossline_range[0], num_crosslines_total - 1
                )
                crossline_end_idx = self._safe_coordinate_to_index(
                    crossline_axis, crossline_range[1], num_crosslines_total - 1
                ) + 1  # Exclusive upper bound
            else:
                crossline_start_idx = 0
                crossline_end_idx = num_crosslines_total
                crossline_range = survey["crossline_range"]

            # Validate ranges
            if inline_start_idx >= inline_end_idx:
                return {
                    "error": f"Invalid inline range: start {inline_start_idx} >= end {inline_end_idx}"
                }
            if crossline_start_idx >= crossline_end_idx:
                return {
                    "error": f"Invalid crossline range: start {crossline_start_idx} >= end {crossline_end_idx}"
                }

            # Define voxel range
            voxel_min = (sample_index, crossline_start_idx, inline_start_idx)
            voxel_max = (sample_index + 1, crossline_end_idx, inline_end_idx)

            # Extract data
            num_inlines = inline_end_idx - inline_start_idx
            num_crosslines = crossline_end_idx - crossline_start_idx
            buffer = np.empty((num_inlines, num_crosslines), dtype=np.float32)

            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )

            # Wait for completion (async-safe - runs in thread pool)
            await self._safe_wait_for_completion(request)

            # Get no-value sentinel for proper null detection
            no_value = self._get_no_value_sentinel(layout, channel=0)

            # Calculate statistics
            result = {
                "survey_id": survey_id,
                "extraction_type": "timeslice",
                "time_value": time_value,
                "inline_range": list(inline_range),
                "crossline_range": list(crossline_range),
                "dimensions": {
                    "inlines": num_inlines,
                    "crosslines": num_crosslines
                },
                "data_summary": {
                    "amplitude_range": [float(buffer.min()), float(buffer.max())],
                    "mean_amplitude": float(buffer.mean()),
                    "std_amplitude": float(buffer.std()),
                    "null_pixels": self._count_null_traces(buffer, no_value, axis=0)  # For 2D timeslice
                },
                "note": "Real data extracted from VDS file"
            }

            # Optionally include raw data and provenance for validation
            # Check payload size to prevent huge responses
            if return_data:
                total_elements = buffer.size
                if total_elements > self.max_data_elements:
                    logger.warning(
                        f"Data too large for survey={survey_id}, time={time_value}: "
                        f"{total_elements} elements (max: {self.max_data_elements}). "
                        f"Not returning raw data."
                    )
                    result["data_warning"] = (
                        f"Data too large ({total_elements} elements, "
                        f"max {self.max_data_elements}). Raw data not included."
                    )
                else:
                    result["data"] = buffer.tolist()

                    # Add provenance tracking (only when data is returned)
                    integrity_agent = get_integrity_agent()
                    source_info = {
                        "vds_file": survey.get("file_path", "unknown"),
                        "survey_id": survey_id,
                        "survey_name": survey.get("name", "unknown")
                    }
                    extraction_params = {
                        "section_type": "timeslice",
                        "section_number": time_value,
                        "inline_range": result["inline_range"],
                        "crossline_range": result["crossline_range"]
                    }
                    result["provenance"] = integrity_agent.create_provenance_record(
                        buffer, source_info, extraction_params
                    )

            return result

        except Exception as e:
            logger.error(
                f"Error extracting timeslice for survey={survey_id}, time={time_value}: {e}",
                exc_info=True
            )
            return {"error": f"Data extraction failed: {str(e)}"}

    async def extract_timeslice_image(
        self,
        survey_id: str,
        time_value: int,
        inline_range: Optional[List[int]] = None,
        crossline_range: Optional[List[int]] = None,
        colormap: str = 'seismic',
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """
        Extract time/depth slice and generate seismic image (map view)

        Args:
            survey_id: Survey identifier
            time_value: Time/depth value to extract
            inline_range: Optional [start, end] inline range
            crossline_range: Optional [start, end] crossline range
            colormap: 'seismic' (red-white-blue), 'gray', or 'petrel'
            clip_percentile: Amplitude clipping percentile (default 99%)

        Returns:
            Dict with image_data (PNG bytes) and metadata
        """
        # Get survey metadata
        survey = await self.get_survey_metadata(survey_id, include_stats=False)

        if "error" in survey:
            return survey

        # Validate time value is in range
        time_min, time_max = survey["sample_range"]
        if not (time_min <= time_value <= time_max):
            return {
                "error": f"Time value {time_value} out of range [{time_min}, {time_max}]"
            }

        # If demo mode, return simulated response
        if self.demo_mode or survey.get("file_path", "").startswith("demo://"):
            return {
                "survey_id": survey_id,
                "extraction_type": "timeslice",
                "time_value": time_value,
                "inline_range": inline_range or survey["inline_range"],
                "crossline_range": crossline_range or survey["crossline_range"],
                "visualization": "Image generation not available in demo mode",
                "note": "Demo mode - simulated data"
            }

        # REAL DATA EXTRACTION
        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            layout = openvds.getLayout(vds_handle)
            manager = openvds.getAccessManager(vds_handle)

            # Convert time value to sample index
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            sample_index = int(sample_axis.coordinateToSampleIndex(float(time_value)))

            # Define inline and crossline ranges
            if inline_range:
                inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
                inline_start_idx = int(inline_axis.coordinateToSampleIndex(float(inline_range[0])))
                inline_end_idx = int(inline_axis.coordinateToSampleIndex(float(inline_range[1]))) + 1
            else:
                inline_start_idx = 0
                inline_end_idx = layout.getDimensionNumSamples(self.INLINE_DIM)
                inline_range = survey["inline_range"]

            if crossline_range:
                crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
                crossline_start_idx = int(crossline_axis.coordinateToSampleIndex(float(crossline_range[0])))
                crossline_end_idx = int(crossline_axis.coordinateToSampleIndex(float(crossline_range[1]))) + 1
            else:
                crossline_start_idx = 0
                crossline_end_idx = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
                crossline_range = survey["crossline_range"]

            # Define voxel range for time slice (single sample plane)
            voxel_min = (sample_index, crossline_start_idx, inline_start_idx)
            voxel_max = (sample_index + 1, crossline_end_idx, inline_end_idx)

            # Extract data
            num_inlines = inline_end_idx - inline_start_idx
            num_crosslines = crossline_end_idx - crossline_start_idx
            buffer = np.empty((num_inlines, num_crosslines), dtype=np.float32)

            request = manager.requestVolumeSubset(
                data_out=buffer,
                dimensionsND=openvds.DimensionsND.Dimensions_012,
                min=voxel_min,
                max=voxel_max,
                lod=0,
                channel=0
            )
            request.waitForCompletion()

            # Generate visualization
            visualizer = get_visualizer()
            img_bytes = visualizer.create_timeslice_image(
                data=buffer,
                time_value=time_value,
                inline_range=tuple(inline_range),
                crossline_range=tuple(crossline_range),
                colormap=colormap,
                clip_percentile=clip_percentile
            )

            # More aggressive compression for timeslices (they tend to be larger)
            img_bytes = visualizer.compress_image(img_bytes, max_size_kb=600)

            # Calculate statistics
            return {
                "survey_id": survey_id,
                "extraction_type": "timeslice",
                "time_value": time_value,
                "inline_range": inline_range,
                "crossline_range": crossline_range,
                "dimensions": {
                    "inlines": num_inlines,
                    "crosslines": num_crosslines
                },
                "statistics": {
                    "amplitude_range": [float(buffer.min()), float(buffer.max())],
                    "mean_amplitude": float(buffer.mean()),
                    "std_amplitude": float(buffer.std())
                },
                "image_data": img_bytes,
                "image_format": "PNG",
                "image_size_kb": len(img_bytes) / 1024,
                "colormap": colormap,
                "clip_percentile": clip_percentile,
                "note": "Real data extracted from VDS file"
            }

        except Exception as e:
            logger.error(f"Error generating timeslice image: {e}")
            return {"error": f"Image generation failed: {str(e)}"}

    async def get_facets(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get pre-computed facets for fast filtering

        Returns available regions, years, data types with counts
        """
        # Check cache first
        cached = self.cache.get_facets(
            filter_region=filter_region,
            filter_year=filter_year
        )
        if cached is not None:
            logger.info("Cache HIT: Returning cached facets")
            return cached

        # Use Elasticsearch aggregations if available
        if self.use_elasticsearch and self.es_client:
            try:
                # Get all matching surveys first
                surveys = await self.search_surveys(
                    filter_region=filter_region,
                    filter_year=filter_year,
                    max_results=10000
                )

                # Compute facets from results
                facets = self._compute_facets(surveys)

                # Cache for 15 minutes
                self.cache.set_facets(
                    facets,
                    filter_region=filter_region,
                    filter_year=filter_year
                )

                return facets

            except Exception as e:
                logger.error(f"Error computing facets: {e}")

        # Fall back to in-memory computation
        surveys = await self.search_surveys(
            filter_region=filter_region,
            filter_year=filter_year,
            max_results=10000
        )
        return self._compute_facets(surveys)

    def _compute_facets(self, surveys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute facets from survey list"""
        regions = {}
        years = {}
        data_types = {}

        for survey in surveys:
            # Extract region from path
            path = survey.get("file_path", "")
            path_parts = [p for p in path.split("/") if p and len(p) > 2 and not p.endswith(".vds")]
            for part in path_parts[:3]:  # Use top-level path segments
                regions[part] = regions.get(part, 0) + 1

            # Extract year from path or metadata
            for part in path.split("/"):
                if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2030:
                    years[int(part)] = years.get(int(part), 0) + 1

            # Data type
            dtype = survey.get("data_type", "Unknown")
            data_types[dtype] = data_types.get(dtype, 0) + 1

        # Sort and limit
        top_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:20]
        all_years = sorted(years.items(), key=lambda x: x[0], reverse=True)
        top_types = sorted(data_types.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_surveys": len(surveys),
            "regions": {k: v for k, v in top_regions},
            "years": {k: v for k, v in all_years},
            "data_types": {k: v for k, v in top_types},
            "facet_counts": {
                "regions": len(regions),
                "years": len(years),
                "data_types": len(data_types)
            },
            "cache_info": "Cached for 15 minutes"
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache.get_stats()

    def __del__(self):
        """Clean up VDS handles on deletion"""
        for handle in self.vds_handles.values():
            try:
                if handle:
                    pass  # OpenVDS handles cleanup automatically with context manager
            except Exception:
                pass
