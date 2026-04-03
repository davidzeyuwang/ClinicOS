#!/usr/bin/env python3
"""
Seed production with stable rooms, staff, and service types for smoke testing.

Usage:
    python3 scripts/seed_prod.py            # create missing rooms/staff/service_types
    python3 scripts/seed_prod.py --reset    # clear ALL data first, then seed
    python3 scripts/seed_prod.py --status   # show current counts only
"""
import asyncio
import sys
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────

APP_URL = "https://clinicos-psi.vercel.app"

ROOMS = [
    {"name": "Clinic Room 1", "code": "C1", "floor": "1F", "room_type": "treatment"},
    {"name": "Clinic Room 2", "code": "C2", "floor": "1F", "room_type": "treatment"},
    {"name": "Clinic Room 3", "code": "C3", "floor": "2F", "room_type": "treatment"},
]

STAFF = [
    {"name": "Dr. Smith",   "role": "therapist"},
    {"name": "Dr. Johnson", "role": "therapist"},
    {"name": "Dr. Chen",    "role": "therapist"},
]

DEFAULT_SERVICE_TYPES = [
    "PT", "OT", "Eval", "Re-eval", "Acupuncture", "Cupping",
    "Massage", "E-stim", "Speech", "Heat Therapy", "Cold Therapy",
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_env() -> dict:
    envfile = Path(__file__).parent.parent / ".env.prod"
    env: dict = {}
    for line in envfile.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def supa_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "return=minimal",
    }


async def supa_count(c: httpx.AsyncClient, url: str, key: str, table: str) -> int:
    r = await c.get(
        f"{url}/rest/v1/{table}",
        headers={**supa_headers(key), "Prefer": "count=exact"},
        params={"select": "count", "limit": "0"},
        timeout=10,
    )
    return int(r.headers.get("content-range", "0/0").split("/")[-1])


async def supa_delete_all(c: httpx.AsyncClient, url: str, key: str, table: str, pk: str):
    r = await c.delete(
        f"{url}/rest/v1/{table}",
        headers=supa_headers(key),
        params={pk: "not.is.null"},
        timeout=30,
    )
    return r.status_code


# ── Main ────────────────────────────────────────────────────────────────────

async def main(reset: bool = False, status_only: bool = False):
    env = load_env()
    supa_url = env["SUPABASE_URL"]
    supa_key = env["SUPABASE_SERVICE_KEY"]
    hdrs_supa = {
        "apikey": supa_key,
        "Authorization": f"Bearer {supa_key}",
    }
    hdrs_app = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=20) as c:

        # ── Status only ─────────────────────────────────────────────────────
        if status_only:
            print("Production DB status:")
            for table, pk in [
                ("rooms", "room_id"), ("staff", "staff_id"),
                ("service_types", "service_type_id"), ("staff_service_types", "staff_id"),
                ("patients", "patient_id"), ("visits", "visit_id"),
                ("visit_treatments", "treatment_id"), ("event_log", "event_id"),
            ]:
                n = await supa_count(c, supa_url, supa_key, table)
                print(f"  {table:25s}: {n}")
            return

        # ── Reset ───────────────────────────────────────────────────────────
        if reset:
            print("Resetting all production data...")
            for table, pk in [
                ("event_log",          "event_id"),
                ("visit_treatments",   "treatment_id"),
                ("appointments",       "appointment_id"),
                ("visits",             "visit_id"),
                ("insurance_policies", "policy_id"),
                ("patients",           "patient_id"),
                ("staff",              "staff_id"),
                ("rooms",              "room_id"),
            ]:
                code = await supa_delete_all(c, supa_url, supa_key, table, pk)
                print(f"  Cleared {table}: HTTP {code}")
            print()

        # ── Seed rooms ──────────────────────────────────────────────────────
        r = await c.get(
            f"{supa_url}/rest/v1/rooms",
            headers=hdrs_supa,
            params={"select": "code"},
            timeout=10,
        )
        existing_codes = {x["code"] for x in r.json()}

        print("Seeding rooms:")
        for room in ROOMS:
            if room["code"] in existing_codes:
                print(f"  SKIP   {room['name']} ({room['code']}) — already exists")
            else:
                r = await c.post(
                    f"{APP_URL}/prototype/admin/rooms",
                    headers=hdrs_app,
                    json=room,
                )
                if r.status_code < 300:
                    print(f"  CREATE {room['name']} ({room['code']})")
                else:
                    print(f"  ERROR  {room['name']}: {r.status_code} — {r.text[:80]}")

        # ── Seed staff ──────────────────────────────────────────────────────
        r = await c.get(
            f"{supa_url}/rest/v1/staff",
            headers=hdrs_supa,
            params={"select": "name"},
            timeout=10,
        )
        existing_names = {x["name"] for x in r.json()}

        print("\nSeeding staff:")
        for person in STAFF:
            if person["name"] in existing_names:
                print(f"  SKIP   {person['name']} — already exists")
            else:
                r = await c.post(
                    f"{APP_URL}/prototype/admin/staff",
                    headers=hdrs_app,
                    json=person,
                )
                if r.status_code < 300:
                    print(f"  CREATE {person['name']}")
                else:
                    print(f"  ERROR  {person['name']}: {r.status_code} — {r.text[:80]}")

        # ── Seed service types ───────────────────────────────────────────────
        r = await c.get(
            f"{supa_url}/rest/v1/service_types",
            headers=hdrs_supa,
            params={"select": "name"},
            timeout=10,
        )
        existing_svc_names = {x["name"] for x in r.json()} if r.status_code == 200 else set()

        print("\nSeeding service types:")
        if existing_svc_names:
            print(f"  SKIP   all — {len(existing_svc_names)} service types already exist")
        else:
            for svc_name in DEFAULT_SERVICE_TYPES:
                r = await c.post(
                    f"{APP_URL}/prototype/admin/service-types",
                    headers=hdrs_app,
                    json={"name": svc_name},
                )
                if r.status_code < 300:
                    print(f"  CREATE {svc_name}")
                else:
                    print(f"  ERROR  {svc_name}: {r.status_code} — {r.text[:80]}")

        # ── Summary ─────────────────────────────────────────────────────────
        n_rooms = await supa_count(c, supa_url, supa_key, "rooms")
        n_staff = await supa_count(c, supa_url, supa_key, "staff")
        n_svc   = await supa_count(c, supa_url, supa_key, "service_types")
        print(f"\nDone. Production: {n_rooms} rooms, {n_staff} staff, {n_svc} service types.")
        print(f"Smoke test room code: C1  (run: npx playwright test --config=playwright.smoke.config.ts)")


if __name__ == "__main__":
    asyncio.run(main(
        reset="--reset" in sys.argv,
        status_only="--status" in sys.argv,
    ))
