# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Add invoice_cash_rounding_id to sale_order to use Odoo's built-in cash rounding"""
    
    # Add invoice_cash_rounding_id to sale_order if it doesn't exist
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='sale_order' 
        AND column_name='invoice_cash_rounding_id'
    """)
    
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE sale_order 
            ADD COLUMN invoice_cash_rounding_id INTEGER
        """)
        
        cr.execute("""
            ALTER TABLE sale_order 
            ADD CONSTRAINT sale_order_invoice_cash_rounding_id_fkey 
            FOREIGN KEY (invoice_cash_rounding_id) 
            REFERENCES account_cash_rounding(id) 
            ON DELETE SET NULL
        """)
    
    # Clean up old custom columns if they exist
    columns_to_remove = [
        ('res_company', 'round_off_account_id'),
        ('sale_order', 'round_off_amount'),
        ('sale_order', 'amount_total_rounded'),
        ('account_move', 'round_off_amount'),
        ('account_move', 'round_off_account_id'),
        ('account_move', 'amount_total_rounded'),
    ]
    
    for table, column in columns_to_remove:
        cr.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table}' 
            AND column_name='{column}'
        """)
        
        if cr.fetchone():
            cr.execute(f"""
                ALTER TABLE {table} DROP COLUMN IF EXISTS {column} CASCADE
            """)
