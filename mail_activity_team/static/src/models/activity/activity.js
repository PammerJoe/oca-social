/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

/*registerClassPatchModel('mail.activity', 'calendar/static/src/models/activity/activity.js', {
    /**
     * @override
     */
    /*convertData(data) {
        const res = this._super(data);
        if ('calendar_event_id' in data) {
            res.calendar_event_id = data.calendar_event_id[0];
        }
        return res;
    },
});*/

registerFieldPatchModel('mail.activity' {
    /**
     * Employee related to this user.
     */
    team_id: many2one('mail.team'),
});
