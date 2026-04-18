"""Add missing columns to Logs table"""
import sys
sys.path.insert(0, '.')
from api.database import get_db_cursor

with get_db_cursor() as cursor:
    # Check current columns
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'Logs' ORDER BY ordinal_position
    """)
    cols = [r['column_name'] for r in cursor.fetchall()]
    print('Current Logs columns:', cols)

    # Add missing columns
    needed = {
        'model_used': 'VARCHAR(255)',
        'tokens_used': 'INTEGER',
        'response_time_ms': 'INTEGER',
        'was_healed': 'BOOLEAN DEFAULT FALSE',
    }
    for col, col_type in needed.items():
        if col not in cols:
            cursor.execute(f'ALTER TABLE "Logs" ADD COLUMN "{col}" {col_type}')
            print(f'  Added: {col}')
        else:
            print(f'  OK: {col}')

    # Verify
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'Logs' ORDER BY ordinal_position
    """)
    print('Final Logs columns:', [r['column_name'] for r in cursor.fetchall()])

print('Done!')
