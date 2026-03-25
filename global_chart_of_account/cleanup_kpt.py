from odoo import api, SUPERUSER_ID

def cleanup_kpt_models(env):
    """
    Remove old KPT models from ir.model to fix registry KeyErrors.
    """
    # Models to remove
    models_to_remove = ['kpt.account.type', 'kpt.account.category']
    
    # 1. Remove ir.model records
    ir_models = env['ir.model'].search([('model', 'in', models_to_remove)])
    if ir_models:
        print(f"Removing {len(ir_models)} ir.model records: {ir_models.mapped('model')}")
        ir_models.unlink()
        
    # 2. Remove ir.model.data (External IDs) if any
    ir_data = env['ir.model.data'].search([('model', 'in', models_to_remove)])
    if ir_data:
        print(f"Removing {len(ir_data)} ir.model.data records for old models")
        ir_data.unlink()

# This script is intended to be run via shell or pre-init hook if possible,
# but since valid module install is blocked, user might need to run this in shell.
