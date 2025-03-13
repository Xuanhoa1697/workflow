# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

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
# To return list user validate to result
# EX: result = record.env.user.ids\n\n\n\n"""

class WorkflowConfig(models.Model):
    _name = 'workflow.config'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Workflow Config'
    _order = 'id desc'

    code = fields.Char(string=_("Code"))
    name = fields.Char(string=_('Workflow Name'))
    active = fields.Boolean(string=_('Active'), default=True)
    model_id = fields.Many2one('ir.model', string=_('Form'))
    model = fields.Char(string=_('Form Name'))
    is_conditional = fields.Boolean(string=_('Conditional?'), default=False)
    domain = fields.Char(string=_('Domain'), default='[]')
    description = fields.Char(string=_('Description'))
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    workflow_config_state_ids = fields.One2many('workflow.config.state', 'workflow_config_id',
                                                string='Workflow Config States', copy=True)
    origin_id = fields.Integer('Origin ID')
    bpmnio_xml = fields.Char()
    state = fields.Selection([('draft', 'Draft'), ('in_use', 'In Use'), ('obsolute', 'Obsolete')], default="draft")
    submit_reason = fields.Boolean('Submit Reason')
    request_email = fields.Boolean('Request Email')
    approval_submitter_ids = fields.Many2many('res.users', 'res_users_workflow_config_rel', string='Approval Submitter', compute="_compute_approval_submitter", store=True)
    hold_buttons = fields.Char(string='Hold Button', help="Hold Button")
    fields_id = fields.Many2one('ir.model.fields', string='Workflow Config', ondelete='cascade')
    fields_readonly_id = fields.Many2one('ir.model.fields', string='Workflow Field', ondelete='cascade')
    
    @api.depends('state')
    def _compute_approval_submitter(self):
        for rec in self:
            default_create_user = rec.create_uid
            if rec.state == 'in_use':
                default_create_user |= self.env.user
            rec.approval_submitter_ids = default_create_user.ids

    @api.onchange('model_id')
    def onchange_mode_id(self):
        if self.model_id:
            self.model = self.model_id.model

    @api.model
    def create(self, vals):
        res = super(WorkflowConfig, self).create(vals)
        res._create_fields()
        return res
    
    def _create_fields(self):
        env_sudo = self.env['ir.model.fields'].sudo()
        fields_id = env_sudo.search([('model_id', '=', self.model_id.id), ('name', '=', 'x_workflow_diagram_config_id')])
        fields_readonly_id = env_sudo.search([('model_id', '=', self.model_id.id), ('name', '=', 'x_workflow_diagram_fields')])
        if not fields_id:
            field_name = env_sudo.search([('model_id', '=', self.model_id.id)]).mapped('name')
            field_name.remove("id")
            fields_id = env_sudo.create({
                'name': 'x_workflow_diagram_config_id',
                'ttype': 'many2one',
                'relation': self._name,
                'on_delete': 'cascade',
                'model_id': self.model_id.id,
                'compute': "for rec in self:\n    rec['x_workflow_diagram_config_id'] = rec.env['workflow.config'].sudo().get_wfl_cf(rec)",
                'store': True,
                'depends': ','.join(field_name)
            })

            fields_readonly_id = env_sudo.create({
                'name': 'x_workflow_diagram_fields',
                'ttype': 'char',
                'model_id': self.model_id.id,
                'compute': "for rec in self:\n    rec['x_workflow_diagram_fields'] = rec.env['workflow.config'].sudo().get_wfl_field_readonly(rec)",
                'depends': ','.join(field_name),
                'store': True,
            })
        self.fields_id = fields_id.id
        self.fields_readonly_id = fields_readonly_id
    
    def unlink(self):
        env_sudo = self.env['ir.model.fields'].sudo()
        fields_id = env_sudo.search([('model_id', '=', self.model_id.id), ('name', '=', 'x_workflow_diagram_config_id')])
        fields_readonly_id = env_sudo.search([('model_id', '=', self.model_id.id), ('name', '=', 'x_workflow_diagram_fields')])
        fields_id.unlink()
        fields_readonly_id.unlink()
        return super(WorkflowConfig, self).unlink()
    
    def get_wfl_field_readonly(self, rec):
        fields_ids = ''
        if not rec.id:
            return ''
        history_ids = self.env['approve.history'].search([('res_id', '=', rec.id), ('res_model', '=', rec._name)])
        if history_ids:
            last_history_id = history_ids[-1]
            if last_history_id.state_to_id.fields_ids:
                fields_ids = last_history_id.state_to_id.fields_ids.mapped('name')
                fields_ids = ','.join(fields_ids)
        return fields_ids

    def get_wfl_cf(self, rec):
        wfl_id = False
        if not rec.id:
            return wfl_id
        
        workflow_ids = self.sudo().search([('model', '=', rec._name), ('state', '=', 'in_use')])
        active_id = self.env[rec._name].browse(rec.id)
        for workflow in workflow_ids:
            domain = [('id', '=', rec.id)]
            if workflow.domain:
                domain = eval(workflow.domain)
                domain.append(('id', '=', rec.id))
            current_id = self.env[rec._name].search(domain)
            if current_id == active_id:
                wfl_id = workflow
                break
        if wfl_id:
            return wfl_id.id
        else:
            return wfl_id
        


    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + ' (copy)'
        default['origin_id'] = self.id
        new_record = super(WorkflowConfig, self).copy(default=default)
        new_record._set_transitions_line(self)
        return new_record

    def _set_transitions_line(self, record):
        for line in self.workflow_config_state_ids:
            old_line =  record.workflow_config_state_ids.filtered(lambda x: x.sequence == line.sequence and x.name == line.name)[0]
            if not old_line: continue
            for in_transition in old_line.in_transitions:
                old_act_from_id = in_transition.act_from_id
                act_from_id = self.workflow_config_state_ids.filtered(lambda x: x.sequence == old_act_from_id.sequence and x.name == old_act_from_id.name)[0]
                if not act_from_id: continue
                act_exist_id = line.in_transitions.filtered(lambda x: x.domain == in_transition.domain and x.act_to_id.id == line.id and x.act_from_id.id == act_from_id.id)
                if not act_exist_id:
                    in_transition.copy({
                        'act_to_id': line.id,
                        'act_from_id': act_from_id.id,
                        'workflow_config_id': self.id,
                    })
            for out_transition in old_line.out_transitions:
                old_act_to_id = out_transition.act_to_id
                act_to_id = self.workflow_config_state_ids.filtered(lambda x: x.sequence == old_act_to_id.sequence and x.name == old_act_to_id.name)[0]
                if not act_to_id: continue
                act_exist_id = line.out_transitions.filtered(lambda x: x.domain == out_transition.domain and x.act_from_id.id == line.id and x.act_to_id.id == act_to_id.id)
                if not act_exist_id:
                    out_transition.copy({
                        'act_from_id': line.id,
                        'act_to_id': act_to_id.id,
                        'workflow_config_id': self.id,
                    })

    def _check_exist_record(self):
        if self.model_id and self.model:
            record_ids = self.env[self.model].search(
                [('workflow_config_id', '!=', False), ('is_start_workflow', '=', False),
                 ('is_end_workflow', '=', False),
                 ('is_cancel_workflow', '=', False)])
            if record_ids:
                raise ValidationError(_('Invalid related record, please check again before changing workflow config.'))

    def action_config_workflow(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'workflow_diagram_view',
            'context': {
                'active_id': self.id,
                'editMode': self.state == 'draft'
            }
        }
    
    def get_data_workflow_diagrams(self):
        self = self.sudo()
        workflow_config_state_ids = { i.bpmn_id: {
            'id': i.id,
            'name': i.name,
            'color': i.color,
            'position_workflow': list(filter(lambda x: x[0] == i.start_end_cancel_workflow, i._fields['start_end_cancel_workflow'].selection))[0][1] if i.start_end_cancel_workflow else False,
            'position_workflow_type': i.start_end_cancel_workflow
        } for i in self.workflow_config_state_ids}

        workflow_transitions_state_ids = { i.bpmn_id: {
            'id': i.id,
            'name': i.name,
        } for i in self.workflow_config_state_ids.out_transitions}


        return {
            'name': self.name,
            'is_edit': self.create_uid.id == self.env.user.id,
            'bpmnio_xml': self.bpmnio_xml,
            'workflow_config_state_ids': workflow_config_state_ids,
            'workflow_transitions_state_ids': workflow_transitions_state_ids
        }
    
    @api.model
    def check_apply(self, resModel, wfl_id):
        if not wfl_id:
            return {
                'is_continue': False,
                'btn_hold': []
            }
        workflow_id = self.sudo().browse(int(wfl_id[0]))

        return {
            'is_continue': True if workflow_id else False,
            'btn_hold': workflow_id.hold_buttons.split(',') if workflow_id.hold_buttons else []
        }

    @api.model
    def get_data_button_header(self, resId, resModel, wfl_id):
        workflow_id = self.sudo().browse(wfl_id[0])
        history_ids = self.env['approve.history'].search([('res_id', '=', resId), ('res_model', '=', resModel)])
        active_id = self.env[resModel].browse(resId)
        record_id = self.env['workflow.record'].sudo().search([('res_model', '=', resModel), ('res_id', '=', resId)])
        if not record_id:
            self.env['workflow.record'].sudo().create({
                'res_model': resModel,
                'res_id': resId
            })
        domain = [('id', '=', resId)]
        if workflow_id.domain:
            domain = eval(workflow_id.domain)
            domain.append(('id', '=', resId))
        current_id = self.env[resModel].search(domain)

        user_ids = [] if history_ids else self.env.user.search([]).ids
        transfer_user_ids = []
        additional_signatories_user_ids = []
        is_apply_btn = True
        if history_ids:
            last_history = history_ids[-1]
            transfer_user_ids = last_history.transfer_user_ids.ids
            additional_signatories_user_ids = last_history.additional_signatories_user_ids.ids
            state_id = last_history.state_id
            state_to_id = last_history.state_to_id
            user_ids += last_history.user_ids.ids
            if state_to_id.start_end_cancel_workflow == 'start_workflow' or state_to_id.start_end_cancel_workflow == 'cancel_workflow':
                user_ids = active_id.create_uid.ids
            if state_to_id.start_end_cancel_workflow == 'end_workflow':
                user_ids = history_ids.mapped('user_id').ids + history_ids.mapped('user_ids').ids
            if state_to_id.review_type == 'individual':
                user_ids = state_to_id.reviewer_id.ids
            if state_to_id.review_type == 'group':
                user_ids = state_to_id.reviewer_group_id.mapped('users').ids
            if state_to_id.review_type == 'code':
                localdict = {
                    'record': active_id,
                    'result': []
                }
                safe_eval(state_to_id.definition_code, localdict, mode="exec", nocopy=True)
                if 'result' in localdict:
                    user_ids = localdict.get('result', [])
            
        option_all_user_ids = transfer_user_ids + additional_signatories_user_ids
        if option_all_user_ids:
            is_apply_btn = self.env.user.id in option_all_user_ids
                
        return {
            'name': workflow_id.name,
            'is_apply': True if current_id in active_id and self.env.user.id in user_ids and is_apply_btn else False,
            'workflow_id': workflow_id.id,
            'isStart': True if not history_ids or (len(history_ids) > 1 and history_ids[-1].state_to_id.start_end_cancel_workflow == 'start_workflow') else False,
            'isProgress': True if history_ids and \
                not history_ids[-1].state_to_id.start_end_cancel_workflow else False,
            'isEnd': True if history_ids and \
                history_ids[-1].state_to_id.start_end_cancel_workflow == 'end_workflow' else False,
            'withDraft': True if history_ids and history_ids[-1].state_to_id.to_draft else False,
            'withCancel': True if workflow_id.workflow_config_state_ids.filtered(lambda x: x.start_end_cancel_workflow == 'cancel_workflow') else False,
            'isTransferToOthers': history_ids[-1].state_to_id.transfer_to_others and not option_all_user_ids if history_ids else False,
            'isAdditionalSignatories': history_ids[-1].state_to_id.additional_signatories and not option_all_user_ids if history_ids else False
        }