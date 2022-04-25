# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from tempfile import TemporaryFile
from zipfile import BadZipFile

import xlrd
import xlwt
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

FROM_EXCEL_FILE_MIXIN_MODEL_NAME = "modify.model_fields.from.excel_file"
IMPORT_FILE_MODEL_NAME = "xlsx.import"
IMPORT_TEMPLATE_MODEL_NAME = "xlsx.template"
UNSUPPORTED_FILE_MSG = "Unsupported file format, this import option only supports excel files (*.xls, *.xlsx)."


class ModifyModelFieldsFromExcelFileMixin(models.AbstractModel):
    _name = FROM_EXCEL_FILE_MIXIN_MODEL_NAME
    _description = "Mixin to fill any field that you may have from excel files."

    import_file = fields.Binary(string="Import File (*.xls, *.xlsx)")
    import_template_id = fields.Many2one(
        comodel_name=IMPORT_TEMPLATE_MODEL_NAME,
        string="Import Template",
    )

    @api.onchange("import_file")
    def onchange_import_file(self):
        if self.import_file:
            return self._check_excel_file_content(self.import_file)

    @api.constrains("import_file")
    def constrains_import_file(self):
        for mixin in self:
            if mixin.import_file:
                self._check_excel_file_content(mixin.import_file, for_onchange=False)

    @api.model
    def _check_excel_file_content(self, base64_data, for_onchange=True, convert_to_xls=False, b64econded=True):
        decoded_data = base64.b64decode(base64_data)
        successfull_result = {} if for_onchange else True
        try:
            xlrd.open_workbook(file_contents=decoded_data)
            return successfull_result
        except xlrd.XLRDError:
            unsupported_file_msg = _(UNSUPPORTED_FILE_MSG)
            bad_result_dict = {
                "warning": {"title": "Error de validación", "message": unsupported_file_msg},
                "value": {"import_file": None},
            }
            try:
                with TemporaryFile() as xlsx_file:
                    xlsx_file.write(decoded_data)
                    xlsx_file.seek(0)
                    xlsx_workbook = load_workbook(filename=xlsx_file, data_only=True)
                    if convert_to_xls:
                        return self._convert_to_xls(xlsx_workbook, b64econded=b64econded)
                    return successfull_result
            except InvalidFileException:
                if for_onchange:
                    return bad_result_dict
                else:
                    raise ValidationError(unsupported_file_msg)
            except BadZipFile:
                if for_onchange:
                    return bad_result_dict
                else:
                    raise ValidationError(unsupported_file_msg)

    @api.model
    def _convert_to_xls(self, xlsx_workbook, b64econded=True):
        xslx_active_sheet = xlsx_workbook.active
        xls_workbook = xlwt.Workbook()
        xls_active_sheet = xls_workbook.add_sheet(xslx_active_sheet.title)
        for row_index, row in enumerate(
            xslx_active_sheet.iter_rows(
                min_row=xslx_active_sheet.min_row,
                max_row=xslx_active_sheet.max_row,
                min_col=xslx_active_sheet.min_column,
                max_col=xslx_active_sheet.max_column,
            )
        ):
            for col_index, row_info in enumerate(row):
                xls_active_sheet.write(row_index, col_index, row_info.value)
        if not b64econded:
            return xls_workbook
        else:
            content = BytesIO()
            xls_workbook.save(content)
            content.seek(0)  # Set index to 0, and start reading
            return base64.b64encode(content.read())

    @api.model
    def create(self, vals_list):
        created = super().create(vals_list)
        import_excel_file = vals_list.get("import_file", None)
        if import_excel_file:
            created.perform_import(vals_list["import_template_id"], import_excel_file)
        return created

    def write(self, vals):
        result = super().write(vals)
        import_excel_file = vals.get("import_file", None)
        if result and import_excel_file:
            for mixin in self:
                mixin.perform_import(mixin.import_template_id.id, import_excel_file)
        return result

    def perform_import(self, import_template_id, import_excel_file):
        self.ensure_one()

        CustomImportModel = self.env[IMPORT_FILE_MODEL_NAME]
        import_excel_file_template = self.env[IMPORT_TEMPLATE_MODEL_NAME].browse(import_template_id)
        import_excel_file = self._check_excel_file_content(import_excel_file, for_onchange=False, convert_to_xls=True)
        CustomImportModel.import_xlsx(
            base64.encodebytes(base64.b64decode(import_excel_file)),
            import_excel_file_template,
            res_model=self._name,
            res_id=self.id,
        )
