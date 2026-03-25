#!/usr/bin/env python
"""
Simpler validation - just check experiment results from magentic-marketplace.
Uses the analytics module to introspect results.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    """Check experiment results."""
    from magentic_marketplace.experiments.run_analytics import run_analytics
    
    experiments = ['mr_contractors_10_30', 'mr_contractors_33_99']
    
    print("🔍 VALIDATING CONTRACTORS EXPERIMENTS")
    print("=" * 70)
    
    for exp_name in experiments:
        print(f"\n📊 {exp_name}")
        print("-" * 70)
        
        try:
            results = await run_analytics(
                exp_name,
                db_type="postgres",
                save_to_json=False,
                print_results=True
            )
            
            print(f"\n✅ Analytics Results:")
            print(results)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
