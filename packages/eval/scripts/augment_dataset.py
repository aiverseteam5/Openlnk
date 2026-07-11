"""Augment eval seed cases to ≥500 messages via LLM paraphrasing.

Takes the hand-crafted seeds, generates 4-5 paraphrased variants per seed
while preserving the gold labels. Adversarial cases get more variants since
they're cheap to validate.

Usage:
    python scripts/augment_dataset.py [--target 520] [--dry-run]
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

_SEEDS_PATH = Path(__file__).resolve().parent.parent / "data" / "v0" / "seeds.json"
_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "v0" / "dataset.json"
_API_DIR = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "api"

# Load API key from the API's .env
def _load_api_key() -> str:
    env_path = _API_DIR / ".env"
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("LLM_API_KEY="):
            val = line.split("=", 1)[1].strip()
            # Strip surrounding quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            return val
    print("ERROR: LLM_API_KEY not found in apps/api/.env", file=sys.stderr)
    sys.exit(1)


_PARAPHRASE_SYSTEM = """You generate realistic WhatsApp message variants for a tuition center context in Chennai, India.

Given an original message, produce exactly {count} paraphrased variants that:
1. Preserve the EXACT same meaning and commitments (same obligations, same amounts, same people, same deadlines)
2. Vary the tone, phrasing, formality, and structure naturally
3. Use realistic Indian English (mix of formal and casual, "Rs" or "₹", "madam/sir", "pls/plz", typical WhatsApp shorthand)
4. Some should be brief, some longer — mirror real chat variety
5. Do NOT add or remove any commitment, amount, date, or person name
6. For adversarial messages (no commitments), generate messages that are similarly non-committal but varied

Return a JSON array of {count} strings. No other text."""

_PARAPHRASE_TOOL = {
    "name": "return_variants",
    "description": "Return the paraphrased message variants",
    "input_schema": {
        "type": "object",
        "properties": {
            "variants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of paraphrased message variants",
            }
        },
        "required": ["variants"],
    },
}


async def generate_variants(
    client: httpx.AsyncClient,
    model: str,
    message: str,
    has_commitments: bool,
    count: int,
    max_retries: int = 2,
) -> list[str]:
    """Generate paraphrased variants of a message."""
    context = "This message CONTAINS commitments — preserve all obligations exactly." if has_commitments else "This is an adversarial message with NO commitments — keep it non-committal."

    for attempt in range(max_retries + 1):
        try:
            resp = await client.post(
                "/v1/messages",
                json={
                    "model": model,
                    "max_tokens": 2048,
                    "system": _PARAPHRASE_SYSTEM.format(count=count),
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{context}\n\nOriginal message:\n\"{message}\"\n\nGenerate {count} variants.",
                        }
                    ],
                    "tools": [_PARAPHRASE_TOOL],
                    "tool_choice": {"type": "tool", "name": "return_variants"},
                },
                timeout=30.0,
            )

            if resp.status_code != 200:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                print(f"  API error {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                return []

            data = resp.json()
            for block in data.get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "return_variants":
                    variants = block["input"].get("variants", [])
                    return variants[:count]

            return []

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            print(f"  Network error: {e}", file=sys.stderr)
            return []

    return []


async def augment(target: int, dry_run: bool = False) -> None:
    seeds = json.loads(_SEEDS_PATH.read_text())
    cases = seeds["cases"]
    total_seeds = len(cases)

    # Calculate variants needed per seed
    variants_needed = max(0, target - total_seeds)
    # Commitment cases get 4 variants, adversarial get 5 (they're cheaper to validate)
    commitment_cases = [c for c in cases if c["gold_commitments"]]
    adversarial_cases = [c for c in cases if not c["gold_commitments"]]

    # Roughly: 55 commitment * 4 + 45 adversarial * 5 = 220 + 225 = 445 + 100 seeds = 545
    commit_variants = 4
    adv_variants = 5

    estimated = total_seeds + len(commitment_cases) * commit_variants + len(adversarial_cases) * adv_variants
    print(f"Seeds: {total_seeds} ({len(commitment_cases)} commitment, {len(adversarial_cases)} adversarial)")
    print(f"Variants per commitment case: {commit_variants}")
    print(f"Variants per adversarial case: {adv_variants}")
    print(f"Estimated total: {estimated}")

    if dry_run:
        print("Dry run — no API calls made.")
        return

    api_key = _load_api_key()
    client = httpx.AsyncClient(
        base_url="https://api.anthropic.com",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    model = "claude-sonnet-4-6"
    all_cases = list(cases)  # Start with seeds
    variant_id = 1

    # Process in batches of 5 to avoid rate limits
    batch_size = 5
    all_seeds = list(cases)

    for batch_start in range(0, len(all_seeds), batch_size):
        batch = all_seeds[batch_start : batch_start + batch_size]
        tasks = []

        for seed in batch:
            has_commitments = bool(seed["gold_commitments"])
            count = commit_variants if has_commitments else adv_variants
            tasks.append((seed, count, has_commitments))

        # Run batch concurrently
        results = await asyncio.gather(
            *[
                generate_variants(client, model, s["message"], hc, c)
                for s, c, hc in tasks
            ]
        )

        for (seed, count, _), variants in zip(tasks, results):
            for v_msg in variants:
                new_case = {
                    "id": f"aug-{variant_id:04d}",
                    "message": v_msg,
                    "provenance_kind": seed["provenance_kind"],
                    "gold_commitments": seed["gold_commitments"],
                    "tags": seed["tags"] + ["augmented", f"source:{seed['id']}"],
                }
                all_cases.append(new_case)
                variant_id += 1

        done = batch_start + len(batch)
        print(f"  [{done}/{len(all_seeds)}] Generated variants for {len(batch)} seeds, total cases: {len(all_cases)}")

        # Small delay between batches to respect rate limits
        if batch_start + batch_size < len(all_seeds):
            await asyncio.sleep(1)

    await client.aclose()

    # Build final dataset
    dataset = {
        "version": "v0",
        "frozen_at": seeds["frozen_at"],
        "cases": all_cases,
    }

    # Stats
    total = len(all_cases)
    gold = sum(len(c["gold_commitments"]) for c in all_cases)
    adversarial = sum(1 for c in all_cases if not c["gold_commitments"])
    multi_cp = sum(
        1 for c in all_cases
        if any(len(g.get("counterparties", [])) > 1 for g in c["gold_commitments"])
    )

    print(f"\nFinal dataset:")
    print(f"  Total cases: {total}")
    print(f"  Gold commitments: {gold}")
    print(f"  Adversarial: {adversarial} ({adversarial/total:.0%})")
    print(f"  Multi-cp: {multi_cp} ({multi_cp/total:.0%})")
    print(f"  Target met: {'YES' if total >= 500 and gold >= 60 and adversarial/total >= 0.15 and multi_cp/total >= 0.10 else 'NO'}")

    _OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWritten to {_OUTPUT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment eval dataset")
    parser.add_argument("--target", type=int, default=520, help="Target total cases")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without API calls")
    args = parser.parse_args()

    asyncio.run(augment(args.target, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
