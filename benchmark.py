import asyncio
import aiohttp
import time
import argparse
import statistics

async def make_request(session, url, method="POST"):
    try:
        if method == "POST":
            async with session.post(url) as response:
                return await response.json()
        else:
            async with session.get(url) as response:
                return await response.json()
    except Exception as e:
        return {"error": str(e)}

async def run_benchmark(url, num_requests, concurrency):
    print(f"Benchmarking {url} with {num_requests} requests (concurrency: {concurrency})...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Create batches of tasks to limit concurrency
        latencies = []
        for i in range(0, num_requests, concurrency):
            batch_size = min(concurrency, num_requests - i)
            tasks = [make_request(session, url) for _ in range(batch_size)]
            results = await asyncio.gather(*tasks)
            
            for r in results:
                if "latency_ms" in r:
                    latencies.append(r["latency_ms"])
        
        total_time = time.time() - start_time
        
        # Verify final state
        final_state = await make_request(session, url.replace("/increment", "/state"), method="GET")
        
        print(f"--- Results for {url} ---")
        print(f"Total time: {total_time:.2f}s")
        print(f"Requests/sec: {num_requests / total_time:.2f}")
        if latencies:
            print(f"Average internal latency: {statistics.mean(latencies):.2f}ms")
            print(f"Max internal latency: {max(latencies):.2f}ms")
            print(f"P95 internal latency: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")
        print(f"Final state counter: {final_state.get('counter', 'unknown')}")
        print("--------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark state persistence methods.")
    parser.add_argument("--url", type=str, default="http://localhost:8000/increment", help="Target URL")
    parser.add_argument("--requests", type=int, default=1000, help="Total number of requests")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrency level")
    
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.url, args.requests, args.concurrency))
