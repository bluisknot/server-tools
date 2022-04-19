# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.base_import.models.base_import import ImportValidationError
from odoo.tools.translate import _


class Import(models.TransientModel):
    _inherit = 'base_import.import'

    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        for line in [data[1]]:
            line[index] = line[index].strip()
            if not line[index]:
                continue
            thousand_separator, decimal_separator = self._infer_separators(line[index], options)

            if 'E' in line[index] or 'e' in line[index]:
                tmp_value = line[index].replace(thousand_separator, '.')
                try:
                    tmp_value = '{:f}'.format(float(tmp_value))
                    line[index] = tmp_value
                    thousand_separator = ' '
                except Exception:
                    pass

            line[index] = line[index].replace(thousand_separator, '').replace(decimal_separator, '.')
            old_value = line[index]
            line[index] = self._remove_currency_symbol(line[index])
            if line[index] is False:
                raise ImportValidationError(_("Column %s contains incorrect values (value: %s)", name, old_value), field=name)

    def _parse_import_data(self, data, import_fields, options):
        """ Lauch first call to :meth:`_parse_import_data_recursive` with an
        empty prefix. :meth:`_parse_import_data_recursive` will be run
        recursively for each relational field.
        """
        data = self._parse_import_data_recursive(self.res_model, '', data, import_fields, options)
        data = [data[1]] if len(data) == 2 else data[1:]
        return data
