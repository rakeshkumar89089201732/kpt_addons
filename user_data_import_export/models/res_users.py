# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError

USER_IMPORT_EXPORT_GROUP = 'user_data_import_export.group_user_import_export'
PASSWORD_MASK = '********'


class ResUsers(models.Model):
    _inherit = 'res.users'

    def export_data(self, fields_to_export):
        """Restrict user export to admin or users with User Data Export/Import group.
        Mask password column in exported data.
        """
        if self._name != 'res.users':
            return super(ResUsers, self).export_data(fields_to_export)

        if not (self.env.is_admin() or self.env.user.has_group(USER_IMPORT_EXPORT_GROUP)):
            raise UserError(_(
                "You don't have the rights to export user data. "
                "Please contact an Administrator to get the 'User Data Export/Import' access."
            ))

        result = super(ResUsers, self).export_data(fields_to_export)
        # Mask password in exported rows
        result['datas'] = self._mask_password_in_export_data(
            result['datas'], fields_to_export
        )
        return result

    def _mask_password_in_export_data(self, datas, fields_to_export):
        """Replace password column values with mask in exported data matrix."""
        password_indices = []
        for i, path in enumerate(fields_to_export):
            if path and len(path) > 0 and path[0] == 'password':
                password_indices.append(i)

        if not password_indices:
            return datas

        for row in datas:
            for idx in password_indices:
                if idx < len(row):
                    row[idx] = PASSWORD_MASK
        return datas

    @api.model
    def load(self, fields, data):
        """Restrict user import to admin or users with User Data Export/Import group."""
        if self._name != 'res.users':
            return super(ResUsers, self).load(fields, data)

        if not (self.env.is_admin() or self.env.user.has_group(USER_IMPORT_EXPORT_GROUP)):
            raise UserError(_(
                "You don't have the rights to import user data. "
                "Please contact an Administrator to get the 'User Data Export/Import' access."
            ))

        return super(ResUsers, self).load(fields, data)
