# -*- coding: utf-8 -*-

from odoo import fields, api, models, _


class NameStage(models.Model):
    _name = 'name.stage'
    _order = 'id desc'
    _description = 'Name Stage'

    code = fields.Char('Code')
    name = fields.Char('Name')
    model_id = fields.Many2one('ir.model', string='Apply For Model')
