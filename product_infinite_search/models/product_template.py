# -*- coding: utf-8 -*-

import re
import logging

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# High limit for "infinite" product search (used when no limit is passed)
INFINITE_SEARCH_LIMIT = 15000

# --- Original code used a while-loop delegation to product.product._name_search ---
# --- which was slow and the Tally-style search didn't properly carry through. ---
# --- The new implementation applies character-subsequence matching directly on ---
# --- product.template, consistent with product.product's approach. ---


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override the PUBLIC name_search for product.template.

        Uses the same character-subsequence matching as product.product
        to ensure consistent Tally-style search behavior.
        """
        if name:
            domain = args or []
            search_limit = limit or 80

            # Primary: Character subsequence search
            tmpl_ids = self._tally_char_search_tmpl(name, domain, search_limit)
            if not tmpl_ids:
                # Secondary: Word-level token search
                tmpl_ids = self._tally_word_search_tmpl(name, domain, search_limit)

            if tmpl_ids:
                templates = self.browse(tmpl_ids)
                return [(t.id, t.display_name) for t in templates]

        # Fallback to standard Odoo name_search
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Override _name_search for product.template with Tally-style search.

        Uses character-subsequence matching (same approach as product.product).
        """
        domain = domain or []
        if limit is None:
            limit = INFINITE_SEARCH_LIMIT

        if not name:
            return super()._name_search(name, domain, operator, limit, order)

        positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']

        if operator in positive_operators:
            # Primary: Character subsequence search
            tmpl_ids = self._tally_char_search_tmpl(name, domain, limit)
            if tmpl_ids:
                return tmpl_ids

            # Secondary: Word-level token search
            tmpl_ids = self._tally_word_search_tmpl(name, domain, limit)
            if tmpl_ids:
                return tmpl_ids

        # Fallback to standard Odoo search
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def _tally_char_search_tmpl(self, name, domain, limit):
        """Character-level subsequence search for product.template.

        Same logic as product.product._tally_char_search but operates
        directly on product.template fields (name, default_code).
        """
        clean = re.sub(r'[^a-zA-Z0-9]', '', name)
        if not clean:
            return []

        # Strategy 1: Character subsequence (chars in order)
        pattern = '%'.join(clean)
        search_domain = expression.AND([
            domain,
            expression.OR([
                [('name', 'ilike', pattern)],
                [('default_code', 'ilike', pattern)],
            ])
        ])
        tmpl_ids = list(self._search(search_domain, limit=limit))
        if tmpl_ids:
            return tmpl_ids

        # Strategy 2: All unique characters present (any order)
        unique_chars = list(set(clean.lower()))
        if len(unique_chars) <= 20:
            char_domains = []
            for char in unique_chars:
                char_domain = expression.OR([
                    [('name', 'ilike', char)],
                    [('default_code', 'ilike', char)],
                ])
                char_domains.append(char_domain)

            combined = expression.AND(char_domains)
            full_domain = expression.AND([domain, combined])
            tmpl_ids = list(self._search(full_domain, limit=limit))
            if tmpl_ids:
                return tmpl_ids

        # Strategy 3: Partial characters
        if len(clean) > 3:
            partial_len = max(3, int(len(clean) * 0.75))
            partial_clean = clean[:partial_len]
            pattern = '%'.join(partial_clean)
            search_domain = expression.AND([
                domain,
                expression.OR([
                    [('name', 'ilike', pattern)],
                    [('default_code', 'ilike', pattern)],
                ])
            ])
            tmpl_ids = list(self._search(search_domain, limit=limit))
            if tmpl_ids:
                return tmpl_ids

        return []

    @api.model
    def _tally_word_search_tmpl(self, name, domain, limit):
        """Word-level tokenized search for product.template."""
        Product = self.env['product.product']
        tokens = Product._tally_tokenize(name)
        if not tokens:
            return []

        # All tokens (AND)
        token_domains = [
            expression.OR([
                [('name', 'ilike', t)],
                [('default_code', 'ilike', t)],
            ])
            for t in tokens
        ]
        combined = expression.AND(token_domains)
        full_domain = expression.AND([domain, combined])
        tmpl_ids = list(self._search(full_domain, limit=limit))
        if tmpl_ids:
            return tmpl_ids

        # N-1 tokens
        if len(tokens) > 2:
            for skip_idx in range(len(tokens)):
                remaining = tokens[:skip_idx] + tokens[skip_idx + 1:]
                token_domains = [
                    expression.OR([
                        [('name', 'ilike', t)],
                        [('default_code', 'ilike', t)],
                    ])
                    for t in remaining
                ]
                combined = expression.AND(token_domains)
                full_domain = expression.AND([domain, combined])
                tmpl_ids = list(self._search(full_domain, limit=limit))
                if tmpl_ids:
                    return tmpl_ids

        # Any single token (broadest)
        any_domains = [
            expression.OR([
                [('name', 'ilike', t)],
                [('default_code', 'ilike', t)],
            ])
            for t in tokens if len(t) >= 2 or t.isdigit()
        ]
        if any_domains:
            union_domain = expression.OR(any_domains)
            full_domain = expression.AND([domain, union_domain])
            tmpl_ids = list(self._search(full_domain, limit=limit))
            if tmpl_ids:
                return tmpl_ids

        return []

    # =========================================================================
    # CUSTOM RPC METHOD: Direct template search (bypasses name_search entirely)
    # Called by our custom JS patch when standard name_search fails
    # =========================================================================
    @api.model
    def tally_product_search(self, search_term, domain=None, limit=80):
        """Custom RPC method for Tally-style product template search.

        This method is called directly from JavaScript as a backup when
        the standard name_search pathway is intercepted by other modules.
        """
        domain = domain or []
        if not search_term:
            templates = self.search(domain, limit=limit)
            return [(t.id, t.display_name) for t in templates]

        # Character subsequence search
        tmpl_ids = self._tally_char_search_tmpl(search_term, domain, limit)

        if not tmpl_ids:
            # Word-level token search
            tmpl_ids = self._tally_word_search_tmpl(search_term, domain, limit)

        if not tmpl_ids:
            # Ultimate fallback: standard ilike on name
            fallback_domain = expression.AND([
                domain,
                [('name', 'ilike', search_term)]
            ])
            tmpl_ids = list(self._search(fallback_domain, limit=limit))

        if tmpl_ids:
            templates = self.browse(tmpl_ids)
            return [(t.id, t.display_name) for t in templates]

        return []

