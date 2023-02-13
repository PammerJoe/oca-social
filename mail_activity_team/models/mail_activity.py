# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, _, api, fields, models, exceptions
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    _inherit = "mail.activity"

    assigned_team_member = fields.Many2one(string="Felelős csapattag", comodel_name="res.users")

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            return False
            # user_id = self.env.uid
        res_model = self.env.context.get("default_res_model")
        model = self.sudo().env["ir.model"].search([("model", "=", res_model)], limit=1)
        domain = [("member_ids", "in", [user_id])]
        if res_model:
            domain.extend(
                ["|", ("res_model_ids", "=", False), ("res_model_ids", "in", model.ids)]
            )
        return self.env["mail.activity.team"].search(domain, limit=1)

    team_id = fields.Many2one(
        comodel_name="mail.activity.team", default=lambda s: s._get_default_team_id()
    )
    team_member_ids = fields.Many2many(related='team_id.member_ids')

    @api.onchange("assigned_team_member")
    def _onchange_assigned_team_member(self):
        res = {"domain": {"team_id": []}}
        if not self.assigned_team_member:
            return res
        res["domain"]["team_id"] = [
            "|",
            ("res_model_ids", "=", False),
            ("res_model_ids", "in", self.res_model_id.ids),
        ]
        if self.team_id and self.assigned_team_member in self.team_id.member_ids:
            return res
        self.team_id = self.with_context(
            default_res_model=self.res_model_id.id
        )._get_default_team_id(user_id=self.assigned_team_member.id)
        return res

    @api.onchange("team_id")
    def _onchange_team_id(self):
        res = {"domain": {"user_id": []}}
        if not self.team_id:
            return res
        res["domain"]["user_id"] = [("id", "in", self.team_id.member_ids.ids)]
        if self.assigned_team_member not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.assigned_team_member = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.assigned_team_member = self.team_id.member_ids
            else:
                self.assigned_team_member = self.env["res.users"]
        return res

    @api.constrains("team_id", "assigned_team_member")
    def _check_team_and_user(self):
        for activity in self:
            # SUPERUSER is used to put mail.activity on some objects
            # like sale.order coming from stock.picking
            # (for example with exception type activity, with no backorder).
            # SUPERUSER is inactive and then even if you add it
            # to member_ids it's not taken account
            # To not be blocked we must add it to constraint condition.
            # We must consider also users that could be archived but come from
            # an automatic scheduled activity
            if (
                activity.assigned_team_member.id != SUPERUSER_ID
                and activity.team_id
                and activity.assigned_team_member
                and activity.assigned_team_member
                not in activity.team_id.with_context(active_test=False).member_ids
            ):
                raise ValidationError(
                    _(
                        "The assigned user %(user_name)s is "
                        "not member of the team %(team_name)s.",
                        user_name=activity.assigned_team_member.name,
                        team_name=activity.team_id.name,
                    )
                )

    def activity_format(self):
        objects = super().activity_format()
        for obj in objects:
            if obj['team_id']:
                # record = self.env['mail.activity.team'].sudo().search([('id', '=', obj['team_id'].id)])
                obj['team_name'] = obj['team_id'][1]
                if obj['assigned_team_member']:
                    obj['assigned_team_member'] = obj['assigned_team_member'][1]
            else:
                obj['team_name'] = False
        return objects

    def set_assigned_team_member(self):
        for activity in self:
            activity.assigned_team_member = self.env.user
        return

    # ------------------------------------------------------
    # Notification
    # ------------------------------------------------------

    def action_notify(self):
        if not self:
            return
        original_context = self.env.context
        body_template = self.env.ref('mail.message_activity_assigned')
        for activity in self:
            notified_user = activity.user_id if activity.team_id is False and activity.assigned_team_member is False else activity.assigned_team_member
            notified_users = activity.team_id.member_ids if activity.team_id is True and activity.assigned_team_member is False else None
            if notified_users is not None:
                for user in notified_users:
                    if user != self.env.user:
                        self.send_notification(user, body_template, activity, original_context)
            else:
                if notified_user != self.env.user:
                    self.send_notification(notified_user, body_template, activity, original_context)

    def send_notification(self, notified_user, body_template, activity, original_context):
        if notified_user.lang:
            # Send the notification in the assigned user's language
            self = self.with_context(lang=notified_user.lang)
            body_template = body_template.with_context(lang=notified_user.lang)
            activity = activity.with_context(lang=notified_user.lang)
        model_description = self.env['ir.model']._get(activity.res_model).display_name
        body = body_template._render(
            dict(
                activity=activity,
                model_description=model_description,
                access_link=self.env['mail.thread']._notify_get_action_link('view', model=activity.res_model,
                                                                            res_id=activity.res_id),
            ),
            engine='ir.qweb',
            minimal_qcontext=True
        )
        record = self.env[activity.res_model].browse(activity.res_id)
        if notified_user:
            record.message_notify(
                partner_ids=notified_user.partner_id.ids,
                body=body,
                subject=_('%(activity_name)s: %(summary)s assigned to you',
                          activity_name=activity.res_name,
                          summary=activity.summary or activity.activity_type_id.name),
                record_name=activity.res_name,
                model_description=model_description,
                email_layout_xmlid='mail.mail_notification_light',
            )
        body_template = body_template.with_context(original_context)
        self = self.with_context(original_context)

    def _action_done(self, feedback=False, attachment_ids=None):
        """ Overridden activity done method to send reminders when activity is marked as done. """
        original_context = self.env.context
        body_template = self.env.ref('mail.message_activity_done_notification')
        for activity in self:
            if activity.team_id:
                if activity.assigned_team_member:
                    if activity.assigned_team_member != self.env.user:
                        activity.send_notification(activity.assigned_team_member, body_template, activity, original_context)
            else:
                if activity.user_id != self.env.user:
                    activity.send_notification(activity.user_id, body_template, activity, original_context)
            record = self.env[activity.res_model].browse(activity.res_id)
            if 'responsible_user' in record._fields:
                if record.responsible_user:
                    if record.responsible_user != self.env.user:
                        self.send_notification(record.responsible_user, body_template, activity, original_context)
        result = super(MailActivity, self)._action_done(feedback, attachment_ids)
        return result

    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        activities = super(MailActivity, self).create(vals_list)
        for activity in activities:
            need_sudo = False
            try:
                partner_id = activity.assigned_team_member.partner_id.id
            except exceptions.AccessError:
                need_sudo = True
                partner_id = activity.assigned_team_member.sudo().partner_id.id

            # Send a notificiation to assigned team/team member/user
            # if activity.assigned_team_member != self.env.user:
            if need_sudo:
                activity.sudo().action_notify()
            else:
                activity.action_notify()

            self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[partner_id])
        return activities

    def write(self, values):
        if values.get('assigned_team_member'):
            team_member_changes = self.filtered(lambda activity: activity.assigned_team_member.id != values.get('assigned_team_member'))
            pre_responsibles_team_member = team_member_changes.mapped('assigned_team_member.partner_id')
        res = super(MailActivity, self).write(values)

        if values.get('assigned_team_member'):
            if values['assigned_team_member'] != self.env.uid:
                to_check = team_member_changes.filtered(lambda act: not act.automated)
                to_check._check_access_assignation()
                if not self.env.context.get('mail_activity_quick_update', False):
                    team_member_changes.action_notify()
            for activity in team_member_changes:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.assigned_team_member.partner_id.id])
        return res
