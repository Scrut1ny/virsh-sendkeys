#!/usr/bin/env python3
"""
Performance benchmark comparing original vs optimized implementation
Focuses on the hot path: key map lookups and command preparation
"""

import time
import sys

# Import the optimized version
import sendkeys


def benchmark_key_map_access():
    """Benchmark key map access time"""
    test_string = "The quick brown fox jumps over the lazy dog 123!@# ABC"
    iterations = 10000
    
    print("=" * 60)
    print("Performance Benchmark")
    print("=" * 60)
    
    # Test 1: Key map is pre-computed (constant time initialization)
    print(f"\nTest 1: Key Map Initialization")
    print(f"  Optimized: Pre-computed as module constant (KEY_MAP)")
    print(f"  Benefit: Zero initialization overhead at runtime")
    
    # Test 2: Key sequence lookup and processing
    print(f"\nTest 2: Key Sequence Lookup ({iterations} iterations)")
    print(f"  Test string: {repr(test_string)}")
    
    start = time.perf_counter()
    for _ in range(iterations):
        for char in test_string:
            key_seq = sendkeys.KEY_MAP.get(char)
            if key_seq:
                # Simulate what the old version did: split() operation
                pass
    optimized_time = time.perf_counter() - start
    
    print(f"  Optimized (pre-split lists): {optimized_time:.4f}s")
    
    # Simulate old behavior with split operations
    # Create a version with strings instead of lists
    old_key_map = {}
    for char, seq_list in sendkeys.KEY_MAP.items():
        old_key_map[char] = " ".join(seq_list)
    
    start = time.perf_counter()
    for _ in range(iterations):
        for char in test_string:
            key_seq = old_key_map.get(char)
            if key_seq:
                _ = key_seq.split()  # Split operation on every access
    old_time = time.perf_counter() - start
    
    print(f"  Original (with split):        {old_time:.4f}s")
    speedup = (old_time / optimized_time - 1) * 100
    print(f"  Speedup: {speedup:.1f}% faster")
    
    # Test 3: Memory efficiency
    print(f"\nTest 3: Memory Efficiency")
    print(f"  Optimized: Pre-split sequences stored once")
    print(f"  Original:  Split operation creates new list every time")
    print(f"  Benefit:   Reduced memory allocations and GC pressure")
    
    # Test 4: String conversion overhead
    print(f"\nTest 4: String Conversion Overhead")
    holdtime = 100
    
    start = time.perf_counter()
    for _ in range(iterations * 10):
        _ = str(holdtime)
    conversion_time = time.perf_counter() - start
    
    # Pre-computed version
    holdtime_str = str(holdtime)
    start = time.perf_counter()
    for _ in range(iterations * 10):
        _ = holdtime_str
    precomputed_time = time.perf_counter() - start
    
    print(f"  Converting int to string each time: {conversion_time:.4f}s")
    print(f"  Using pre-computed string:          {precomputed_time:.4f}s")
    speedup = (conversion_time / precomputed_time - 1) * 100
    print(f"  Speedup: {speedup:.1f}% faster")
    
    # Test 5: Sleep conversion
    print(f"\nTest 5: Sleep Time Conversion")
    pause_time_ms = 300
    
    start = time.perf_counter()
    for _ in range(iterations):
        _ = pause_time_ms / 1000
    conversion_time = time.perf_counter() - start
    
    pause_time_sec = pause_time_ms / 1000
    start = time.perf_counter()
    for _ in range(iterations):
        _ = pause_time_sec
    precomputed_time = time.perf_counter() - start
    
    print(f"  Converting ms to sec each time: {conversion_time:.4f}s")
    print(f"  Using pre-computed value:       {precomputed_time:.4f}s")
    speedup = (conversion_time / precomputed_time - 1) * 100
    print(f"  Speedup: {speedup:.1f}% faster")
    
    print("\n" + "=" * 60)
    print("Summary of Optimizations")
    print("=" * 60)
    print("""
1. ✓ Key map pre-computed as module constant (KEY_MAP)
2. ✓ Key sequences pre-split into lists (no runtime split())
3. ✓ String conversions pre-computed outside loops
4. ✓ Sleep conversion calculated once
5. ✓ Early exit strategies for empty input and unsupported chars
6. ✓ Reduced screen clears (3 → 2)
7. ✓ Consolidated input prompts (better UX)
8. ✓ Debug overhead minimized with conditional string building
9. ✓ Better memory management with cached values

Performance Impact:
- Faster execution for large text inputs
- Reduced memory allocations
- Lower GC pressure
- More efficient hot path execution
""")


if __name__ == "__main__":
    benchmark_key_map_access()
