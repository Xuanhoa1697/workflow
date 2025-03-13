# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

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
# To return list user validate to 'result' variables
# EX: result = record.env.user.ids\n\n\n\n"""


class WorkflowConfigState(models.Model):
    _name = 'workflow.config.state'
    _description = 'Workflow Config State'
    _order = 'sequence asc'

    sequence = fields.Integer()
    name_stage_id = fields.Many2one('name.stage', string='Name Stage')
    name = fields.Char(string=_("State"), store=True)
    code = fields.Char(string='Code')
    workflow_config_id = fields.Many2one('workflow.config', string='Workflow Config', ondelete='cascade')
    model_id = fields.Many2one('ir.model', string=_('Form'), related='workflow_config_id.model_id')
    active = fields.Boolean(string=_('Active'), default=True)
    start_end_cancel_workflow = fields.Selection(
        [('start_workflow', 'Start Workflow'), ('end_workflow', 'End Workflow'),
         ('cancel_workflow', 'Cancel Workflow')], string='Type Stage')
    in_transitions = fields.One2many('workflow.transition', 'act_to_id', string='Incoming Transitions', copy=False, ondelete='cascade')
    out_transitions = fields.One2many('workflow.transition', 'act_from_id', string='Outgoing Transitions', copy=False, ondelete='cascade')
    job_id = fields.Many2one('hr.job', 'Job Position')
    department_id = fields.Many2one('hr.department', string='Department',
                                    help='If you select a department here, it will determine which department the next reviewer belongs to.'
                                         ' If not selected, it will be selected according to the department of the function.')
    fold = fields.Boolean(string='Folded in Kanban',
                          help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_request_to_skip = fields.Boolean(string=_('Request to Skip Button'))
    bpmn_id = fields.Char('BPMN ID')
    color = fields.Char('Color')
    review_type = fields.Selection(
        string="Validated by",
        default="code",
        selection=[
            ("individual", "Specific user"),
            ("group", "Any user in a specific group"),
            ("code", "Code"),
        ],
    )
    reviewer_id = fields.Many2many(comodel_name="res.users", string="Reviewer")
    reviewer_group_id = fields.Many2many(
        comodel_name="res.groups", string="Reviewer group"
    )
    definition_code = fields.Text(default=DEFAULT_PYTHON_CODE)
    before_callback_button = fields.Char('Before Callback Button')
    after_callback_button = fields.Char('After Callback Button')
    to_draft = fields.Boolean(string='To Draft', help='When the workflow is in this state, the record is set to draft.')
    fields_ids = fields.Many2many('ir.model.fields', string='Readonly Field')
    transfer_to_others = fields.Boolean(string='Transfer To Others?')
    additional_signatories  = fields.Boolean(string='Additional Signatories?')

    @api.onchange('start_end_cancel_workflow')
    def _onchange_start_end_cancel_workflow(self):
        if self.start_end_cancel_workflow:
            self.review_type = self.reviewer_id = self.reviewer_group_id = False
            self.definition_code = DEFAULT_PYTHON_CODE

    @api.onchange('review_type')
    def _onchange_review_type(self):
        if self.review_type == 'code':
            self.definition_code = DEFAULT_PYTHON_CODE


    def action_config_workflow(self):
        self.ensure_one()
        view_id = self.env.ref('workflow_diagram.workflow_config_state_form_view')
        return {
            'name': _('Workflow State Configuration'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': view_id.id,
            'target': 'new'
        }
