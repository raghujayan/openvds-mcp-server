"""
VDS Client - OpenVDS integration layer for data access
"""

import logging
from typing import Optional, Dict, List, Any
import asyncio
from pathlib import Path
import os

try:
    import openvds
except ImportError:
    openvds = None

logger = logging.getLogger("vds-client")


class VDSClient:
    """Client for interacting with OpenVDS datasets"""
    
    def __init__(self):
        self.is_connected = False
        self.vds_handle = None
        self.available_surveys: List[Dict[str, Any]] = []
        self.demo_mode = True
        
    async def initialize(self):
        """Initialize the VDS client and check for available surveys"""
        if openvds is None:
            logger.warning("OpenVDS library not available, running in demo mode")
            self.demo_mode = True
            self._setup_demo_data()
        else:
            logger.info("OpenVDS library loaded successfully")
            self.demo_mode = False
            await self._scan_for_surveys()
        
        self.is_connected = True
        logger.info(f"VDS Client initialized (demo_mode={self.demo_mode})")
    
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
        """Scan for available VDS files in configured locations"""
        vds_paths = os.environ.get("VDS_DATA_PATH", "").split(":")
        
        for path_str in vds_paths:
            if not path_str:
                continue
            
            path = Path(path_str)
            if path.exists() and path.is_dir():
                for vds_file in path.glob("**/*.vds"):
                    try:
                        survey_info = await self._extract_survey_info(vds_file)
                        self.available_surveys.append(survey_info)
                    except Exception as e:
                        logger.error(f"Error processing {vds_file}: {e}")
        
        if not self.available_surveys:
            logger.info("No VDS files found, using demo data")
            self._setup_demo_data()
    
    async def _extract_survey_info(self, vds_file: Path) -> Dict[str, Any]:
        """Extract metadata from a VDS file"""
        return {
            "id": vds_file.stem,
            "name": vds_file.stem.replace("_", " ").title(),
            "file_path": str(vds_file)
        }
    
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
        
        if include_stats and self.demo_mode:
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
        
        return metadata
    
    async def extract_inline(
        self,
        survey_id: str,
        inline_number: int,
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract an inline slice from a survey"""
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
        inline_min, inline_max = survey["inline_range"]
        if not (inline_min <= inline_number <= inline_max):
            return {
                "error": f"Inline {inline_number} out of range [{inline_min}, {inline_max}]"
            }
        
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
            "note": "Demo mode - actual data extraction requires VDS file access"
        }
    
    async def extract_crossline(
        self,
        survey_id: str,
        crossline_number: int,
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract a crossline slice from a survey"""
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
        crossline_min, crossline_max = survey["crossline_range"]
        if not (crossline_min <= crossline_number <= crossline_max):
            return {
                "error": f"Crossline {crossline_number} out of range [{crossline_min}, {crossline_max}]"
            }
        
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
            "note": "Demo mode - actual data extraction requires VDS file access"
        }
    
    async def extract_volume_subset(
        self,
        survey_id: str,
        inline_range: List[int],
        crossline_range: List[int],
        sample_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract a volumetric subset from a survey"""
        survey = await self.get_survey_metadata(survey_id, include_stats=False)
        
        if "error" in survey:
            return survey
        
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
            "note": "Demo mode - actual data extraction requires VDS file access"
        }
