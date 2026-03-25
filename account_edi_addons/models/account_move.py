# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_document_ids = fields.One2many(
        comodel_name='account.edi.document',
        inverse_name='move_id')
    show_process_section = fields.Boolean(string='Show Process Section', default=False)
    edi_web_services_einvoice = fields.Char(compute='_compute_edi_web_services_einvoice')
    edi_web_services_ewaybill = fields.Char(compute='_compute_edi_web_services_ewaybill')

    # E-Invoice Web Service
    @api.depends('edi_document_ids', 'edi_document_ids.state', 'edi_document_ids.blocking_level',
                 'edi_document_ids.edi_format_id', 'edi_document_ids.edi_format_id.name')
    def _compute_edi_web_services_einvoice(self):
        for move in self:
            to_process = move.edi_document_ids.filtered(
                lambda d: d.state in ['to_send',
                                      'to_cancel'] and d.blocking_level != 'error' and d.edi_format_id.code == 'in_einvoice_1_03')
            move.edi_web_services_einvoice = ', '.join(to_process.mapped('edi_format_id.name'))

    # E-Way Bill Web Service
    @api.depends('edi_document_ids', 'edi_document_ids.state', 'edi_document_ids.blocking_level',
                 'edi_document_ids.edi_format_id', 'edi_document_ids.edi_format_id.name')
    def _compute_edi_web_services_ewaybill(self):
        for move in self:
            to_process = move.edi_document_ids.filtered(
                lambda d: d.state in ['to_send',
                                      'to_cancel'] and d.blocking_level != 'error' and d.edi_format_id.code == 'in_ewaybill_1_03')
            move.edi_web_services_ewaybill = ', '.join(to_process.mapped('edi_format_id.name'))

    def button_process_edi_web_services(self):
        self.ensure_one()
        self.action_process_edi_web_services(with_commit=False)
        self.write({'show_process_section': False})

    def action_process_edi_web_services(self, with_commit=True):
        docs = self.edi_document_ids.filtered(
            lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
        docs._process_documents_web_services(with_commit=with_commit)
        self.write({'show_process_section': False})  # Ensure the process section is hidden after processing

    # Write Show Process Section
    def cancel_to_send(self):
        self.write({'show_process_section': False})

    # E-Invoice Send Button
    def button_send_einvoice(self):
        self._process_edi_documents('in_einvoice_1_03')
        self._process_specific_edi_documents('in_einvoice_1_03')
        # self.write({'invisible_einvoice': True})

    # E-Way Bill Send Button
    def button_send_ewaybill(self):
        self._process_edi_documents('in_ewaybill_1_03')
        self._process_specific_edi_documents('in_ewaybill_1_03')
        # self.write({'invisible_eway': True})

    # Process EDI Document
    def _process_edi_documents(self, edi_format_code):
        edi_format = self.env['account.edi.format'].search([('code', '=', edi_format_code)], limit=1)
        if not edi_format:
            raise UserError(_("EDI format not found for code: %s") % edi_format_code)
        edi_document_vals_list = []
        for move in self:
            if move.state != 'posted':
                raise UserError(_("You can only create documents from posted invoices"))
            errors = edi_format._check_move_configuration(move)
            if errors:
                raise UserError(_("Invalid invoice configuration:\n\n%s") % '\n'.join(errors))
            existing_edi_document = move._get_edi_document(edi_format)
            if existing_edi_document:
                if existing_edi_document.state == 'to_cancel':
                    existing_edi_document.write({'state': 'to_send', 'error': False})
            else:
                edi_document_vals_list.append({
                    'edi_format_id': edi_format.id,
                    'move_id': move.id,
                    'state': 'to_send',
                })
        if edi_document_vals_list:
            self.env['account.edi.document'].create(edi_document_vals_list)
        self.write({'show_process_section': True})

    # Process Specific E-way bill and E-invoice
    def _process_specific_edi_documents(self, edi_format_code):
        specific_docs = self.edi_document_ids.filtered(lambda d: d.edi_format_id.code == edi_format_code)
        specific_docs._process_documents_web_services(with_commit=True)
        self.write({'show_process_section': False})

    # E-Invoice Cancel Button
    def einvoice_button_cancel_posted_moves(self):
        '''Mark the edi.document related to this move to be canceled.'''
        to_cancel_documents = self.env['account.edi.document']
        for move in self:
            move._check_fiscalyear_lock_date()
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.edi_format_id.code == 'in_einvoice_1_03' and doc.edi_format_id._needs_web_services() and doc.state == 'sent':
                    to_cancel_documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A cancellation of the E-invoice has been requested."))
        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})
        self.write({'show_process_section': True})

    # E-Way Bill Cancel Button
    def eway_button_cancel_posted_moves(self):
        '''Mark the edi.document related to this move to be canceled.'''
        to_cancel_documents = self.env['account.edi.document']
        for move in self:
            move._check_fiscalyear_lock_date()
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.edi_format_id.code == 'in_ewaybill_1_03' and doc.edi_format_id._needs_web_services() and doc.state == 'sent':
                    to_cancel_documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A cancellation of the E-way Bill has been requested."))
        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})
        self.write({'show_process_section': True})

    def button_abandon_cancel_posted_posted_moves(self):
        '''Cancel the request for cancellation of the EDI.
        '''
        documents = self.env['account.edi.document']
        for move in self:
            is_move_marked = False
            for doc in move.edi_document_ids:
                move_applicability = doc.edi_format_id._get_move_applicability(move)
                if doc.state == 'to_cancel' and move_applicability and move_applicability.get('cancel'):
                    documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A request for cancellation of the EDI has been called off."))
        documents.write({'state': 'sent'})
        self.write({'show_process_section': True})

    def button_cancel_posted_moves(self):
        '''Mark the edi.document related to this move to be canceled.
        '''
        to_cancel_documents = self.env['account.edi.document']
        for move in self:
            move._check_fiscalyear_lock_date()
            is_move_marked = False
            for doc in move.edi_document_ids:
                move_applicability = doc.edi_format_id._get_move_applicability(move)
                if doc.edi_format_id._needs_web_services() \
                        and doc.state == 'sent' \
                        and move_applicability \
                        and move_applicability.get('cancel'):
                    to_cancel_documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A cancellation of the EDI has been requested."))

        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})







