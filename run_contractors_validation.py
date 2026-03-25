#!/usr/bin/env python
"""Run and validate contractors sample datasets with model-router configuration."""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Now import magentic-marketplace components
from magentic_marketplace.experiments.run_analytics import run_analytics
from magentic_marketplace.experiments.run_experiment import run_marketplace_experiment

# Import for database access
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def get_db_connection():
    """Create PostgreSQL connection."""
    if not HAS_PSYCOPG2:
        return None
    
    try:
        conn = psycopg2.connect(
            database="marketplace",
            user="postgres",
            password="postgres",
            host="localhost",
            port=5432
        )
        return conn
    except Exception as e:
        print(f"  ⚠️  PostgreSQL connection failed: {e}")
        return None


def get_table_row_counts(experiment_name: str) -> dict:
    """Get row counts for tables related to experiment."""
    results = {}
    conn = get_db_connection()
    if not conn:
        print(f"  ⚠️  Cannot query database - no connection")
        return {"agents": None, "actions": None, "logs": None}
    
    try:
        cursor = conn.cursor()
        # Try different queries to find the data
        for table in ["agents", "actions", "logs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results[table] = count
                print(f"    ✓ {table}: {count} rows")
            except Exception as e:
                # Try with experiment filter
                try:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE experiment_name = %s",
                        (experiment_name,)
                    )
                    count = cursor.fetchone()[0]
                    results[table] = count
                    print(f"    ✓ {table} (filtered): {count} rows")
                except Exception as e2:
                    print(f"    ⚠️  {table}: unable to query ({e2})")
                    results[table] = None
        
        cursor.close()
    finally:
        conn.close()
    
    return results


async def run_single_dataset(experiment_name: str, data_dir: str) -> dict:
    """Run a single dataset through the full pipeline."""
    print(f"\n{'='*70}")
    print(f"PROCESSING: {experiment_name}")
    print(f"{'='*70}")
    print(f"📁 Data: {data_dir}")
    
    result = {
        "experiment": experiment_name,
        "status": "pending",
        "steps": {},
    }
    
    # Step 1: Run experiment
    print(f"\n1️⃣  Running experiment with --override-db...")
    try:
        await run_marketplace_experiment(
            data_dir=data_dir,
            experiment_name=experiment_name,
            customer_max_steps=100,
            override=True,  # --override-db equivalent
        )
        result["steps"]["experiment"] = "success"
        print(f"   ✅ Experiment completed")
    except Exception as e:
        result["steps"]["experiment"] = f"failed: {str(e)[:100]}"
        print(f"   ❌ Experiment failed: {e}")
        result["status"] = "failed"
        return result
    
    # Step 2: Run analytics
    print(f"\n2️⃣  Running magentic-marketplace analyze...")
    try:
        results = await run_analytics(
            experiment_name,
            db_type="postgres",
            save_to_json=False,
            print_results=False
        )
        result["steps"]["analytics"] = "success"
        print(f"   ✅ Analytics completed")
    except Exception as e:
        result["steps"]["analytics"] = f"failed: {str(e)[:100]}"
        print(f"   ⚠️  Analytics failed: {e}")
        # Don't fail - continue to validation
    
    # Step 3: Validate data in database
    print(f"\n3️⃣  Validating data in PostgreSQL...")
    counts = get_table_row_counts(experiment_name)
    
    # Check if all are non-zero
    all_valid = all(c and c > 0 for c in counts.values())
    
    result["counts"] = counts
    
    if all_valid:
        result["status"] = "done"
        print(f"   ✅ All validations passed")
    else:
        zeros = {k: v for k, v in counts.items() if v is None or v == 0}
        result["status"] = "failed"
        print(f"   ⚠️  Some tables empty/missing: {zeros}")
    
    return result


async def run_contractors_validation():
    """Run full validation pipeline for contractors datasets."""
    print("🚀 CONTRACTORS SAMPLE DATASET VALIDATION")
    print("=" * 70)
    print("Configuration: model-router via Azure AI Foundry")
    print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
    print(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")
    print("=" * 70)
    
    datasets = [
        {
            "experiment_name": "mr_contractors_10_30",
            "data_dir": "data/contractors/contractors_10_30",
        },
        {
            "experiment_name": "mr_contractors_33_99",
            "data_dir": "data/contractors/contractors_33_99",
        },
    ]
    
    all_results = []
    
    for dataset in datasets:
        result = await run_single_dataset(
            dataset["experiment_name"],
            dataset["data_dir"]
        )
        all_results.append(result)
    
    # Print summary
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    all_done = True
    for result in all_results:
        status_icon = "✅" if result["status"] == "done" else "⚠️ " if result["status"] == "pending" else "❌"
        print(f"\n{status_icon} {result['experiment']}: {result['status'].upper()}")
        for step, status in result['steps'].items():
            step_icon = "✓" if status == "success" else "✗"
            print(f"   {step_icon} {step}: {status}")
        if result['counts']:
            for table, count in result['counts'].items():
                if count is not None:
                    count_str = f"{count} rows"
                    icon = "✓" if count > 0 else "✗"
                    print(f"   {icon} {table}: {count_str}")
                else:
                    print(f"   ? {table}: unable to query")
        
        if result['status'] != "done":
            all_done = False
    
    print(f"\n{'='*70}")
    if all_done:
        print("✅ ALL DATASETS VALIDATED SUCCESSFULLY")
        return True
    else:
        print("⚠️  SOME DATASETS INCOMPLETE - REVIEW ABOVE")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_contractors_validation())
    sys.exit(0 if success else 1)
