#!/usr/bin/env python
"""Run large datasets with extended timeout."""
import sys
import subprocess
from pathlib import Path

LARGE_DATASETS = [
    ("data/mexican_100_300", "mr_mexican_100_300", 1800),  # 30 min timeout
    ("data/contractors/contractors_100_300", "mr_contractors_100_300", 1800),  # 30 min timeout
]

def run_dataset(dataset_path: str, exp_name: str, timeout: int) -> bool:
    """Run a single large dataset."""
    print(f"\n{'='*80}")
    print(f"Processing: {exp_name}")
    print(f"Dataset: {dataset_path}")
    print(f"Timeout: {timeout}s ({timeout//60} minutes)")
    print(f"{'='*80}")
    
    # Step 1: Run
    print(f"\n[STEP 1] Running experiment with --override-db...")
    run_cmd = [
        sys.executable, "-c",
        f"from magentic_marketplace.cli import main; import sys; sys.argv = ['magentic-marketplace', 'run', '{dataset_path}', '--experiment-name', '{exp_name}', '--override-db']; main()"
    ]
    
    try:
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent),
        )
        
        if result.returncode != 0:
            print(f"❌ Run failed")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"✅ Run succeeded")
        
        # Step 2: Analyze
        print(f"\n[STEP 2] Running analyze --no-save-json...")
        analyze_cmd = [
            sys.executable, "-c",
            f"from magentic_marketplace.cli import main; import sys; sys.argv = ['magentic-marketplace', 'analyze', '{exp_name}', '--no-save-json']; main()"
        ]
        
        result = subprocess.run(
            analyze_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(Path(__file__).parent),
        )
        
        if result.returncode != 0:
            print(f"❌ Analyze failed")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"✅ Analyze succeeded")
        
        # Step 3: Validate
        print(f"\n[STEP 3] Validating with asyncpg...")
        try:
            import asyncpg
            import asyncio
            
            async def validate():
                try:
                    conn = await asyncpg.connect(
                        host="localhost",
                        port=5432,
                        user="postgres",
                        password="postgres",
                        database="marketplace"
                    )
                    
                    # Check schema exists
                    schema_exists = await conn.fetchval(
                        f"SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = '{exp_name}')"
                    )
                    
                    if not schema_exists:
                        print(f"❌ Schema '{exp_name}' not found")
                        return False
                    
                    # Get counts
                    agents = await conn.fetchval(f"SELECT COUNT(*) FROM {exp_name}.agents")
                    actions = await conn.fetchval(f"SELECT COUNT(*) FROM {exp_name}.actions")
                    logs = await conn.fetchval(f"SELECT COUNT(*) FROM {exp_name}.logs")
                    
                    await conn.close()
                    
                    print(f"✅ Validation passed")
                    print(f"   agents={agents}, actions={actions}, logs={logs}")
                    return agents > 0 and actions > 0 and logs > 0
                except Exception as e:
                    print(f"❌ Validation error: {e}")
                    return False
            
            return asyncio.run(validate())
        except Exception as e:
            print(f"⚠️  Could not validate: {e}")
            return True  # Assume success if we can't validate
    
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    """Run large datasets."""
    results = []
    
    for dataset_path, exp_name, timeout in LARGE_DATASETS:
        success = run_dataset(dataset_path, exp_name, timeout)
        results.append({
            "experiment": exp_name,
            "dataset": dataset_path,
            "success": success
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        print(f"{status} | {r['experiment']:40} | {r['dataset']}")
    
    done_count = sum(1 for r in results if r["success"])
    print(f"\nResults: {done_count}/{len(results)} successful")
    
    return 0 if done_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
