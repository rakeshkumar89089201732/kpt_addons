# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# =============================================================================
# DISABLED: This module's _name_search, name_search, and _search overrides
# were conflicting with the product_infinite_search module, causing "No records"
# in Many2One product dropdowns. 
#
# ROOT CAUSE: The character-by-character AND search approach created enormous
# SQL queries (one condition per character) that were too restrictive.
# For "greentherm pn16 160mm", it generated 19 separate AND conditions
# (one for each character: g, r, e, e, n, t, h, e, r, m, p, n, 1, 6, 1, 6, 0, m, m)
# which practically never matched any product name.
#
# Additionally, the name_search() override returned [] instead of proper
# tuples, and the _search() override intercepted domain logic at the lowest
# level, corrupting other modules' search behavior.
#
# All enhanced product search logic is now consolidated in the
# product_infinite_search module which uses a proper Tally-style tokenized
# search (word-level tokens, not character-level).
# =============================================================================

import re
from odoo import api, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # --- Original _calculate_match_score method ---
    # --- Commented out: was used by the character-by-character search ---
    # --- which has been replaced by product_infinite_search module ---
    # def _calculate_match_score(self, product, search_term):
    #     """Calculate match score - lower is better"""
    #     clean_search = re.sub(r'[^a-zA-Z0-9]', '', search_term).lower()
    #     name = (product.name or '').lower()
    #     code = (product.default_code or '').lower()
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
    # --- and conflicted with product_infinite_search module's tokenized search ---
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
    #             '|', '|', '|',
    #             ('name', 'ilike', f'%{char}%'),
    #             ('default_code', 'ilike', f'%{char}%'),
    #             ('barcode', 'ilike', f'%{char}%'),
    #             ('product_tmpl_id.name', 'ilike', f'%{char}%'),
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
    #         products = self.search(final_domain, limit=None, order=None)
    #         products_with_score = [(p, self._calculate_match_score(p, search_term)) for p in products]
    #         products_with_score.sort(key=lambda x: x[1])
    #         sorted_ids = [p[0].id for p in products_with_score]
    #         if limit:
    #             sorted_ids = sorted_ids[:limit]
    #         return sorted_ids
    #     except Exception:
    #         return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

    # --- Original name_search method ---
    # --- Commented out: returned [] instead of falling back to super(), ---
    # --- and intercepted the public API bypassing product_infinite_search ---
    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     """
    #     Override name_search to utilize our enhanced _name_search method.
    #     This ensures compatibility with all Odoo search contexts.
    #     """
    #     ids = self._name_search(name=name, domain=args, operator=operator, limit=limit)
    #     if ids:
    #         products = self.browse(ids)
    #         return [(product.id, product.display_name) for product in products]
    #     return []

    # --- Original _search method ---
    # --- Commented out: intercepted domain logic at the lowest level, ---
    # --- corrupting other modules' search behavior including ---
    # --- product_infinite_search's _tally_search which calls self._search() ---
    # def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
    #     """
    #     Override _search for list view search bar - simple regex approach
    #     """
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
    #                                 '|', '|', '|',
    #                                 ('name', 'ilike', f'%{char}%'),
    #                                 ('default_code', 'ilike', f'%{char}%'),
    #                                 ('barcode', 'ilike', f'%{char}%'),
    #                                 ('product_tmpl_id.name', 'ilike', f'%{char}%'),
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