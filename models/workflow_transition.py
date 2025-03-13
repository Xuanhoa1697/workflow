# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

DEFAULT_PYTHON_CODE = """# Available variables:
#  - env: environment on which the action is triggered
#  - model: model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: utility function to compare floats based on specific precision
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - _logger: _logger.info(message): logger to emit messages in server logs
#  - UserError: exception class for raising user-facing warning messages
#  - Command: x2many commands namespace
# To return value to 'result' variables
# EX: result = True\n\n\n\n"""


class WorkflowTransition(models.Model):
    _name = 'workflow.transition'
    _description = 'Workflow Transition'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')

    workflow_config_id = fields.Many2one('workflow.config', compute='_compute_workflow_config',
                                         string='Workflow Config', store=True)
    is_conditional = fields.Boolean(string=_('Conditional?'), default=False)
    model_id = fields.Many2one('ir.model', compute='_compute_model', string='Model', store=True)
    model = fields.Char(compute='_compute_model', string='Model Name', store=True)
    domain = fields.Char(string=_('Domain'), default='[]')
    act_from_id = fields.Many2one('workflow.config.state', string='Source Stage', required=True, ondelete='cascade')
    act_to_id = fields.Many2one('workflow.config.state', string='Destination Stage', required=True, ondelete='cascade')
    list_stage_ids = fields.Many2many('workflow.config.state', string='List Stage')
    mail_template_id = fields.Many2one('mail.template', string=_('Mail Template'), domain="[('model', '=', model)]",
                                       help="If set an email will be sent to the customer when the task or issue reaches this step.")
    is_transition_cancel = fields.Boolean('Is Transition Cancel', default=False)
    transition_type = fields.Selection([('send', 'Send'), ('cancel', 'Cancel'), ('return', 'Return'), ('refuse', 'Refuse')],
                                       string='Transition Type', default='send')
    bpmn_id = fields.Char('BPMN ID')
    review_type = fields.Selection(
        string="Transaction Type",
        default="domain",
        selection=[
            ("domain", "Domain"),
            ("code", "Code"),
        ],
    )
    definition_code = fields.Text(default=DEFAULT_PYTHON_CODE)

    @api.onchange('review_type')
    def _onchange_review_type(self):
        if self.review_type == 'code':
            self.definition_code = DEFAULT_PYTHON_CODE

    @api.depends('act_from_id',
                 'act_from_id.workflow_config_id',
                 'act_to_id',
                 'act_to_id.workflow_config_id')
    def _compute_workflow_config(self):
        for item in self:
            item.workflow_config_id = False
            if item.act_from_id or item.act_to_id:
                wkf_config_stage_id = item.act_from_id or item.act_to_id
                if wkf_config_stage_id and wkf_config_stage_id.workflow_config_id:
                    item.workflow_config_id = wkf_config_stage_id.workflow_config_id.id

    @api.depends('workflow_config_id',
                 'workflow_config_id.model_id',
                 'workflow_config_id.model')
    def _compute_model(self):
        for item in self:
            item.model = ''
            item.model_id = False
            if item.workflow_config_id:
                item.model_id = item.workflow_config_id.model_id.id
                item.model = item.workflow_config_id.model
