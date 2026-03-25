# Copy this entire script
# Open your terminal/command prompt
# Run: python odoo-bin shell -d <your_database_name>
# Then paste this code and hit enter.

print("--- STARTING REGISTRY FIX ---")

# 1. Delete old models from ir_model
env.cr.execute("DELETE FROM ir_model WHERE model IN ('kpt.account.type', 'kpt.account.category')")
print(f"Deleted {env.cr.rowcount} records from ir_model")

# 2. Delete old model data (external IDs)
env.cr.execute("DELETE FROM ir_model_data WHERE model IN ('kpt.account.type', 'kpt.account.category')")
print(f"Deleted {env.cr.rowcount} records from ir_model_data (model refs)")

# 3. Delete leftover module data for the old module name
env.cr.execute("DELETE FROM ir_model_data WHERE module = 'kpt_custom_account_types'")
print(f"Deleted {env.cr.rowcount} records from ir_model_data (module refs)")

# 4. Delete old Views
env.cr.execute("DELETE FROM ir_ui_view WHERE model IN ('kpt.account.type', 'kpt.account.category')")
print(f"Deleted {env.cr.rowcount} records from ir_ui_view")

# 5. Delete old Actions
env.cr.execute("DELETE FROM ir_act_window WHERE res_model IN ('kpt.account.type', 'kpt.account.category')")
print(f"Deleted {env.cr.rowcount} records from ir_act_window")

# 6. Delete old Menus (if any specially linked, though usually linked via action)
# (Optional, cascade usually handles this)

# 7. Delete the old module record from app list so Odoo forgets it was installed
env.cr.execute("DELETE FROM ir_module_module WHERE name = 'kpt_custom_account_types'")
print(f"Deleted {env.cr.rowcount} records from ir_module_module")

# Commit the changes
env.cr.commit()
print("--- FIX COMPLETED. PLEASE RESTART SERVER ---")
