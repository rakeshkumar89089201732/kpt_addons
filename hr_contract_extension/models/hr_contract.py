from setuptools.unicode_utils import filesys_decode
from collections import defaultdict

from typing_extensions import deprecated

from odoo import _, models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError
import itertools
import math


class HrContractNewWizard(models.TransientModel):
    _name = 'hr.contract.new.wizard'
    _description = 'New Contract Wizard'

    current_contract_id = fields.Many2one('hr.contract', string='Current Contract', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='current_contract_id.employee_id', readonly=True)
    previous_contract_end_date = fields.Date(string='Previous Contract End Date', required=True)
    new_contract_start_date = fields.Date(string='New Contract Start Date', required=True, default=fields.Date.context_today)

    def action_confirm(self):
        self.ensure_one()
        current = self.current_contract_id
        if not current:
            raise UserError(_('No current contract found.'))

        prev_end = self.previous_contract_end_date
        new_start = self.new_contract_start_date
        if not prev_end or not new_start:
            raise UserError(_('Please set both Previous Contract End Date and New Contract Start Date.'))
        if prev_end >= new_start:
            raise UserError(_('Previous Contract End Date must be before New Contract Start Date.'))

        # Close current running contract
        current.write({
            'state': 'close',
            'date_end': prev_end,
        })

        # Create new draft contract copied from current
        new_contract = current.copy({
            'date_start': new_start,
            'date_end': False,
            'state': 'draft',
            'name': current._generate_contract_reference_from_employee(current.employee_id),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }

class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    tds_history_ids = fields.One2many('tds.history', 'hr_contract_id')
    tds_details_ids = fields.One2many('hr.tds', 'hr_contract_id', string='TDS Details')
    tds_count = fields.Integer('TDS Records', compute='_compute_tds_count')
    form14_count = fields.Integer('Form 14', compute='_compute_form14_count')
    tax_regime_slab = fields.Many2one('tax.slab', string='Tax Regime', help='Default tax regime for this contract')
    apply_pf = fields.Boolean('Apply Provident Fund')
    apply_esic = fields.Boolean('Apply ESIC')
    deduct_employee_pf_in_net_pay = fields.Boolean('Deduct Employee Share in Net Pay', default=True)
    deduct_employer_pf_in_net_pay = fields.Boolean('Deduct Employer Share in Net Pay')
    pf_admin_percent = fields.Float('Administrative Expense (%)', default=1.0)
    
    house_rent_allowance = fields.Float('HRA')
    conveyance_allowance = fields.Float('Conveyance Allowance')
    medical_allowance = fields.Float('Medical Allowance')
    vehicle_allowance = fields.Float('Vehicle Allowance')
    washing_allowance = fields.Float('Washing Allowance')
    other_allowance = fields.Float('Other Allowance')
    tour_expenses = fields.Float('Tour Expenses')
    gross = fields.Float('GROSS', compute='_compute_contract_amounts', readonly=True)
    current_ctc = fields.Float('Current CTC', compute='_compute_current_ctc', store=True, readonly=True)
    professional_tax = fields.Float('Professional Tax')
    employee_provident_fund = fields.Float('Employee Share', compute='_compute_contract_amounts', readonly=True)
    # Backward-compatible total employer PF (historically 13%)
    contributory_provident_fund = fields.Float('Employer Total PF', compute='_compute_contract_amounts', readonly=True)
    employer_pf_total = fields.Float('Employer Total PF (13%)', compute='_compute_contract_amounts', readonly=True)
    employer_pf_share = fields.Float('Employer Share', compute='_compute_contract_amounts', readonly=True)
    pf_admin_expense = fields.Float('Administrative Expense', compute='_compute_contract_amounts', readonly=True)
    employee_esic = fields.Float('Employee ESIC', compute='_compute_contract_amounts', readonly=True)
    employer_esic = fields.Float('Employer ESIC', compute='_compute_contract_amounts', readonly=True)
    life_insurance_corporation = fields.Float('Life Insurance Corporation')
    postal_life_insurance = fields.Float('Postal Life Insurance')
    group_insurance = fields.Float('Group Insurance')
    credit_society = fields.Float('Credit Society')
    tds = fields.Float('TDS')
    net_pay = fields.Float('Net Pay', compute='_compute_contract_amounts', readonly=True)
    effective_fy_salary = fields.Float('Effective Salary (FY)', compute='_compute_effective_fy_salary', readonly=True, digits=(16, 0))

    form_nominee_name = fields.Char('Nominee Name')
    form_nominee_relation = fields.Char('Nominee Relation')
    form_nominee_dob = fields.Date('Nominee Date of Birth')
    form_nominee_address = fields.Text('Nominee Address')

    form14_place = fields.Char('Form 14 Place')
    form14_date = fields.Date('Form 14 Date')
    form15_place = fields.Char('Form 15 Place')
    form15_date = fields.Date('Form 15 Date')
    form23_place = fields.Char('Form 23 Place')
    form23_date = fields.Date('Form 23 Date')

    @api.depends(
        'apply_pf',
        'apply_esic',
        'deduct_employee_pf_in_net_pay',
        'deduct_employer_pf_in_net_pay',
        'pf_admin_percent',
        'wage',
        'house_rent_allowance',
        'conveyance_allowance',
        'medical_allowance',
        'vehicle_allowance',
        'washing_allowance',
        'other_allowance',
        'tour_expenses',
        'tds',
        'professional_tax',
        'life_insurance_corporation',
        'postal_life_insurance',
        'group_insurance',
        'credit_society',
    )
    def _compute_contract_amounts(self):
        for contract in self:
            wage = contract.wage or 0.0
            gross = (
                wage
                + (contract.house_rent_allowance or 0.0)
                + (contract.conveyance_allowance or 0.0)
                + (contract.medical_allowance or 0.0)
                + (contract.vehicle_allowance or 0.0)
                + (contract.washing_allowance or 0.0)
                + (contract.other_allowance or 0.0)
                + (contract.tour_expenses or 0.0)
            )

            employee_pf = float(math.ceil((wage * 0.12))) if contract.apply_pf else 0.0
            employer_pf_total = float(math.ceil((wage * 0.13))) if contract.apply_pf else 0.0

            # Split employer PF total (13%) into:
            # - Employer Share (default 12%)
            # - Administrative Expense (default 1%)
            # If admin % is set to 0, the 1% automatically moves to employer share.
            admin_percent = float(contract.pf_admin_percent or 0.0) if contract.apply_pf else 0.0
            admin_percent = max(min(admin_percent, 13.0), 0.0)
            admin_amt = float(math.ceil(wage * (admin_percent / 100.0))) if (contract.apply_pf and admin_percent) else 0.0
            admin_amt = min(admin_amt, employer_pf_total)
            employer_share_amt = employer_pf_total - admin_amt

            employee_esic = float(math.ceil((gross * 0.0075))) if contract.apply_esic else 0.0
            employer_esic = float(math.ceil((gross * 0.0325))) if contract.apply_esic else 0.0

            employee_pf_deduction = employee_pf if (contract.apply_pf and contract.deduct_employee_pf_in_net_pay) else 0.0
            # Deduct employer PF share from net pay only if checkbox is checked
            employer_pf_deduction = employer_share_amt if (contract.apply_pf and contract.deduct_employer_pf_in_net_pay) else 0.0

            contract.gross = gross
            contract.employee_provident_fund = employee_pf
            contract.employer_pf_total = employer_pf_total
            contract.contributory_provident_fund = employer_pf_total
            contract.employer_pf_share = employer_share_amt
            contract.pf_admin_expense = admin_amt
            contract.employee_esic = employee_esic
            contract.employer_esic = employer_esic

            contract.net_pay = gross - (
                (contract.tds or 0.0)
                + (contract.professional_tax or 0.0)
                + employee_pf_deduction
                + employer_pf_deduction
                + employee_esic
                + (contract.life_insurance_corporation or 0.0)
                + (contract.postal_life_insurance or 0.0)
                + (contract.group_insurance or 0.0)
                + (contract.credit_society or 0.0)
            )

    @api.depends('gross')
    def _compute_current_ctc(self):
        for contract in self:
            contract.current_ctc = (contract.gross or 0.0) * 12

    @api.onchange(
        'apply_pf',
        'apply_esic',
        'deduct_employee_pf_in_net_pay',
        'deduct_employer_pf_in_net_pay',
        'pf_admin_percent',
        'wage',
        'house_rent_allowance',
        'conveyance_allowance',
        'medical_allowance',
        'vehicle_allowance',
        'washing_allowance',
        'other_allowance',
        'tour_expenses',
        'tds',
        'professional_tax',
        'life_insurance_corporation',
        'postal_life_insurance',
        'group_insurance',
        'credit_society',
    )
    def _onchange_contract_amounts(self):
        self._compute_contract_amounts()

    @api.depends('tds_details_ids')
    def _compute_tds_count(self):
        for contract in self:
            contract.tds_count = len(contract.tds_details_ids)

    def _compute_form14_count(self):
        """Compatibility placeholder for removed Form 14 model.

        Original implementation counted related hr.contract.form14 records.
        Form 14 pages/models were removed as per business requirement, so this
        field now always returns 0 to keep existing views and buttons loading
        without error.
        """
        for contract in self:
            contract.form14_count = 0

    def action_open_tds(self):
        """Open TDS records for this contract"""
        self.ensure_one()

        return {
            'name': 'TDS Records',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.tds',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('hr_contract_id', '=', self.id)],
            'context': {
                **self.env.context,
                'default_hr_employee_id': self.employee_id.id,
                'default_hr_contract_id': self.id,
                'default_tax_regime_slab': self.tax_regime_slab.id if self.tax_regime_slab else False,
            },
        }

    def action_print_form14(self):
        self.ensure_one()
        return self.env.ref('hr_contract_extension.action_report_contract_form14').report_action(self)

    def action_print_form15(self):
        self.ensure_one()
        return self.env.ref('hr_contract_extension.action_report_contract_form15').report_action(self)

    def action_print_form23(self):
        self.ensure_one()
        return self.env.ref('hr_contract_extension.action_report_contract_form23').report_action(self)


    @api.onchange('wage', 'house_rent_allowance', 'conveyance_allowance', 'medical_allowance', 'vehicle_allowance', 'washing_allowance', 'other_allowance', 'tour_expenses')
    def _onchange_gross(self):
        for contract in self:
            contract._compute_contract_amounts()

    @api.depends('tds_details_ids', 'tds_details_ids.annual_salary', 'tds_details_ids.tds_from_date', 'tds_details_ids.tds_to_date')
    def _compute_effective_fy_salary(self):
        for contract in self:
            effective = 0.0
            tds_recs = contract.tds_details_ids.sorted(key=lambda r: (r.tds_to_date or fields.Date.from_string('1900-01-01')), reverse=True)
            today = fields.Date.context_today(contract)
            # Prefer the TDS record whose FY covers today; fallback to latest
            chosen = False
            for rec in tds_recs:
                if rec.tds_from_date and rec.tds_to_date and rec.tds_from_date <= today <= rec.tds_to_date:
                    effective = float(math.ceil(rec.annual_salary or 0.0))
                    chosen = True
                    break
            if not chosen and tds_recs:
                effective = float(math.ceil(tds_recs[0].annual_salary or 0.0))
            contract.effective_fy_salary = float(math.ceil(effective or 0.0))

    def _prepare_pf_net_pay_vals(self, vals):
        self.ensure_one()

        wage = vals.get('wage', self.wage) or 0.0
        house_rent_allowance = vals.get('house_rent_allowance', self.house_rent_allowance) or 0.0
        conveyance_allowance = vals.get('conveyance_allowance', self.conveyance_allowance) or 0.0
        medical_allowance = vals.get('medical_allowance', self.medical_allowance) or 0.0
        vehicle_allowance = vals.get('vehicle_allowance', self.vehicle_allowance) or 0.0
        washing_allowance = vals.get('washing_allowance', self.washing_allowance) or 0.0
        other_allowance = vals.get('other_allowance', self.other_allowance) or 0.0
        tour_expenses = vals.get('tour_expenses', self.tour_expenses) or 0.0

        gross = wage + house_rent_allowance + conveyance_allowance + medical_allowance + vehicle_allowance + washing_allowance + other_allowance + tour_expenses

        apply_pf = vals.get('apply_pf', self.apply_pf)
        deduct_employee_pf = vals.get('deduct_employee_pf_in_net_pay', self.deduct_employee_pf_in_net_pay)
        deduct_employer_pf = vals.get('deduct_employer_pf_in_net_pay', self.deduct_employer_pf_in_net_pay)
        admin_percent = vals.get('pf_admin_percent', self.pf_admin_percent)
        admin_percent = max(min(float(admin_percent or 0.0), 13.0), 0.0) if apply_pf else 0.0

        employee_pf = float(math.ceil(wage * 0.12)) if apply_pf else 0.0
        employer_pf_total = float(math.ceil(wage * 0.13)) if apply_pf else 0.0
        admin_amt = float(math.ceil(wage * (admin_percent / 100.0))) if (apply_pf and admin_percent) else 0.0
        admin_amt = min(admin_amt, employer_pf_total)
        employer_share_amt = employer_pf_total - admin_amt

        employee_pf_deduction = employee_pf if (apply_pf and deduct_employee_pf) else 0.0
        # Employer PF is a company cost; it should not reduce employee Net Pay.
        employer_pf_deduction = 0.0

        tds = vals.get('tds', self.tds) or 0.0
        professional_tax = vals.get('professional_tax', self.professional_tax) or 0.0
        life_insurance_corporation = vals.get('life_insurance_corporation', self.life_insurance_corporation) or 0.0
        postal_life_insurance = vals.get('postal_life_insurance', self.postal_life_insurance) or 0.0
        group_insurance = vals.get('group_insurance', self.group_insurance) or 0.0
        credit_society = vals.get('credit_society', self.credit_society) or 0.0

        net_pay = gross - (
            tds
            + professional_tax
            + employee_pf_deduction
            + employer_pf_deduction
            + life_insurance_corporation
            + postal_life_insurance
            + group_insurance
            + credit_society
        )

        return {
            'gross': gross,
            'employee_provident_fund': employee_pf,
            'contributory_provident_fund': employer_pf_total,
            'employer_pf_total': employer_pf_total,
            'employer_pf_share': employer_share_amt,
            'pf_admin_expense': admin_amt,
            'net_pay': net_pay,
        }

    @api.onchange('apply_pf', 'wage')
    def _onchange_pf_contribution(self):
        for contract in self:
            contract._compute_contract_amounts()

    @api.onchange('apply_pf', 'deduct_employee_pf_in_net_pay', 'deduct_employer_pf_in_net_pay', 'pf_admin_percent', 'gross', 'tds', 'professional_tax', 'employee_provident_fund', 'contributory_provident_fund', 'life_insurance_corporation', 'postal_life_insurance', 'group_insurance', 'credit_society')
    def _onchange_net_pay(self):
        for contract in self:
            contract._compute_contract_amounts()

    def _generate_contract_reference_from_employee(self, employee):
        """Generate a contract reference based on employee.

        Notes:
        - We keep the native hr.contract sequence (if available) to ensure uniqueness.
        - We prefix with employee name to match the requested requirement.
        """
        employee_name = (employee.name or '').strip()
        seq = self.env['ir.sequence'].next_by_code('hr.contract')
        if employee_name and seq:
            return f"{employee_name} - {seq} - Contract"
        if employee_name:
            return f"{employee_name} - Contract"
        return seq or _('New')

    @api.onchange('employee_id')
    def _onchange_employee_id_set_contract_reference(self):
        for contract in self:
            if not contract.employee_id:
                continue
            # Only auto-fill when user hasn't already provided a reference.
            if contract.name and contract.name not in (_('New'), '/', ''):
                continue
            contract.name = contract._generate_contract_reference_from_employee(contract.employee_id)

    @api.onchange('employee_id')
    def _onchange_employee_id_warn_existing_contract(self):
        for contract in self:
            if not contract.employee_id:
                continue

            running_contract = self.env['hr.contract'].search([
                ('id', '!=', contract.id or 0),
                ('employee_id', '=', contract.employee_id.id),
                ('state', '=', 'open'),
                ('active', '=', True),
            ], limit=1)

            if running_contract:
                return {
                    'warning': {
                        'title': _('Existing Running Contract'),
                        'message': _(
                            "Employee already has a Running contract (%(contract)s). You can still create another contract in Draft, but you cannot start it while another Running contract exists.",
                            contract=running_contract.display_name,
                        ),
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Ensure reference is generated even when created via import/API.
            name = vals.get('name')
            employee_id = vals.get('employee_id')
            if employee_id and (not name or name in ('/', _('New'))):
                employee = self.env['hr.employee'].browse(employee_id)
                vals['name'] = self._generate_contract_reference_from_employee(employee)
            if not self._fields['net_pay'].compute:
                new_contract = self.new(vals)
                vals.update(new_contract._prepare_pf_net_pay_vals({}))
        return super().create(vals_list)

    def write(self, vals):
        if self._fields['net_pay'].compute:
            return super().write(vals)
        if self.env.context.get('skip_pf_net_pay_vals'):
            return super().write(vals)

        for contract in self:
            per_vals = dict(vals)
            per_vals.update(contract._prepare_pf_net_pay_vals(per_vals))
            super(HrContract, contract.with_context(skip_pf_net_pay_vals=True)).write(per_vals)

        return True

    def action_start_contract(self):
        today = fields.Date.today()
        for contract in self:
            if contract.state != 'draft':
                continue
            if contract.date_start and contract.date_start > today:
                raise UserError(_("You cannot start a contract before its Start Date. Please adjust the Start Date first."))

            start_date = contract.date_start or today

            # Find other running contracts; ignore closed/cancel/draft
            other_contracts = self.env['hr.contract'].search([
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                ('state', '=', 'open'),
                ('active', '=', True),
            ])
            if other_contracts:
                # Close overlapping running contracts
                to_close = other_contracts.filtered(lambda c: (not c.date_end or c.date_end >= start_date))
                if to_close:
                    to_close.write({
                        'state': 'close',
                        'date_end': start_date - timedelta(days=1),
                    })
            contract.write({'state': 'open'})
        return True

    def action_cancel_contract(self):
        for contract in self:
            if contract.state in ('cancel',):
                continue
            contract.write({'state': 'cancel'})
        return True

    def action_new_contract_from_current(self):
        """
        Expire current contract and create a new draft contract with a warning message.
        This allows salary increments mid-FY: TDS will sum salary from all contracts in current FY.
        """
        self.ensure_one()

        today = fields.Date.context_today(self)
        # Default suggestion: close current contract as yesterday, new contract starts today.
        wiz = self.env['hr.contract.new.wizard'].create({
            'current_contract_id': self.id,
            'previous_contract_end_date': today - timedelta(days=1),
            'new_contract_start_date': today,
        })

        # --- Odoo 13/17 customization note ---
        # Previously, we auto-closed the running contract with end date = yesterday and created a new draft.
        # User requirement: prompt for the contract end date when clicking New Contract.
        # Old logic preserved above in git history; replaced by explicit wizard flow.
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract.new.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # def action_configure_tds(self):
    #     hr_tds_id = self.env['hr.tds'].sudo()
    #     hr_tds_id = hr_tds_id.search([('hr_contract_id', '=', self.id)], order="id desc")
    #     if hr_tds_id:
    #         hr_tds_id = hr_tds_id.search([('is_tds_payslip', '=', True)], order="id desc", limit=1)
    #     elif not hr_tds_id:
    #         hr_tds_id = hr_tds_id.create({'hr_employee_id': self.employee_id.id, 'hr_contract_id': self.id, 'annual_salary': self.wage * 12})





class DeductionDescription(models.Model):
    _name = 'deduction.description'
    _description = 'Deduction Description'

    hr_tds_id = fields.Many2one('hr.tds')
    hr_contract_id = fields.Many2one('hr.contract')
    name = fields.Char('Deduction Description')
    section_id = fields.Many2one('tds.section', string='Section')
    scheme_id = fields.Many2one('tds.section.scheme', string='Investment/Scheme')
    scheme_details = fields.Char(related='scheme_id.scheme_details', string='Scheme Details')
    max_limit_deduction = fields.Float(related='scheme_id.max_limit_deduction', string='Max Limit Deduction')
    deduction_amt = fields.Float('Amount')
    
    # Tax Regime Type - to preserve deductions when switching between regimes
    tax_regime_type = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime'),
    ], string='Tax Regime Type', help='Automatically populated from parent TDS record to preserve deductions when switching regimes')

    @api.onchange('scheme_id')
    def _onchange_scheme_id_set_default_amount(self):
        for rec in self:
            if rec.scheme_id:
                rec.deduction_amt = rec.max_limit_deduction or 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-populate tax_regime_type from parent TDS record"""
        for vals in vals_list:
            # If tax_regime_type not explicitly provided, get it from parent TDS
            if 'tax_regime_type' not in vals and vals.get('hr_tds_id'):
                tds = self.env['hr.tds'].browse(vals['hr_tds_id'])
                if tds.tax_regime_type:
                    vals['tax_regime_type'] = tds.tax_regime_type
            # Fallback to 'old' for backward compatibility
            if 'tax_regime_type' not in vals:
                vals['tax_regime_type'] = 'old'
        return super().create(vals_list)


class MonthWiseTDS(models.Model):
    _name = 'month.wise.tds'
    _description = 'Month Wise TDS'

    hr_tds_id = fields.Many2one('hr.tds')
    hr_contract_id = fields.Many2one('hr.contract')
    months = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ], string="Month")

    tds_month_amt = fields.Float('TDS Amt')
    tds_month_year = fields.Char('TDS Month Year')
    is_previous_employer = fields.Boolean('Previous Employer Month', default=False, help='Indicates if this month was covered by previous employer')


    def unlink(self):
        res = super().unlink()
        return res


class TDSHistory(models.Model):
    _name = 'tds.history'
    _description = 'TDS History'

    hr_contract_id = fields.Many2one('hr.contract')
    employer_name = fields.Char('Employer Name')
    month = fields.Date('month')
    year = fields.Date('year')
    employer_tds = fields.Float('TDS Amount')
