#!/usr/bin/env python
"""Direct database validation using sqlalchemy or direct connection."""

import os
import sys

try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    print("sqlalchemy not available, using psycopg2...")
    try:
        import psycopg2
        HAS_PSYCOPG2 = True
    except ImportError:
        HAS_PSYCOPG2 = False


def validate_with_sqlalchemy():
    """Validate using SQLAlchemy."""
    try:
        # Create engine
        engine = create_engine(
            'postgresql://postgres:postgres@localhost:5432/marketplace'
        )
        
        with engine.connect() as conn:
            # Get list of tables
            inspector = sa.inspect(engine)
            tables = inspector.get_table_names()
            print(f"📋 Available tables: {tables}\n")
            
            # Check our tables
            for table in ['agents', 'actions', 'logs']:
                if table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"✓ {table}: {count} rows")
                else:
                    print(f"✗ {table}: table not found")
            
            # Try to find experiment-specific data
            for exp in ['mr_contractors_10_30', 'mr_contractors_33_99']:
                print(f"\n🔎 {exp}:")
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as cnt FROM agents WHERE experiment_name = '{exp}'")
                    )
                    count = result.fetchone()[0]
                    print(f"   Agents: {count}")
                except Exception as e:
                    print(f"   Agents: error ({e})")
                    
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as cnt FROM actions WHERE experiment_name = '{exp}'")
                    )
                    count = result.fetchone()[0]
                    print(f"   Actions: {count}")
                except Exception as e:
                    print(f"   Actions: error ({e})")
                    
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as cnt FROM logs WHERE experiment_name = '{exp}'")
                    )
                    count = result.fetchone()[0]
                    print(f"   Logs: {count}")
                except Exception as e:
                    print(f"   Logs: error ({e})")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def validate_with_psycopg2():
    """Validate using psycopg2."""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            database="marketplace",
            user="postgres",
            password="postgres",
            host="localhost",
            port=5432
        )
        
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Available tables: {tables}\n")
        
        # Check counts
        for table in ['agents', 'actions', 'logs']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✓ {table}: {count} rows")
        
        # Check experiment data
        for exp in ['mr_contractors_10_30', 'mr_contractors_33_99']:
            print(f"\n🔎 {exp}:")
            try:
                cursor.execute(f"SELECT COUNT(*) FROM agents WHERE experiment_name = %s", (exp,))
                count = cursor.fetchone()[0]
                print(f"   Agents: {count}")
            except Exception as e:
                print(f"   Agents: error ({e})")
            
            try:
                cursor.execute(f"SELECT COUNT(*) FROM actions WHERE experiment_name = %s", (exp,))
                count = cursor.fetchone()[0]
                print(f"   Actions: {count}")
            except Exception as e:
                print(f"   Actions: error ({e})")
            
            try:
                cursor.execute(f"SELECT COUNT(*) FROM logs WHERE experiment_name = %s", (exp,))
                count = cursor.fetchone()[0]
                print(f"   Logs: {count}")
            except Exception as e:
                print(f"   Logs: error ({e})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 VALIDATING CONTRACTORS EXPERIMENT DATA\n")
    print("=" * 70)
    
    if HAS_SQLALCHEMY:
        print("Using SQLAlchemy...\n")
        validate_with_sqlalchemy()
    elif HAS_PSYCOPG2:
        print("Using psycopg2...\n")
        validate_with_psycopg2()
    else:
        print("❌ No database libraries available")
        sys.exit(1)
