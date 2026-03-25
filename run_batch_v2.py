#!/usr/bin/env python
"""Batch runner for datasets."""
import sys
import subprocess
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Datasets to process (using correct paths from DATASET_INVENTORY)
DATASETS = [
    ("data/malicious_description/mexican_control", "mr_mal_mexican_control", "1"),
    ("data/malicious_description/mexican_authority", "mr_mal_mexican_authority", "2"),
    ("data/malicious_description/mexican_loss_aversion", "mr_mal_mexican_loss_aversion", "3"),
    ("data/malicious_description/mexican_prompt_injection_basic", "mr_mal_mexican_prompt_inj_basic", "4"),
    ("data/malicious_description/contractors_control", "mr_mal_contractors_control", "5"),
    ("data/malicious_description/contractors_authority", "mr_mal_contractors_authority", "6"),
    ("data/malicious_description/contractors_loss_aversion", "mr_mal_contractors_loss_aversion", "7"),
    ("data/mexican_100_300", "mr_mexican_100_300", "8"),
    ("data/contractors/contractors_100_300", "mr_contractors_100_300", "9"),
]

def run_command(cmd: list, exp_name: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"[{exp_name}] Running experiment...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout for large datasets
            cwd=str(Path(__file__).parent),
        )
        
        # Combine stdout and stderr
        output = result.stdout + "\n" + result.stderr
        
        # Check for success
        success = result.returncode == 0
        
        return success, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after 600 seconds"
    except Exception as e:
        return False, f"Error: {str(e)}"


def validate_experiment(exp_name: str) -> tuple[bool, Optional[int], Optional[int], Optional[int], str]:
    """Validate experiment results by checking row counts in PostgreSQL."""
    # Try to connect to PostgreSQL and check the schema
    try:
        import asyncpg
        import asyncio
        
        async def check_database():
            try:
                # Connect to PostgreSQL
                conn = await asyncpg.connect(
                    host="localhost",
                    port=5432,
                    user="postgres",
                    password="postgres",
                    database="marketplace"
                )
                
                try:
                    # Check if schema exists and has tables
                    schema_check = await conn.fetchval(
                        f"SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = '{exp_name}')"
                    )
                    
                    if not schema_check:
                        return False, None, None, None, f"Schema '{exp_name}' not found in PostgreSQL"
                    
                    # Get row counts for required tables
                    tables = {"agents", "actions", "logs"}
                    counts = {}
                    
                    for table in tables:
                        try:
                            count = await conn.fetchval(
                                f"SELECT COUNT(*) FROM {exp_name}.{table}"
                            )
                            counts[table] = count if count else 0
                        except Exception as e:
                            return False, None, None, None, f"Error querying table '{table}': {str(e)}"
                    
                    agents_count = counts.get("agents", 0)
                    actions_count = counts.get("actions", 0)
                    logs_count = counts.get("logs", 0)
                    
                    if agents_count > 0 and actions_count > 0 and logs_count > 0:
                        return True, agents_count, actions_count, logs_count, "All tables have non-zero rows"
                    else:
                        return False, agents_count, actions_count, logs_count, f"Some tables are empty: agents={agents_count}, actions={actions_count}, logs={logs_count}"
                finally:
                    await conn.close()
            except Exception as e:
                return False, None, None, None, f"Connection error: {str(e)}"
        
        success, agents, actions, logs, msg = asyncio.run(check_database())
        return success, agents, actions, logs, msg
        
    except ImportError:
        return False, None, None, None, "asyncpg not available - cannot validate database"
    except Exception as e:
        return False, None, None, None, f"Error validating: {str(e)}"


def main():
    """Process all datasets."""
    print("=" * 80)
    print("BATCH DATASET RUNNER: malicious_description + large datasets")
    print("=" * 80)
    
    results = []
    
    for dataset_path, exp_name, dataset_id in DATASETS:
        print(f"\n{'='*80}")
        print(f"[{dataset_id}] Processing: {exp_name}")
        print(f"Dataset: {dataset_path}")
        print(f"{'='*80}")
        
        result = {
            "id": dataset_id,
            "dataset_path": dataset_path,
            "experiment_name": exp_name,
            "status": "failed",
            "run_status": "pending",
            "analyze_status": "pending",
            "agents_count": None,
            "actions_count": None,
            "logs_count": None,
            "notes": "",
        }
        
        try:
            # Step 1: Run experiment
            print(f"\n[STEP 1] Running experiment with --override-db...")
            run_cmd = [
                sys.executable, "-c",
                f"from magentic_marketplace.cli import main; import sys; sys.argv = ['magentic-marketplace', 'run', '{dataset_path}', '--experiment-name', '{exp_name}', '--override-db']; main()"
            ]
            run_success, run_output = run_command(run_cmd, exp_name)
            result["run_status"] = "success" if run_success else "failed"
            
            if not run_success:
                result["notes"] = f"Run failed: {run_output[-500:]}"
                print(f"❌ Run failed")
                print(run_output[-500:] if len(run_output) > 500 else run_output)
                results.append(result)
                continue
            
            print(f"✅ Run succeeded")
            
            # Step 2: Run analyze
            print(f"\n[STEP 2] Running analyze --no-save-json...")
            analyze_cmd = [
                sys.executable, "-c",
                f"from magentic_marketplace.cli import main; import sys; sys.argv = ['magentic-marketplace', 'analyze', '{exp_name}', '--no-save-json']; main()"
            ]
            analyze_success, analyze_output = run_command(analyze_cmd, exp_name)
            result["analyze_status"] = "success" if analyze_success else "failed"
            
            if not analyze_success:
                result["notes"] = f"Analyze failed: {analyze_output[-500:]}"
                print(f"❌ Analyze failed")
                print(analyze_output[-500:] if len(analyze_output) > 500 else analyze_output)
                results.append(result)
                continue
            
            print(f"✅ Analyze succeeded")
            
            # Step 3: Validate row counts
            print(f"\n[STEP 3] Validating row counts...")
            valid, agents_count, actions_count, logs_count, val_msg = validate_experiment(exp_name)
            
            result["agents_count"] = agents_count
            result["actions_count"] = actions_count
            result["logs_count"] = logs_count
            result["notes"] = val_msg
            
            if valid:
                result["status"] = "done"
                print(f"✅ Validation passed")
                print(f"   agents={agents_count}, actions={actions_count}, logs={logs_count}")
            else:
                result["status"] = "failed"
                print(f"❌ Validation failed")
                print(f"   {val_msg}")
            
        except Exception as e:
            result["status"] = "failed"
            result["notes"] = f"Exception: {str(e)}"
            print(f"❌ Exception: {str(e)}")
        
        results.append(result)
    
    # Print final summary
    print(f"\n{'='*80}")
    print("BATCH SUMMARY")
    print(f"{'='*80}")
    
    done_count = sum(1 for r in results if r["status"] == "done")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    
    print(f"\nResults: {done_count} done, {failed_count} failed out of {len(results)} total\n")
    
    for r in results:
        status_icon = "✅" if r["status"] == "done" else "❌"
        print(f"{status_icon} {r['id']:2} | {r['experiment_name']:40} | agents={r['agents_count']} actions={r['actions_count']} logs={r['logs_count']}")
    
    # Save results to JSON for inspection
    results_file = Path(__file__).parent / "batch_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
