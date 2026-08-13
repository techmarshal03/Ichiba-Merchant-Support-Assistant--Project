"""
Canary deployment health monitor.
Called by CI/CD after routing 10% of traffic to new pod revision.
Exits 0 (promote) or 1 (rollback) based on error rate and P95 latency.

Usage:
    python scripts/canary_monitor.py --duration 300 --namespace ichiba-prod
"""
import argparse
import asyncio
import logging
import sys
import time

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ERROR_RATE_THRESHOLD = 0.01   # 1%
P95_LATENCY_THRESHOLD = 5.0   # seconds
PROMETHEUS_URL = "http://prometheus-operated.monitoring:9090"


async def query_prometheus(metric: str) -> float:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": metric},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if not results:
            return 0.0
        return float(results[0]["value"][1])


async def monitor(duration_seconds: int) -> bool:
    """
    Monitor canary for `duration_seconds`.
    Returns True if canary is healthy (promote), False if degraded (rollback).
    """
    start = time.monotonic()
    poll_interval = 30

    while time.monotonic() - start < duration_seconds:
        elapsed = time.monotonic() - start
        log.info("Canary monitor: %.0fs / %ds elapsed", elapsed, duration_seconds)

        error_rate = await query_prometheus(
            'rate(ichiba_request_errors_total[2m]) / rate(ichiba_requests_total[2m])'
        )
        p95_latency = await query_prometheus(
            'histogram_quantile(0.95, rate(ichiba_request_latency_seconds_bucket[2m]))'
        )

        log.info("Error rate: %.4f (threshold %.4f)", error_rate, ERROR_RATE_THRESHOLD)
        log.info("P95 latency: %.2fs (threshold %.2fs)", p95_latency, P95_LATENCY_THRESHOLD)

        if error_rate > ERROR_RATE_THRESHOLD:
            log.error("ROLLBACK: error rate %.4f > threshold %.4f", error_rate, ERROR_RATE_THRESHOLD)
            return False

        if p95_latency > P95_LATENCY_THRESHOLD:
            log.error("ROLLBACK: P95 latency %.2fs > threshold %.2fs", p95_latency, P95_LATENCY_THRESHOLD)
            return False

        await asyncio.sleep(poll_interval)

    log.info("PROMOTE: canary healthy for %ds ✓", duration_seconds)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canary deployment monitor")
    parser.add_argument("--duration", type=int, default=300, help="Monitor duration in seconds")
    parser.add_argument("--namespace", type=str, default="ichiba-prod")
    args = parser.parse_args()

    healthy = asyncio.run(monitor(args.duration))
    sys.exit(0 if healthy else 1)
