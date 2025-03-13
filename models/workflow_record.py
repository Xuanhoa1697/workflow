# -*- coding: utf-8 -*-

from odoo import fields, api, models, _


class WorkflowRecord(models.Model):
    _name = 'workflow.record'
    _order = 'id desc'

    res_model = fields.Char(string='Record Model')
    res_id = fields.Many2oneReference(string="Approval Name", model_field="res_model")
    workflow_id = fields.Many2one('workflow.config', compute="_compute_workflow_id")
    state = fields.Selection([('to_start', 'To Start'), ('with_draft', 'With Draft'), ('approve', 'Approve'),('cancel', 'Cancel')], compute="_compute_workflow_id")
    history_ids = fields.One2many('approve.history', 'record_id')

    def _compute_workflow_id(self):
        for rec in self:
            active_id = self.env[rec.res_model].browse(rec.res_id)
            history_ids = self.env['approve.history'].search([('res_id', '=', rec.res_id), ('res_model', '=', rec.res_model)])
            rec.workflow_id = active_id.x_workflow_diagram_config_id
            rec.state = history_ids[-1].state if history_ids else False
    
    def action_view_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            'view_mode': 'form'
        }