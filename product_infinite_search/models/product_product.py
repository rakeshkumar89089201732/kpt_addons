# -*- coding: utf-8 -*-

import re
import logging

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# High limit for "infinite" product search when no limit is passed
INFINITE_SEARCH_LIMIT = 15000

# =============================================================================
# TALLY-STYLE PRODUCT SEARCH
# =============================================================================
# Tally ERP search works by matching ANY combination of typed characters
# against product names, regardless of separators, spaces, or order.
#
# Example: User types "pn16 160mm tl"
#   -> Strip non-alphanumeric: "pn16160mmtl"
#   -> Build char-subsequence pattern: "p%n%1%6%1%6%0%m%m%t%l"
#   -> SQL: WHERE name ILIKE '%p%n%1%6%1%6%0%m%m%t%l%'
#   -> Matches: "PN 16 160MM T/L GREEN 3" (characters appear in order)
#
# This uses a SINGLE ILIKE pattern instead of N separate AND conditions,
# making it both correct AND efficient.
#
# Previous approach (robust_search module) used character-by-character AND
# conditions (19 separate AND clauses for "pn16 160mm tl"), which was
# too restrictive and produced no results. That module is now disabled.
# =============================================================================


class ProductProduct(models.Model):
    _inherit = "product.product"

    # =========================================================================
    # UTILITY: Tokenizer (kept for backward compatibility / advanced strategies)
    # =========================================================================
    @api.model
    def _tally_tokenize(self, search_str):
        """Tally-style tokenizer: splits any search string into meaningful
        tokens for word-level matching strategies.

        Used by product_template.py for direct Tally search.
        """
        if not search_str:
            return []

        # Step 1: Split by common separators (space, /, -, _, \, |, comma, dot, ;)
        initial_tokens = [t for t in re.split(r'[\s/\\_|,;.\-]+', search_str) if t.strip()]

        result = []
        for token in initial_tokens:
            if not token:
                continue
            # Step 2: Split on camelCase and number-letter boundaries
            split_token = token
            split_token = re.sub(r'([A-Za-z])(\d)', r'\1 \2', split_token)
            split_token = re.sub(r'(\d)([A-Za-z])', r'\1 \2', split_token)
            split_token = re.sub(r'([a-z])([A-Z])', r'\1 \2', split_token)

            parts = [p.strip() for p in split_token.split() if p.strip()]
            result.extend(parts)

        return result

    # =========================================================================
    # CORE: Character subsequence search (Tally-style)
    # =========================================================================
    @api.model
    def _tally_char_search(self, name, domain, limit, order):
        """Character-level subsequence search - the core of Tally-style search.

        How it works:
        1. Strip ALL non-alphanumeric from search input
        2. Insert '%' between EACH character
        3. Use ilike which adds outer '%' on both sides
        4. Result: a single ILIKE pattern that matches the characters in order

        Example: "pn16 160mm t/l" -> strip -> "pn16160mmtl"
                 -> pattern -> "p%n%1%6%1%6%0%m%m%t%l"
                 -> SQL: WHERE name ILIKE '%p%n%1%6%1%6%0%m%m%t%l%'
                 This matches ANY product name containing these chars in order,
                 regardless of separators, spaces, or casing.

        This approach uses exactly 2 ILIKE conditions (name OR default_code),
        unlike the old robust_search which used 19+ AND conditions.
        """
        # Step 1: Strip all non-alphanumeric characters
        clean = re.sub(r'[^a-zA-Z0-9]', '', name)
        if not clean:
            return []

        _logger.info(
            "Tally char search: input='%s' -> clean='%s' -> %d chars",
            name, clean, len(clean)
        )

        # =====================================================================
        # Strategy 1: Character subsequence match (chars in order)
        # "pn16160mmtl" -> "%p%n%1%6%1%6%0%m%m%t%l%"
        # =====================================================================
        pattern = '%'.join(clean)  # ilike adds outer % automatically
        search_domain = expression.AND([
            domain,
            expression.OR([
                [('name', 'ilike', pattern)],
                [('default_code', 'ilike', pattern)],
            ])
        ])
        product_ids = list(self._search(search_domain, limit=limit, order=order))
        if product_ids:
            _logger.info(
                "Tally search Strategy 1 (char subsequence): found %d products",
                len(product_ids)
            )
            return product_ids

        # =====================================================================
        # Strategy 2: All unique characters present (any order)
        # For when user types characters in a different order than the product name
        # Each unique character must appear somewhere in name or default_code
        # =====================================================================
        unique_chars = list(set(clean.lower()))
        if len(unique_chars) <= 20:  # Safety: avoid excessive domain conditions
            char_domains = []
            for char in unique_chars:
                char_domain = expression.OR([
                    [('name', 'ilike', char)],
                    [('default_code', 'ilike', char)],
                ])
                char_domains.append(char_domain)

            combined = expression.AND(char_domains)
            full_domain = expression.AND([domain, combined])
            product_ids = list(self._search(full_domain, limit=limit, order=order))
            if product_ids:
                _logger.info(
                    "Tally search Strategy 2 (all unique chars, any order): found %d products",
                    len(product_ids)
                )
                return product_ids

        # =====================================================================
        # Strategy 3: Progressive character matching
        # Try with ALL chars first, then try dropping chars from the end
        # This handles cases where user typed too many chars
        # =====================================================================
        if len(clean) > 3:
            # Try with 75% of chars (from the beginning)
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
            product_ids = list(self._search(search_domain, limit=limit, order=order))
            if product_ids:
                _logger.info(
                    "Tally search Strategy 3 (partial %d/%d chars): found %d products",
                    partial_len, len(clean), len(product_ids)
                )
                return product_ids

        return []

    # =========================================================================
    # CORE: Word-token search (complementary to character search)
    # =========================================================================
    @api.model
    def _tally_word_search(self, name, domain, limit, order):
        """Word-level tokenized search as a complementary strategy.

        Splits input into word tokens and requires each token to match
        in name or default_code. This handles cases where character
        subsequence is too strict (different word order, etc.)
        """
        tokens = self._tally_tokenize(name)
        if not tokens:
            return []

        # Try all tokens (AND)
        token_domains = [
            expression.OR([
                [('name', 'ilike', term)],
                [('default_code', 'ilike', term)],
            ])
            for term in tokens
        ]
        combined = expression.AND(token_domains)
        full_domain = expression.AND([domain, combined])
        product_ids = list(self._search(full_domain, limit=limit, order=order))
        if product_ids:
            return product_ids

        # Try with N-1 tokens (in case one token is a typo)
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
                product_ids = list(self._search(full_domain, limit=limit, order=order))
                if product_ids:
                    return product_ids

        # Try any single token (broadest)
        any_token_domains = [
            expression.OR([
                [('name', 'ilike', t)],
                [('default_code', 'ilike', t)],
            ])
            for t in tokens if len(t) >= 2 or t.isdigit()
        ]
        if any_token_domains:
            union_domain = expression.OR(any_token_domains)
            full_domain = expression.AND([domain, union_domain])
            product_ids = list(self._search(full_domain, limit=limit, order=order))
            if product_ids:
                return product_ids

        return []

    # =========================================================================
    # MAIN ENTRY: name_search override (PUBLIC method - called by RPC)
    # =========================================================================
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override the PUBLIC name_search to ensure Tally-style search is
        always used, regardless of MRO conflicts with other modules.

        Docstring: This is the method called by Many2One autocomplete via RPC.
        By overriding this (the public method), we guarantee our search logic
        runs even if another module overrides _name_search.
        """
        if name:
            # Use our custom search
            domain = args or []
            search_limit = limit or 80

            # Primary: Character subsequence (Tally-style)
            product_ids = self._tally_char_search(
                name, domain, search_limit, order=None
            )
            if not product_ids:
                # Secondary: Word-level token search
                product_ids = self._tally_word_search(
                    name, domain, search_limit, order=None
                )

            if product_ids:
                products = self.browse(product_ids)
                return [(p.id, p.display_name) for p in products]

        # Fallback to standard Odoo name_search
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    # =========================================================================
    # ALSO OVERRIDE _name_search for compatibility
    # (called by ORM when resolving Many2One name lookups in domains)
    # =========================================================================
    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Override _name_search for Tally-style search.

        This is called internally by the ORM for domain resolution.
        We override both name_search (RPC) and _name_search (ORM internal)
        to ensure complete coverage.
        """
        domain = domain or []
        if limit is None or self.env.context.get('product_infinite_search'):
            limit = limit or INFINITE_SEARCH_LIMIT

        if not name:
            return super()._name_search(name, domain, operator, limit, order)

        positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']

        if operator in positive_operators:
            # Primary: Character subsequence search
            product_ids = self._tally_char_search(name, domain, limit, order)
            if product_ids:
                return product_ids

            # Secondary: Word-level token search
            product_ids = self._tally_word_search(name, domain, limit, order)
            if product_ids:
                return product_ids

        # Fallback to standard Odoo search
        return super()._name_search(name, domain, operator, limit, order)

    # =========================================================================
    # CUSTOM RPC METHOD: Direct product search (bypasses name_search entirely)
    # Called by our custom JS patch when standard name_search fails
    # =========================================================================
    @api.model
    def tally_product_search(self, search_term, domain=None, limit=80):
        """Custom RPC method for Tally-style product search.

        This method is called directly from JavaScript as a backup when
        the standard name_search pathway is intercepted by other modules.
        It completely bypasses the name_search chain.

        Returns: list of [id, display_name] tuples
        """
        domain = domain or []
        if not search_term:
            products = self.search(domain, limit=limit)
            return [(p.id, p.display_name) for p in products]

        # Character subsequence search
        product_ids = self._tally_char_search(search_term, domain, limit, order=None)

        if not product_ids:
            # Word-level token search
            product_ids = self._tally_word_search(search_term, domain, limit, order=None)

        if not product_ids:
            # Ultimate fallback: standard ilike on name
            fallback_domain = expression.AND([
                domain,
                [('name', 'ilike', search_term)]
            ])
            product_ids = list(self._search(fallback_domain, limit=limit))

        if product_ids:
            products = self.browse(product_ids)
            return [(p.id, p.display_name) for p in products]

        return []
