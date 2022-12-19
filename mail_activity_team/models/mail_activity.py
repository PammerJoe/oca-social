# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    assigned_team_member = fields.Many2one(string="Felelős csapattag", comodel_name="res.users",
                                          domain=lambda self: self._get_domain_assigned_team_member())

    def _get_domain_assigned_team_member(self):
        domain = [('id', 'in', self.team_member_ids.ids)]
        return domain

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
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
    team_member_ids = fields.Many2many(related='team_id.member_ids', string="Team Members",)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        res = {"domain": {"team_id": []}}
        if not self.user_id:
            return res
        res["domain"]["team_id"] = [
            "|",
            ("res_model_ids", "=", False),
            ("res_model_ids", "in", self.res_model_id.ids),
        ]
        if self.team_id and self.user_id in self.team_id.member_ids:
            return res
        self.team_id = self.with_context(
            default_res_model=self.res_model_id.id
        )._get_default_team_id(user_id=self.user_id.id)
        return res

    @api.onchange("team_id")
    def _onchange_team_id(self):
        res = {"domain": {"user_id": []}}
        if not self.team_id:
            return res
        res["domain"]["user_id"] = [("id", "in", self.team_id.member_ids.ids)]
        if self.user_id not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.user_id = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.user_id = self.team_id.member_ids
            else:
                self.user_id = self.env["res.users"]
        return res

    @api.constrains("team_id", "user_id")
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
                activity.user_id.id != SUPERUSER_ID
                and activity.team_id
                and activity.user_id
                and activity.user_id
                not in activity.team_id.with_context(active_test=False).member_ids
            ):
                raise ValidationError(
                    _(
                        "The assigned user %(user_name)s is "
                        "not member of the team %(team_name)s.",
                        user_name=activity.user_id.name,
                        team_name=activity.team_id.name,
                    )
                )

    def activity_format(self):
        objects = super().activity_format()
        for obj in objects:
            if obj['team_id']:
                # record = self.env['mail.activity.team'].sudo().search([('id', '=', obj['team_id'].id)])
                obj['team_name'] = obj['team_id'][1]
                if obj['assigned_team_member'] is not False:
                    obj['assigned_team_member'] = obj['assigned_team_member'][1]
        return objects

    def set_assigned_team_member(self):
        for activity in self:
            activity.assigned_team_member = self.env.user
        return
