"""
VDS Client - OpenVDS integration layer for REAL data access
"""

import logging
from typing import Optional, Dict, List, Any
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
        
    async def initialize(self):
        """Initialize the VDS client and check for available surveys"""
        if not HAS_OPENVDS:
            logger.warning("OpenVDS library not available, running in demo mode")
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
        logger.info(f"VDS Client initialized (demo_mode={self.demo_mode}, surveys={len(self.available_surveys)})")
    
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
            manager = openvds.getAccessManager(vds_handle)
            layout = manager.volumeDataLayout
            
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
            
            # Get metadata if available
            metadata_access = layout.getMetadataReadAccess()
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
            vds_handle = openvds.open(survey["file_path"])
            self.vds_handles[survey_id] = vds_handle
            return vds_handle
        except Exception as e:
            logger.error(f"Failed to open VDS file for {survey_id}: {e}")
            return None
    
    async def list_surveys(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List available surveys with optional filtering"""
        surveys = self.available_surveys.copy()
        
        if filter_region:
            surveys = [
                s for s in surveys
                if filter_region.lower() in s.get("region", "").lower()
            ]
        
        if filter_year:
            surveys = [
                s for s in surveys
                if str(filter_year) in s.get("acquisition_date", "")
            ]
        
        return surveys
    
    async def get_survey_metadata(
        self,
        survey_id: str,
        include_stats: bool = True
    ) -> Dict[str, Any]:
        """Get detailed metadata for a specific survey"""
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
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract an inline slice from a survey using REAL OpenVDS data access"""
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
            
            manager = openvds.getAccessManager(vds_handle)
            layout = manager.volumeDataLayout
            
            # Convert inline number to index
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            inline_index = inline_axis.coordinateToSampleIndex(float(inline_number))
            
            # Define sample range
            if sample_range:
                sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
                sample_start_idx = sample_axis.coordinateToSampleIndex(float(sample_range[0]))
                sample_end_idx = sample_axis.coordinateToSampleIndex(float(sample_range[1]))
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            
            # Define voxel range for inline slice
            voxel_min = (sample_start_idx, 0, inline_index)
            voxel_max = (
                sample_end_idx,
                layout.getDimensionNumSamples(self.CROSSLINE_DIM),
                inline_index + 1
            )
            
            # Pre-allocate buffer
            num_crosslines = layout.getDimensionNumSamples(self.CROSSLINE_DIM)
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
            
            # Wait for completion
            request.waitForCompletion()
            
            # Calculate statistics from real data
            return {
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
                    "null_traces": int(np.isnan(buffer).any(axis=1).sum())
                },
                "note": "Real data extracted from VDS file"
            }
            
        except Exception as e:
            logger.error(f"Error extracting inline: {e}")
            return {"error": f"Data extraction failed: {str(e)}"}
    
    async def extract_crossline(
        self,
        survey_id: str,
        crossline_number: int,
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract a crossline slice from a survey using REAL OpenVDS data access"""
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
            
            manager = openvds.getAccessManager(vds_handle)
            layout = manager.volumeDataLayout
            
            # Convert crossline number to index
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            crossline_index = crossline_axis.coordinateToSampleIndex(float(crossline_number))
            
            # Define sample range
            if sample_range:
                sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
                sample_start_idx = sample_axis.coordinateToSampleIndex(float(sample_range[0]))
                sample_end_idx = sample_axis.coordinateToSampleIndex(float(sample_range[1]))
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            
            # Define voxel range for crossline slice
            voxel_min = (sample_start_idx, crossline_index, 0)
            voxel_max = (
                sample_end_idx,
                crossline_index + 1,
                layout.getDimensionNumSamples(self.INLINE_DIM)
            )
            
            # Pre-allocate buffer
            num_inlines = layout.getDimensionNumSamples(self.INLINE_DIM)
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
            
            # Wait for completion
            request.waitForCompletion()
            
            # Calculate statistics from real data
            return {
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
                    "null_traces": int(np.isnan(buffer).any(axis=1).sum())
                },
                "note": "Real data extracted from VDS file"
            }
            
        except Exception as e:
            logger.error(f"Error extracting crossline: {e}")
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
            
            manager = openvds.getAccessManager(vds_handle)
            layout = manager.volumeDataLayout
            
            # Convert ranges to indices
            inline_axis = layout.getAxisDescriptor(self.INLINE_DIM)
            crossline_axis = layout.getAxisDescriptor(self.CROSSLINE_DIM)
            sample_axis = layout.getAxisDescriptor(self.SAMPLE_DIM)
            
            inline_start_idx = inline_axis.coordinateToSampleIndex(float(inline_range[0]))
            inline_end_idx = inline_axis.coordinateToSampleIndex(float(inline_range[1]))
            crossline_start_idx = crossline_axis.coordinateToSampleIndex(float(crossline_range[0]))
            crossline_end_idx = crossline_axis.coordinateToSampleIndex(float(crossline_range[1]))
            
            if sample_range:
                sample_start_idx = sample_axis.coordinateToSampleIndex(float(sample_range[0]))
                sample_end_idx = sample_axis.coordinateToSampleIndex(float(sample_range[1]))
            else:
                sample_start_idx = 0
                sample_end_idx = layout.getDimensionNumSamples(self.SAMPLE_DIM)
            
            # Define voxel range
            voxel_min = (sample_start_idx, crossline_start_idx, inline_start_idx)
            voxel_max = (sample_end_idx, crossline_end_idx, inline_end_idx)
            
            # Calculate dimensions
            num_samples = sample_end_idx - sample_start_idx
            num_crosslines = crossline_end_idx - crossline_start_idx
            num_inlines = inline_end_idx - inline_start_idx
            
            # Pre-allocate buffer
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
            
            # Wait for completion
            request.waitForCompletion()
            
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
    
    def __del__(self):
        """Clean up VDS handles on deletion"""
        for handle in self.vds_handles.values():
            try:
                if handle:
                    pass  # OpenVDS handles cleanup automatically with context manager
            except Exception:
                pass
