# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# =============================================================================
# DISABLED: This module's _name_search, name_search, and _search overrides
# were conflicting with the product_infinite_search module, causing "No records"
# in Many2One product dropdowns.
#
# ROOT CAUSE: Same character-by-character AND approach as product_product.py.
# The product.template._name_search was also bypassing the 
# product_infinite_search.product_template._name_search which properly
# delegates to product.product for Tally-style tokenized search.
#
# All enhanced product search logic is now consolidated in the
# product_infinite_search module.
# =============================================================================

import re
from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # --- Original _calculate_match_score method ---
    # --- Commented out: was used by the character-by-character search ---
    # def _calculate_match_score(self, template, search_term):
    #     """Calculate match score - lower is better"""
    #     clean_search = re.sub(r'[^a-zA-Z0-9]', '', search_term).lower()
    #     name = (template.name or '').lower()
    #     code = (template.default_code or '').lower()
    #     score = 1000
    #     if clean_search == re.sub(r'[^a-zA-Z0-9]', '', name):
    #         return 1
    #     if clean_search == re.sub(r'[^a-zA-Z0-9]', '', code):
    #         return 2
    #     if clean_search in name:
    #         score = 10
    #     elif clean_search in code:
    #         score = 20
    #     else:
    #         name_clean = re.sub(r'[^a-zA-Z0-9]', '', name)
    #         score = 100 + abs(len(name_clean) - len(clean_search))
    #     return score

    # --- Original _name_search method ---
    # --- Commented out: character-by-character AND search was too restrictive ---
    # @api.model
    # def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
    #     """
    #     Fuzzy search with intelligent ranking - best matches first
    #     """
    #     if not name or len(name.strip()) == 0:
    #         return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
    #     domain = domain or []
    #     search_term = name.strip()
    #     clean_search = re.sub(r'[^a-zA-Z0-9]', '', search_term)
    #     if not clean_search:
    #         return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
    #     search_domains = []
    #     for char in clean_search:
    #         char_domain = [
    #             '|', '|',
    #             ('name', 'ilike', f'%{char}%'),
    #             ('default_code', 'ilike', f'%{char}%'),
    #             ('barcode', 'ilike', f'%{char}%'),
    #         ]
    #         search_domains.append(char_domain)
    #     if len(search_domains) == 1:
    #         combined = search_domains[0]
    #     else:
    #         combined = []
    #         for i in range(len(search_domains) - 1):
    #             combined.append('&')
    #         for char_domain in search_domains:
    #             combined.extend(char_domain)
    #     final_domain = expression.AND([domain, combined])
    #     try:
    #         templates = self.search(final_domain, limit=None, order=None)
    #         templates_with_score = [(t, self._calculate_match_score(t, search_term)) for t in templates]
    #         templates_with_score.sort(key=lambda x: x[1])
    #         sorted_ids = [t[0].id for t in templates_with_score]
    #         if limit:
    #             sorted_ids = sorted_ids[:limit]
    #         return sorted_ids
    #     except Exception:
    #         return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

    # --- Original name_search method ---
    # --- Commented out: returned [] when no results, breaking the API ---
    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     ids = self._name_search(name=name, domain=args, operator=operator, limit=limit)
    #     if ids:
    #         templates = self.browse(ids)
    #         return [(template.id, template.display_name) for template in templates]
    #     return []

    # --- Original _search method ---
    # --- Commented out: intercepted domain logic at lowest level ---
    # def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
    #     try:
    #         if not domain or not isinstance(domain, list):
    #             return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
    #         context = self.env.context or {}
    #         if 'product_catalog' in str(context):
    #             return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
    #         new_domain = []
    #         modified = False
    #         for item in domain:
    #             if (isinstance(item, (list, tuple)) and len(item) == 3 and
    #                 item[0] == 'name' and item[1] in ('ilike', '=ilike')):
    #                 search_term = item[2]
    #                 if search_term and isinstance(search_term, str):
    #                     clean_search = re.sub(r'[^a-zA-Z0-9]', '', search_term)
    #                     if clean_search:
    #                         char_domains = []
    #                         for char in clean_search:
    #                             char_domain = [
    #                                 '|', '|',
    #                                 ('name', 'ilike', f'%{char}%'),
    #                                 ('default_code', 'ilike', f'%{char}%'),
    #                                 ('barcode', 'ilike', f'%{char}%'),
    #                             ]
    #                             char_domains.append(char_domain)
    #                         if len(char_domains) == 1:
    #                             combined = char_domains[0]
    #                         else:
    #                             combined = []
    #                             for j in range(len(char_domains) - 1):
    #                                 combined.append('&')
    #                             for cd in char_domains:
    #                                 combined.extend(cd)
    #                         new_domain.extend(combined)
    #                         modified = True
    #                         continue
    #             new_domain.append(item)
    #         domain = new_domain if modified else domain
    #         return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
    #     except Exception:
    #         return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)