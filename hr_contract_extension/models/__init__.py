from . import hr_contract
from . import tax_slab
from . import tax_slab_help_link
from . import res_company
from . import tax_scheme
from . import salary_increment
from . import other_income
from . import rent_payment
from . import hr_tds
from . import hr_payslip
from . import tds_challan
from . import tds_challan_line
from . import hr_employee
from . import hr_salary_attachment_type
from . import hr_salary_attachment
from . import hr_payslip_attachment
from . import hr_salary_rule
from . import hr_payroll_structure

"""
Disabled import: form_14
Reason:
- The HR Contract view pages for Forms (14/15/23) have been removed.
- The models/form_14.py file is not present, and importing it causes an ImportError during registry load.
Resolution:
- Commented out `from . import form_14` to prevent module loading failure while keeping other functionality intact.
"""
# from . import form_14
