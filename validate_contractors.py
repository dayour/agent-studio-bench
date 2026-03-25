#!/usr/bin/env python
"""Quick validation script to verify contractors data in PostgreSQL."""

import subprocess
import sys

def run_psql_query(query: str) -> str:
    """Run a PostgreSQL query using psql command."""
    cmd = [
        'psql',
        '-h', 'localhost',
        '-U', 'postgres',
        '-d', 'marketplace',
        '-c', query
    ]
    
    env = {'PGPASSWORD': 'postgres'}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env={**subprocess.os.environ, **env})
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


def validate_contractors():
    """Validate contractors experiments data."""
    experiments = ['mr_contractors_10_30', 'mr_contractors_33_99']
    
    print("🔍 VALIDATING CONTRACTORS EXPERIMENT DATA")
    print("=" * 70)
    
    all_valid = True
    
    for exp_name in experiments:
        print(f"\n📊 {exp_name}")
        print("-" * 70)
        
        # Query agents table
        query = f"SELECT COUNT(*) FROM agents WHERE experiment_name = '{exp_name}';"
        result = run_psql_query(query)
        print(f"Agents query result:\n{result}")
        
        # Query actions table
        query = f"SELECT COUNT(*) FROM actions WHERE experiment_name = '{exp_name}';"
        result = run_psql_query(query)
        print(f"Actions query result:\n{result}")
        
        # Query logs table
        query = f"SELECT COUNT(*) FROM logs WHERE experiment_name = '{exp_name}';"
        result = run_psql_query(query)
        print(f"Logs query result:\n{result}")
    
    return all_valid


if __name__ == "__main__":
    validate_contractors()
