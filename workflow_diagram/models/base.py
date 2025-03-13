# -*- coding: utf-8 -*-
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ViewBaseWFL(models.AbstractModel):
    _inherit = 'base'
    _tier_validation_buttons_xpath = "/form/header/button[last()]"

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super(ViewBaseWFL, self).get_view(view_id, view_type, **options)
        workflow_id = self.env['workflow.config'].search([('model', '=', self._name), ('state', '=', 'in_use')])
        try:
            if workflow_id and view_type == 'form':
                hold_buttons = []
                if workflow_id.mapped('hold_buttons'):
                    for button in workflow_id.mapped('hold_buttons'):
                        if not button:
                            continue
                        if ',' not in button:
                            hold_buttons.append(button)
                        if ',' in button:
                            buttons = button.split(',')
                            for btn in buttons:
                                hold_buttons.append(button.split())
                doc = etree.XML(result['arch'])
                header = doc.find(".//header")
                sheet = doc.find(".//sheet")

                if sheet is not None:
                    field = etree.Element("field", name="x_workflow_diagram_config_id", invisible="1")
                    field_1 = etree.Element("field", name="x_workflow_diagram_fields", invisible="1")
                    sheet.append(field)
                    sheet.append(field_1)
                
                if header:
                    for elm in header:
                        items = elm.items()
                        if elm.tag == 'button':
                            button_name = list(filter(lambda x: x[0] == 'name', items))
                            if button_name:
                                button_name = button_name[0][1]
                                if button_name not in hold_buttons:
                                    elm.set('invisible', '1')
                                else:
                                    class_btn = dict(filter(lambda x: x[0] == 'class', items))
                                    if 'class' in class_btn:
                                        elm.set('class', class_btn['class'] + ' d-none')
                                    else:
                                        elm.set('class', 'd-none')
                    # if doc.xpath(self._tier_validation_buttons_xpath):
                    #     for node in doc.xpath(self._tier_validation_buttons_xpath):
                    #         # By default, after the last button of the header
                    #         str_element = self.env["ir.qweb"]._render("workflow_diagram.tier_validation_buttons")
                    #         new_node = etree.fromstring(str_element)
                    #         for new_element in new_node:
                    #             node.addnext(new_element)
                    # else:
                    #     str_element = self.env["ir.qweb"]._render("workflow_diagram.tier_validation_buttons")
                    #     new_node = etree.fromstring(str_element)
                    #     for new_element in new_node:
                    #         header.append(new_element)
                result['arch'] = etree.tostring(doc, encoding='unicode')
        except Exception as e:
            return result
        return result