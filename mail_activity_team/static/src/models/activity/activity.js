/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr, many2one, many2many } from '@mail/model/model_field';

registerFieldPatchModel('mail.activity', 'mail_activity_team/static/src/models/activity.js', {
    /**
     * Employee related to this user.
     */
    team_name: attr(),
    assigned_team_member: attr(),
    team_member_ids: attr(),
});

registerClassPatchModel('mail.activity', 'mail_activity_team/static/src/models/activity.js', {
    /**
     * @override
     */
    convertData(data) {
        const res = this._super(data);
        if ('team_name' in data) {
            res.team_name = data.team_name;
        }
        if ('assigned_team_member' in data) {
            res.assigned_team_member = data.assigned_team_member;
        }
        if ('team_member_ids' in data) {
            res.team_member_ids = data.team_member_ids;
        }
        return res;
    },
});

registerInstancePatchModel('mail.activity', 'mail_activity_team/static/src/models/activity.js', {
    /*
    * Set assigned team member to current user.
    */
    async takeActivity() {
        await this.async(() => this.env.services.rpc({
            model: 'mail.activity',
            method: 'set_assigned_team_member',
            args: [[this.id]],
        }));
    },
});

