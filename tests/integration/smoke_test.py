"""
End-to-end smoke tests for Ichiba Merchant Support Agent.
Runs against a live deployment (staging or local).
"""
from __future__ import annotations
import argparse, asyncio, json, sys
import httpx

SMOKE_SCENARIOS = {
    "ja": {
        "store":    "店舗のバナー画像サイズの規定を教えてください",
        "order":    "注文キャンセルの手続きを教えてください",
        "payment":  "売上金の振込スケジュールを教えてください",
        "campaign": "スーパーSALEの参加条件を教えてください",
        "api":      "RMS APIの認証方法を教えてください",
        "policy":   "出品禁止品の一覧を教えてください",
    },
    "en": {
        "store":    "What are the banner image size requirements?",
        "order":    "How do I cancel an order?",
        "payment":  "What is the payout schedule?",
        "campaign": "How do I qualify for Super Sale?",
        "api":      "How do I authenticate with the RMS API?",
        "policy":   "What items are prohibited on Rakuten Ichiba?",
    },
}

async def run_smoke_test(endpoint: str, lang: str, domain: str, query: str, jwt: str) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{endpoint}/v1/chat",
            headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
            json={"message": query, "session_id": f"smoke-{lang}-{domain}"},
        )
        if resp.status_code != 200:
            print(f"  ✗ [{lang}][{domain}] HTTP {resp.status_code}")
            return False
        # Read SSE stream
        content = ""
        async for line in resp.aiter_lines():
            if line.startswith("data:") and "[DONE]" not in line:
                data = json.loads(line[5:].strip())
                if data.get("content"):
                    content += data["content"]
        if len(content) < 20:
            print(f"  ✗ [{lang}][{domain}] Response too short: {content[:50]!r}")
            return False
        print(f"  ✓ [{lang}][{domain}] OK ({len(content)} chars)")
        return True

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--languages", nargs="+", default=["ja", "en"])
    parser.add_argument("--scenarios", nargs="+", default=["store", "order", "payment"])
    parser.add_argument("--jwt", default="test-token")
    args = parser.parse_args()

    print(f"\n🔍 Smoke testing {args.endpoint}\n")
    results = []
    for lang in args.languages:
        for domain in args.scenarios:
            query = SMOKE_SCENARIOS.get(lang, {}).get(domain)
            if query:
                ok = await run_smoke_test(args.endpoint, lang, domain, query, args.jwt)
                results.append(ok)

    passed = sum(results)
    total  = len(results)
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} smoke tests passed\n")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    asyncio.run(main())
