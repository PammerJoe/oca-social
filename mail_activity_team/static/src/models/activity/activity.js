/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.activity', 'mail_activity_team/static/src/models/activity.js', {
    /**
     * Employee related to this user.
     */
    team_name: attr(),
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
        return res;
    },
});

