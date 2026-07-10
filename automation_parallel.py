"""
automation_parallel.py — Parallel pipeline orchestrator
========================================================
All 4 stages run at the same time using threads + queues:

  Stage 1 → knowledge_generator  : runs once, generates graph
  Stage 2 → query_builder        : builds tiers, feeds per-tier search workers
  Stage 3 → serperai             : 5 isolated thread pools (one per tier)
                                   each fires the moment its first query is ready
  Stage 4 → website_validator_v2 : pulls from url_queue, validates immediately
  Stage 5 → result collector     : pulls valid results, builds final list

No stage waits for the previous one to fully finish.
"""

import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from knowledge_generator  import generate_knowledge
from query_builder         import build_queries
from serperai              import search_and_enqueue
from website_validator_v2  import run_validator_worker

SERPER_WORKERS_PER_TIER = 10   # each tier gets its own pool of 10

def run_parallel_pipeline(
    category,
    location,
    search_entity,
    target_count=100,
    progress_callback=None,
    stop_event=None,
):
    scale = max(1, target_count // 10)
    MAX_QUERIES_PER_TIER = {
        "tier1": 15,
        "tier2": min(60, 20 * scale),
        "tier3": min(50, 15 * scale),
        "tier4": min(40, 10 * scale),
        "tier5": 15,
    }
    if stop_event is None:
        stop_event = threading.Event()

    # ── Step 1: Knowledge graph (blocking — must finish before queries) ─────
    print("\n[Pipeline] Generating knowledge graph...")
    if progress_callback:
        progress_callback(
            stage="Building knowledge graph...",
            total_orgs=0,
            organizations=[],
            done=False
        )

    graph = generate_knowledge(category, location)
    query_tiers = build_queries(graph, category, location, search_entity)

    category_signals = list(set(
        graph.get("keywords",      []) +
        graph.get("activities",    []) +
        graph.get("beneficiaries", []) +
        graph.get("synonyms",      [])
    ))

    print(f"[Pipeline] Graph ready. Launching parallel search across {len(query_tiers)} tiers...")

    # ── Shared queues ────────────────────────────────────────────────────────
    url_queue   = queue.Queue()   # Serper → Validator
    valid_queue = queue.Queue()   # Validator → Result collector

    # ── Shared state ─────────────────────────────────────────────────────────
    seen_urls         = set()
    seen_urls_lock    = threading.Lock()
    seen_domains      = set()
    seen_domains_lock = threading.Lock()

    results_list = []
    results_lock = threading.Lock()

    # Events to signal stage completion
    search_done_event    = threading.Event()  # set when ALL tier search pools finish
    validator_done_event = threading.Event()  # set when validator finishes

    # ── Stage 2+3: One thread per tier, each with its own Serper pool ────────
    tier_names = list(query_tiers.keys())
    active_tiers = [len(tier_names)]   # mutable counter

    def run_tier(tier_name):
        queries = query_tiers[tier_name][: MAX_QUERIES_PER_TIER.get(tier_name, 999)]
        print(f"  [{tier_name}] Starting — {len(queries)} queries")

        with ThreadPoolExecutor(max_workers=SERPER_WORKERS_PER_TIER) as pool:
            futures = []
            for q in queries:
                if stop_event.is_set():
                    break
                f = pool.submit(
                    search_and_enqueue,
                    q, category, location,
                    url_queue, seen_urls, seen_urls_lock
                )
                futures.append(f)
                # Small stagger so tier1 gets a head start
                if tier_name == "tier1":
                    time.sleep(0.05)

            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    print(f"  [{tier_name}] Search error: {e}")

        with results_lock:
            active_tiers[0] -= 1
            remaining = active_tiers[0]

        print(f"  [{tier_name}] Done. Tiers still running: {remaining}")

        if remaining == 0:
            search_done_event.set()
            print("[Pipeline] All search tiers finished.")

    tier_threads = [
        threading.Thread(target=run_tier, args=(t,), daemon=True)
        for t in tier_names
    ]

    # ── Stage 4: Validator (runs in its own thread, uses threadpool internally) ─
    def run_validator():
        run_validator_worker(
            url_queue, valid_queue,
            category_signals, location,
            seen_domains, seen_domains_lock,
            stop_event, search_done_event
        )
        validator_done_event.set()
        print("[Pipeline] Validator finished.")

    validator_thread = threading.Thread(target=run_validator, daemon=True)

    # ── Stage 5: Result collector (runs in its own thread) ───────────────────
    def collect_results():
        while True:
            try:
                item = valid_queue.get(timeout=0.3)
            except Exception:
                if validator_done_event.is_set() and valid_queue.empty():
                    break
                if stop_event.is_set():
                    break
                continue

            if stop_event.is_set():
                break

            with results_lock:
                results_list.append(item)
                count = len(results_list)

            print(f"  [Collector] Result #{count}: {item.get('Title','?')[:55]}")

            if count >= target_count:
                stop_event.set()
                break

    collector_thread = threading.Thread(target=collect_results, daemon=True)

    # ── Launch everything simultaneously ──────────────────────────────────────
    t_start = time.time()

    validator_thread.start()   # validator ready before first URL arrives
    collector_thread.start()   # collector ready before first valid result
    collector_thread.join(timeout=30) # wait up to 30s for collector to finish

    for t in tier_threads:
        t.start()              # all 5 tiers start at the same time

    # ── Progress loop ─────────────────────────────────────────────────────────
    while True:
        time.sleep(1)

        with results_lock:
            count = len(results_list)
            orgs  = list(results_list)

        elapsed = round(time.time() - t_start, 1)

        # Build a stage label for the UI
        tiers_left = active_tiers[0]
        if tiers_left > 0:
            stage = f"Searching ({tiers_left} tiers active) — {elapsed}s"
        elif not validator_done_event.is_set():
            stage = f"Validating results — {elapsed}s"
        else:
            stage = f"Collecting — {elapsed}s"

        if progress_callback:
            progress_callback(
                stage=stage,
                total_orgs=count,
                organizations=orgs,
                done=False
            )

        # Stop conditions
        if stop_event.is_set():
            break

        all_threads_done = (
            all(not t.is_alive() for t in tier_threads)
            and not validator_thread.is_alive()
            and not collector_thread.is_alive()
        )
        if all_threads_done:
            break

    # Final results
    with results_lock:
        final = list(results_list)

    elapsed_total = round(time.time() - t_start, 1)
    print(f"\n[Pipeline] Complete in {elapsed_total}s — {len(final)} organizations found.")

    if progress_callback:
        progress_callback(
            stage=f"Done in {elapsed_total}s",
            total_orgs=len(final),
            organizations=final,
            done=True
        )

    return final