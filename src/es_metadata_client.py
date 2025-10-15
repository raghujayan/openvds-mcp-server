"""
Elasticsearch Metadata Client - Fast metadata access without opening VDS files

This client connects to the Elasticsearch index populated by vds-metadata-crawler,
providing instant access to VDS metadata for hundreds of files without the overhead
of opening each VDS file.
"""

import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger("es-metadata")

try:
    from elasticsearch import AsyncElasticsearch
    HAS_ELASTICSEARCH = True
except ImportError:
    AsyncElasticsearch = None
    HAS_ELASTICSEARCH = False
    logger.warning("elasticsearch library not available - ES metadata client disabled")


class ESMetadataClient:
    """Client for querying VDS metadata from Elasticsearch"""

    def __init__(
        self,
        es_url: str = "http://elasticsearch:9200",
        index_name: str = "vds-metadata",
        timeout: int = 30
    ):
        self.es_url = es_url
        self.index_name = index_name
        self.timeout = timeout
        self.es: Optional[AsyncElasticsearch] = None
        self.is_connected = False

    async def initialize(self) -> bool:
        """
        Initialize connection to Elasticsearch

        Returns:
            True if connected successfully, False otherwise
        """
        if not HAS_ELASTICSEARCH:
            logger.warning("Elasticsearch library not available")
            return False

        try:
            self.es = AsyncElasticsearch(
                [self.es_url],
                request_timeout=self.timeout
            )

            # Test connection
            info = await self.es.info()
            logger.info(f"Connected to Elasticsearch: {info['version']['number']}")

            # Check if index exists
            index_exists = await self.es.indices.exists(index=self.index_name)
            if not index_exists:
                logger.warning(
                    f"Elasticsearch index '{self.index_name}' does not exist. "
                    "Run vds-metadata-crawler to populate the index."
                )
                return False

            # Get index stats
            stats = await self.es.count(index=self.index_name)
            doc_count = stats['count']
            logger.info(f"Elasticsearch index '{self.index_name}' has {doc_count} VDS datasets")

            self.is_connected = True
            return True

        except Exception as e:
            logger.warning(f"Failed to connect to Elasticsearch: {e}")
            self.is_connected = False
            return False

    async def list_surveys(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List available surveys from Elasticsearch

        Args:
            filter_region: Optional region filter
            filter_year: Optional year filter
            max_results: Maximum number of results to return

        Returns:
            List of survey metadata dictionaries
        """
        if not self.is_connected or not self.es:
            logger.warning("Elasticsearch not connected")
            return []

        try:
            # Build query
            query = {"bool": {"must": []}}

            # Add filters if specified
            if filter_region:
                # Search in file path or any text field that might contain region info
                query["bool"]["must"].append({
                    "query_string": {
                        "query": f"*{filter_region}*",
                        "fields": ["file_path", "volume_type"],
                        "default_operator": "AND"
                    }
                })

            if filter_year:
                # Search in file path or acquisition date
                query["bool"]["must"].append({
                    "query_string": {
                        "query": f"*{filter_year}*",
                        "fields": ["file_path", "import_info.*"],
                        "default_operator": "AND"
                    }
                })

            # If no filters, match all
            if not query["bool"]["must"]:
                query = {"match_all": {}}

            # Execute search
            response = await self.es.search(
                index=self.index_name,
                query=query,
                size=max_results,
                sort=[{"last_modified": {"order": "desc"}}]
            )

            # Parse results into survey format
            surveys = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                survey = self._convert_es_to_survey(source)
                if survey:
                    surveys.append(survey)

            logger.info(f"Found {len(surveys)} surveys matching criteria")
            return surveys

        except Exception as e:
            logger.error(f"Error querying Elasticsearch: {e}")
            return []

    async def get_survey_metadata(
        self,
        survey_id: str,
        include_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific survey

        Args:
            survey_id: Survey ID (derived from filename)
            include_stats: Whether to include statistics (always True for ES)

        Returns:
            Survey metadata dictionary
        """
        if not self.is_connected or not self.es:
            return {"error": "Elasticsearch not connected"}

        try:
            # Search by file path containing survey_id
            response = await self.es.search(
                index=self.index_name,
                query={
                    "query_string": {
                        "query": f"*{survey_id}*",
                        "fields": ["file_path"]
                    }
                },
                size=1
            )

            if response['hits']['total']['value'] == 0:
                return {"error": f"Survey not found: {survey_id}"}

            source = response['hits']['hits'][0]['_source']
            survey = self._convert_es_to_survey(source)

            if not survey:
                return {"error": f"Failed to parse survey: {survey_id}"}

            # Add statistics from ES
            if include_stats:
                survey["statistics"] = {
                    "total_samples": source.get("total_samples", 0),
                    "file_size_bytes": source.get("file_size", 0),
                    "file_size_gb": round(source.get("file_size", 0) / (1024**3), 2),
                    "channel_count": source.get("channel_count", 1),
                    "dimensionality": source.get("dimensions", 3)
                }

            return survey

        except Exception as e:
            logger.error(f"Error getting survey metadata: {e}")
            return {"error": f"Failed to get survey: {str(e)}"}

    def _convert_es_to_survey(self, es_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert Elasticsearch document to survey format

        Args:
            es_doc: Elasticsearch document

        Returns:
            Survey dictionary in VDSClient format
        """
        try:
            # Extract axis descriptors
            axis_descriptors = es_doc.get("axis_descriptors", [])

            # Find inline, crossline, and sample axes
            inline_range = [0, 0]
            crossline_range = [0, 0]
            sample_range = [0, 0]
            sample_unit = "ms"

            for axis in axis_descriptors:
                name = axis.get("name", "").lower()
                if "inline" in name:
                    inline_range = [
                        int(axis.get("coordinateMin", 0)),
                        int(axis.get("coordinateMax", 0))
                    ]
                elif "crossline" in name:
                    crossline_range = [
                        int(axis.get("coordinateMin", 0)),
                        int(axis.get("coordinateMax", 0))
                    ]
                elif "sample" in name or "time" in name or "depth" in name:
                    sample_range = [
                        int(axis.get("coordinateMin", 0)),
                        int(axis.get("coordinateMax", 0))
                    ]
                    sample_unit = axis.get("unit", "ms")

            # Extract survey ID from file path
            file_path = es_doc.get("file_path", "")
            survey_id = file_path.split("/")[-1].replace(".vds", "")

            # Create survey name
            survey_name = survey_id.replace("_", " ").title()

            # Build survey dictionary matching VDSClient format
            survey = {
                "id": survey_id,
                "name": survey_name,
                "file_path": file_path,
                "inline_range": inline_range,
                "crossline_range": crossline_range,
                "sample_range": sample_range,
                "sample_unit": sample_unit,
                "dimensionality": es_doc.get("dimensions", 3),
                "channel_count": len(es_doc.get("channel_descriptors", [1])),
                "data_type": es_doc.get("volume_type", "3D Seismic"),
                "primary_channel": es_doc.get("primary_channel", "Amplitude"),
                "axis_descriptors": axis_descriptors,
                "channel_descriptors": es_doc.get("channel_descriptors", [])
            }

            # Add inline/crossline/sample axis names if available
            for axis in axis_descriptors:
                name = axis.get("name", "")
                if "inline" in name.lower():
                    survey["inline_axis"] = name
                elif "crossline" in name.lower():
                    survey["crossline_axis"] = name
                elif "sample" in name.lower() or "time" in name.lower():
                    survey["sample_axis"] = name

            # Add CRS info if available
            if "crs_info" in es_doc:
                survey["crs_info"] = es_doc["crs_info"]

            # Add spatial extent if available
            if "spatial_extent" in es_doc:
                survey["spatial_extent"] = es_doc["spatial_extent"]

            return survey

        except Exception as e:
            logger.error(f"Error converting ES document to survey: {e}")
            return None

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Elasticsearch index

        Returns:
            Dictionary with index statistics
        """
        if not self.is_connected or not self.es:
            return {"error": "Elasticsearch not connected"}

        try:
            # Get document count
            count_response = await self.es.count(index=self.index_name)
            doc_count = count_response['count']

            # Get aggregations for statistics
            agg_response = await self.es.search(
                index=self.index_name,
                query={"match_all": {}},
                size=0,
                aggs={
                    "total_size": {
                        "sum": {"field": "file_size"}
                    },
                    "volume_types": {
                        "terms": {"field": "volume_type", "size": 20}
                    },
                    "dimensions": {
                        "terms": {"field": "dimensions", "size": 10}
                    }
                }
            )

            aggs = agg_response.get('aggregations', {})

            return {
                "total_datasets": doc_count,
                "total_size_bytes": int(aggs.get('total_size', {}).get('value', 0)),
                "total_size_gb": round(aggs.get('total_size', {}).get('value', 0) / (1024**3), 2),
                "volume_type_distribution": {
                    bucket['key']: bucket['doc_count']
                    for bucket in aggs.get('volume_types', {}).get('buckets', [])
                },
                "dimension_distribution": {
                    str(bucket['key']): bucket['doc_count']
                    for bucket in aggs.get('dimensions', {}).get('buckets', [])
                }
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close Elasticsearch connection"""
        if self.es:
            await self.es.close()
            self.is_connected = False
            logger.info("Elasticsearch connection closed")


async def main():
    """Test Elasticsearch metadata client"""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    es_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9200"

    print(f"\nConnecting to Elasticsearch at {es_url}...\n")

    client = ESMetadataClient(es_url=es_url)

    # Test connection
    connected = await client.initialize()
    if not connected:
        print("Failed to connect to Elasticsearch")
        sys.exit(1)

    # Get index stats
    print("\n" + "="*70)
    print("INDEX STATISTICS")
    print("="*70)
    stats = await client.get_index_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # List surveys
    print("\n" + "="*70)
    print("AVAILABLE SURVEYS (first 10)")
    print("="*70)
    surveys = await client.list_surveys(max_results=10)
    for i, survey in enumerate(surveys, 1):
        print(f"\n{i}. {survey['name']}")
        print(f"   ID: {survey['id']}")
        print(f"   Type: {survey['data_type']}")
        print(f"   Inlines: {survey['inline_range']}")
        print(f"   Crosslines: {survey['crossline_range']}")
        print(f"   Samples: {survey['sample_range']}")

    # Get detailed metadata for first survey
    if surveys:
        print("\n" + "="*70)
        print("DETAILED METADATA (first survey)")
        print("="*70)
        survey_id = surveys[0]['id']
        metadata = await client.get_survey_metadata(survey_id)
        import json
        print(json.dumps(metadata, indent=2, default=str))

    await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
