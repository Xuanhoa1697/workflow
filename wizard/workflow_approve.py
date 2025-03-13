# -*- coding: utf-8 -*-


from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class WorkflowApprove(models.TransientModel):
    _name = 'workflow.approve'
    _description = 'Workflow Approve'
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

    note = fields.Text('Note')
    res_id = fields.Integer(string="Record id of Model")
    res_model = fields.Char(string="Model")
    employee_ids = fields.Many2many('hr.employee', 'workflow_approve_employee_rel', 'workflow_approve_id',
                                    'employee_id', string='Employee')
    mail_template_id = fields.Many2one('mail.template', string=_(
        'Mail Template'), domain="[('model', '=', res_model)]")
    transition_id = fields.Many2one(
        'workflow.transition', string='Transition', domain="[('model', '=', res_model)]")
    employee_id = fields.Many2one('hr.employee', string='Employee')

    def _get_hr_employee(self):
        return []
        # return self.env.ref('hr.group_hr_user').users.mapped('partner_id').ids
         

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
        users_hr_ids = self._get_hr_employee()
        if users_hr_ids:
            partner_ids.extend(users_hr_ids)
        #####
        content_email = mail_template_id.with_context(note=self.note)._generate_template(
            [res_id], self._MAIL_TEMPLATE_FIELDS)
        email = self.env['ir.mail_server'].sudo().search([], limit=1)
        context = self.env.context.copy()
        if 'default_res_id' in context:
            del context['default_res_id']
        self.env.context = context
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

    def action_confirm(self):
        object_id = self.env[self.res_model].browse(int(self.res_id))
        transition_type = self._context.get('default_transition_type')
        emp_id = self.env.user.employee_id
        user_ids = self.employee_ids.mapped('user_id')

        if transition_type != 'refuse':
            employee_id = object_id._get_field_employee()
            if employee_id and employee_id.user_id:
                user_ids += employee_id.user_id
        self._send_email(user_ids)

        if not object_id:
            return

        old_state = object_id.stage_id.name
        new_state = self.transition_id.act_to_id.name

        #Luong tu choi se gui thong bao den nhung nguoi da duyet
        if transition_type == 'refuse':
            user_ids = False
            if object_id.fields_get(['approver_employee_ids']):
                user_ids = object_id.approver_employee_ids.mapped('user_id')
            if not user_ids and object_id.fields_get(['approver_ids']):
                user_ids = object_id.approver_ids.mapped('employee_id.user_id')
            if user_ids:
                self._send_email(user_ids)

        object_id._refresh_approver_signature(object_id.stage_id, self.transition_id.act_to_id)
        object_id._refresh_approve_replacement(object_id.stage_id, self.transition_id.act_to_id)

        if transition_type == 'send':
            object_id._add_approver_signature(emp_id.id, object_id.stage_id, self.transition_id.act_to_id)

        act = object_id._add_approver(emp_id.id, self.note, old_state, new_state)
        object_id.stage_id = self.transition_id.act_to_id.id
        object_id.emp_current_approve_ids = self.employee_ids
        getattr(object_id, '_update_extra_%s' %transition_type)()

        return act

    def action_request(self):
        Obj = self.env[self.res_model]
        object_id = Obj.browse(int(self.res_id))
        emp_id = self.env.user.employee_id
        user_ids = self.employee_id.mapped('user_id')
        self._send_email(user_ids)
        transition_type = 'request'
        if object_id:
            object_id.emp_current_approve_ids = [(4, self.employee_id.id)]
            object_id._add_approve_replacement(emp_id, self.employee_id)
            getattr(object_id, '_update_extra_%s' %transition_type)()
