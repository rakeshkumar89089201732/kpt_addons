# -*- coding: utf-8 -*-

import odoo
from odoo import http
from odoo.http import request


class UserImportExportController(http.Controller):

    @http.route(
        '/user_data_import_export/download_sample',
        type='http',
        auth='user',
        methods=['GET'],
    )
    def download_user_import_sample(self, **kwargs):
        """Download the sample user import CSV template."""
        group = 'user_data_import_export.group_user_import_export'
        if not request.env.user.has_group(group) and not request.env.is_admin():
            return request.not_found()

        try:
            with odoo.tools.misc.file_open(
                'user_data_import_export/static/description/user_import_sample.csv',
                'rb',
            ) as f:
                content = f.read()
        except FileNotFoundError:
            return request.not_found()

        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', 'attachment; filename="user_import_sample.csv"'),
            ],
        )
