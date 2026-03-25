#!/usr/bin/env python3
"""Check row counts in database schemas."""

import sys
import sqlalchemy as sa
from dotenv import load_dotenv
import os

load_dotenv()

def check_schema(schema_name):
    """Check row counts for a schema."""
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"
    engine = sa.create_engine(db_url)

    try:
        with engine.connect() as conn:
            agents = conn.execute(sa.text(f"SELECT COUNT(*) FROM {schema_name}.agents;")).scalar()
            actions = conn.execute(sa.text(f"SELECT COUNT(*) FROM {schema_name}.actions;")).scalar()
            logs = conn.execute(sa.text(f"SELECT COUNT(*) FROM {schema_name}.logs;")).scalar()
            
            all_valid = agents > 0 and actions > 0 and logs > 0
            
            return {
                'agents': agents,
                'actions': actions,
                'logs': logs,
                'valid': all_valid
            }
    except Exception as e:
        print(f"Error checking {schema_name}: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_row_counts.py <schema_name>")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    result = check_schema(schema_name)
    
    if result:
        print(f"agents: {result['agents']}")
        print(f"actions: {result['actions']}")
        print(f"logs: {result['logs']}")
        print(f"valid: {result['valid']}")
        sys.exit(0 if result['valid'] else 1)
    else:
        sys.exit(1)
