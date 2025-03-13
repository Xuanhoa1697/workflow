# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.tools.safe_eval import safe_eval
_MAIL_TEMPLATE_FIELDS = ['attachment_ids',
                            'body_html',
                            'subject',
                            'email_cc',
                            'email_from',
                            'email_to',
                            'partner_to',
                            'report_template_ids',
                            'reply_to',
                            'scheduled_date',
                            ]


class ApproveHistory(models.Model):
    _name = 'approve.history'
    _description = 'HMV Approve History'

    user_id = fields.Many2one('res.users', string='Approver', default=lambda self: self.env.user)
    workflow_id = fields.Many2one('workflow.config')
    state_id = fields.Many2one('workflow.config.state', 'Status From', compute='_compute_state', store=True)
    state_to_id = fields.Many2one('workflow.config.state', 'Status To', compute='_compute_state', store=True)
    approve_date = fields.Datetime('Approve Date', default=fields.Datetime.now())
    comment = fields.Text('Comment')

    res_id = fields.Integer('res_id')
    res_model = fields.Char('res_model')
    ref_id = fields.Many2oneReference(string="Approval Name", model_field="res_model")
    mail_template_id = fields.Many2one('mail.template', string=_(
        'Mail Template'), domain="[('model', '=', res_model)]")
    
    is_required_comment = fields.Boolean('Required Comment', compute='_compute_is_required_comment')
    is_required_email = fields.Boolean('Required Email', compute='_compute_is_required_comment')
    state = fields.Selection([('to_start', 'To Start'), ('with_draft', 'With Draft'), ('approve', 'Approve'),('cancel', 'Cancel')])
    user_ids = fields.Many2many('res.users', 'approve_history_user_rel', compute='_compute_user_ids', store=True, string='List Users Approve')
    transfer_user_ids = fields.Many2many('res.users', 'approve_history_transfer_user_rel', string='Transfer To Others')
    additional_signatories_user_ids = fields.Many2many('res.users', 'approve_history_additional_user_rel', string='Additional Signatories')

    record_id = fields.Many2one('workflow.record', string="Record Id", compute="_compute_record_id", store=True)

    @api.depends('res_id', 'res_model')
    def _compute_record_id(self):
        for rec in self:
            rec.record_id = self.env['workflow.record'].sudo().search([('res_model', '=', rec.res_model), ('res_id', '=', rec.res_id)])
            

    @api.depends('state_to_id', 'transfer_user_ids', 'additional_signatories_user_ids')
    def _compute_user_ids(self):
        for rec in self:
            rec.user_ids = rec._get_user_approve()
    
    def _get_user_approve(self):
        rec = self
        user_ids = []
        active_id = rec.env[rec.res_model].browse(rec.res_id)
        if rec.state_to_id.start_end_cancel_workflow == 'start_workflow':
            rec.user_ids = active_id.create_uid.ids
        
        if not rec.state_to_id.start_end_cancel_workflow:
            
            if rec.state_to_id.review_type == 'individual':
                user_ids = rec.state_to_id.reviewer_id.ids
            if rec.state_to_id.review_type == 'group':
                user_ids = rec.state_to_id.reviewer_group_id.mapped('users').ids
            if rec.state_to_id.review_type == 'code':
                localdict = {
                    'record': active_id,
                    'result': []
                }
                safe_eval(rec.state_to_id.definition_code, localdict, mode="exec", nocopy=True)
                if 'result' in localdict:
                    user_ids = localdict.get('result', [])
        if rec.transfer_user_ids or rec.additional_signatories_user_ids:
            user_ids = rec.transfer_user_ids + rec.additional_signatories_user_ids
        
        return user_ids

    @api.depends('res_id', 'res_model', 'state')
    def _compute_state(self):
        for rec in self:
            start_state_id = False
            history_ids = self.env['approve.history'].search([('res_id', '=', rec.res_id), ('res_model', '=', rec.res_model)])
            if rec.state == 'to_start':
                start_state_id = self.env['workflow.config.state'].sudo().search([('workflow_config_id', '=', rec.workflow_id.id), ('start_end_cancel_workflow', '=', 'start_workflow')], limit=1) 
            if rec.state == 'approve' or rec.state == 'cancel':
                if rec.id:
                    history_ids = history_ids - rec
                start_state_id = history_ids[-1].state_to_id
            if rec.state == 'with_draft':
                if rec.id:
                    history_ids = history_ids - rec
                start_state_id = history_ids[-1].state_to_id
            rec.state_id = start_state_id
            rec.state_to_id = rec._get_state_to()
    
    def _get_state_to(self):
        active_id = self.env[self.res_model].browse(self.res_id)
        state_id = False
        for transition in self.state_id.out_transitions:
            if self.state == 'with_draft':
                if transition.act_to_id.start_end_cancel_workflow == 'start_workflow':
                    state_id = transition.act_to_id.id
                    break
                continue
            
            if self.state == 'cancel':
                if transition.act_to_id.start_end_cancel_workflow == 'cancel_workflow':
                    state_id = transition.act_to_id.id
                    break
                continue
            if transition.review_type == 'domain':
                domain = eval(transition.domain)
                record_ids = self.env[self.res_model].search(domain)
                if active_id in record_ids:
                    state_id = transition.act_to_id.id
                    break
            
            if transition.review_type == 'code':
                localdict = {
                    'record': active_id,
                    'result': []
                }
                safe_eval(transition.definition_code, localdict, mode="exec", nocopy=True)
                if 'result' in localdict and localdict.get('result'):
                    state_id = transition.act_to_id.id
                    break

        return state_id

    @api.depends('workflow_id')
    def _compute_is_required_comment(self):
        for rec in self:
            rec.is_required_comment = rec.workflow_id.submit_reason
            rec.is_required_email = rec.workflow_id.request_email

    @api.model
    def create(self, vals):
        res = super(ApproveHistory, self).create(vals)
        res.action_confirm()
        res.action_create_activity()
        res.ref_id = res.res_id
        return res

    def action_create_activity(self):
        to_do_id = self.env.ref('mail.mail_activity_data_todo')
        active_id = self.env[self.res_model].browse(self.res_id)
        user_ids = self._get_user_approve()
        for user_id in user_ids:
            active_id.activity_schedule(
                activity_type_id=to_do_id.id,  # Loại activity
                summary=f"Approval: {active_id.name}",
                note=self.comment,
                user_id=user_id,
                date_deadline=fields.Date.today() + timedelta(days=3)  # Hạn chót sau 3 ngày
            )
    
    def action_confirm(self):
        if self.state_to_id and self.state_to_id.before_callback_button:
            active_id = self.env[self.res_model].browse(self.res_id)
            if hasattr(active_id, self.state_to_id.before_callback_button):
                getattr(active_id, self.state_to_id.before_callback_button)()
        
        if self.state_to_id and self.state_to_id.after_callback_button:
            active_id = self.env[self.res_model].browse(self.res_id)
            if hasattr(active_id, self.state_to_id.after_callback_button):
                getattr(active_id, self.state_to_id.after_callback_button)()
        if self.mail_template_id:
            active_id = self.env[self.res_model].browse(int(self.res_id))
            user_ids = False
            if self.state_to_id.start_end_cancel_workflow == 'start_workflow':
                user_ids = self.env['approve.history'].search([('res_id', '=', self.res_id), ('res_model', '=', self.res_model)]).mapped('user_id') - self.env.user
            else:
                if self.state_to_id.review_type == 'individual':
                    user_ids = self.state_to_id.reviewer_id.ids
                if self.state_to_id.review_type == 'group':
                    user_ids = self.state_to_id.reviewer_group_id.mapped('users').ids
                if self.state_to_id.review_type == 'code':
                    localdict = {
                        'record': active_id,
                        'result': []
                    }
                    safe_eval(self.state_to_id.definition_code, localdict, mode="exec", nocopy=True)
                    if 'result' in localdict:
                        user_ids = localdict.get('result', [])
            self._send_email(user_ids)
    
    def _send_email(self, user_ids):
        mail_servers = self.env['ir.mail_server'].sudo().search([], order='sequence, id')
        if not mail_servers:
            return
        if not user_ids:
            ValidationError(
                _('The employee does not have an account on the system.'))
        mail_template_id = self.mail_template_id
        if not mail_template_id:
            return
        res_id = self.res_id
        res_model = self.res_model
        partner_ids = user_ids.mapped('partner_id').ids
        # Gửi mail cho toan bọ phòng HR
        content_email = mail_template_id.with_context(note=self.comment)._generate_template(
            [res_id], self._MAIL_TEMPLATE_FIELDS)
        email = self.env['ir.mail_server'].sudo().search([], limit=1)
        kwargs = {
            'partner_ids': list(set(partner_ids)),
            'model': res_model,
            'res_ids': [res_id],
            'message_type': 'comment',
            'composition_mode': 'comment',
            'subject': content_email[res_id]['subject'],
            'body': content_email[res_id]['body_html']
        }
        if len(email) > 0:
            email_from = email.smtp_user
            kwargs.update({'email_from': email_from})
        # Create the composer
        composer = self.env['mail.compose.message'].create(kwargs)
        composer.partner_ids = partner_ids
        composer.action_send_mail()

    @api.model
    def get_histoty(self, resId, resModel):
        option_fields = ['transfer_user_ids', 'additional_signatories_user_ids', 'user_ids']
        history_ids = self.sudo().search_read([('res_id', '=', resId), ('res_model', '=', resModel)])
        for history in history_ids:
            for field in option_fields:
                datas = []
                for transfer in history[field]:
                    transfer_user_id = self.env.user.browse(transfer)
                    datas.append([transfer, transfer_user_id.name])
                history[field] = datas
        return history_ids
    
    @api.model
    def transfer_to_user(self, resId, resModel):
        last_history_id = False
        history_ids = self.sudo().search([('res_id', '=', resId), ('res_model', '=', resModel)])
        if history_ids:
            last_history_id = history_ids[-1].id
        return last_history_id