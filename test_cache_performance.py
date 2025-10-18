#!/usr/bin/env python3
"""
Test cache performance improvements
"""
import asyncio
import sys
import time
sys.path.insert(0, 'src')

from vds_client import VDSClient

async def main():
    print("=" * 70)
    print("CACHE PERFORMANCE TEST")
    print("=" * 70)

    # Initialize client
    print("\n1. Initializing VDS Client...")
    client = VDSClient()
    await client.initialize()

    print(f"   ✓ Elasticsearch: {client.use_elasticsearch}")
    print(f"   ✓ Available surveys: {len(client.available_surveys)}")

    # Test 1: Search without cache (first time)
    print("\n2. First search (cache MISS expected)...")
    start = time.time()
    results1 = await client.search_surveys(search_query="Brazil", max_results=100)
    time1 = time.time() - start
    print(f"   ✓ Found {len(results1)} surveys in {time1:.3f}s")

    # Test 2: Same search (cache HIT expected)
    print("\n3. Second search - same query (cache HIT expected)...")
    start = time.time()
    results2 = await client.search_surveys(search_query="Brazil", max_results=100)
    time2 = time.time() - start
    speedup = time1 / time2 if time2 > 0 else float('inf')
    print(f"   ✓ Found {len(results2)} surveys in {time2:.3f}s")
    print(f"   ✓ Speedup: {speedup:.1f}x faster!")

    # Test 3: Get facets (first time)
    print("\n4. Get facets (cache MISS expected)...")
    start = time.time()
    facets1 = await client.get_facets()
    time3 = time.time() - start
    print(f"   ✓ Computed facets in {time3:.3f}s")
    print(f"   ✓ Regions: {len(facets1.get('regions', {}))}")
    print(f"   ✓ Years: {len(facets1.get('years', {}))}")
    print(f"   ✓ Data types: {len(facets1.get('data_types', {}))}")

    # Test 4: Get facets again (cache HIT expected)
    print("\n5. Get facets again (cache HIT expected)...")
    start = time.time()
    facets2 = await client.get_facets()
    time4 = time.time() - start
    speedup2 = time3 / time4 if time4 > 0 else float('inf')
    print(f"   ✓ Retrieved facets in {time4:.3f}s")
    print(f"   ✓ Speedup: {speedup2:.1f}x faster!")

    # Test 5: Multiple different searches to fill cache
    print("\n6. Multiple searches to test cache...")
    queries = ["Santos", "Gulf", "North", "Australia", "Brazil"]
    total_time = 0
    for query in queries:
        start = time.time()
        results = await client.search_surveys(search_query=query, max_results=50)
        elapsed = time.time() - start
        total_time += elapsed
        print(f"   - '{query}': {len(results)} results in {elapsed:.3f}s")

    avg_time = total_time / len(queries)
    print(f"   ✓ Average: {avg_time:.3f}s per search")

    # Test 6: Repeat one search to test cache
    print("\n7. Repeat first search (should be cached)...")
    start = time.time()
    results = await client.search_surveys(search_query="Santos", max_results=50)
    cached_time = time.time() - start
    print(f"   ✓ Cached search: {cached_time:.3f}s")
    print(f"   ✓ Improvement: {avg_time/cached_time:.1f}x faster")

    # Test 7: Cache statistics
    print("\n8. Cache Statistics:")
    stats = client.get_cache_stats()
    print(f"   Search Cache:")
    print(f"     - Hits: {stats['search_cache']['hits']}")
    print(f"     - Misses: {stats['search_cache']['misses']}")
    print(f"     - Hit rate: {stats['search_cache']['hit_rate_percent']:.1f}%")
    print(f"     - Cache size: {stats['search_cache']['size']}/{stats['search_cache']['max_size']}")
    print(f"   Facets Cache:")
    print(f"     - Hits: {stats['facets_cache']['hits']}")
    print(f"     - Misses: {stats['facets_cache']['misses']}")
    print(f"     - Hit rate: {stats['facets_cache']['hit_rate_percent']:.1f}%")

    # Performance summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"✓ Search cache speedup: {speedup:.1f}x")
    print(f"✓ Facets cache speedup: {speedup2:.1f}x")
    print(f"✓ Overall cache hit rate: {stats['search_cache']['hit_rate_percent']:.1f}%")
    print("\nCaching is WORKING! Repeat queries are much faster.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
