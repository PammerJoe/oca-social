/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { insert, unlink } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Team extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @returns {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            if ('team_id' in data) {
                if (!data.team_id) {
                    data2.team = unlink();
                } else {
                    const teamNameGet = data['team_id'];
                    const teamData = {
                        display_name: teamNameGet[1],
                        id: teamNameGet[0],
                    };
                    data2.team = insert(teamData);
                }
            }
            return data2;
        }

        /**
         * Performs the `read` RPC on `mail.activity.team`.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        static async performRpcRead({ context, fields, ids }) {
            const teamsData = await this.env.services.rpc({
                model: 'mail.activity.team',
                method: 'read',
                args: [ids],
                kwargs: {
                    context,
                    fields,
                },
            }, { shadow: true });
            return this.messaging.models['mail.team'].insert(teamsData.map(teamData =>
                this.messaging.models['mail.team'].convertData(teamData)
            ));
        }

        /**
         * Fetches the teams.
         */
        async fetchAndUpdate() {
//            return this.messaging.models['mail.team'].performRpcRead({
//                ids: [this.id],
//                fields: ['team_id'],
//                context: { active_test: false },
//            });
            const [data] = await this.async(() => this.env.services.rpc({
                model: 'mail.activity.team',
                method: 'activity_format',
                args: [this.id],
            }, { shadow: true }));
            let shouldDelete = false;
            if (data) {
                this.update(this.constructor.convertData(data));
            } else {
                shouldDelete = true;
            }
//            this.thread.refreshActivities();
//            this.thread.refresh();
            if (shouldDelete) {
                this.delete();
            }
        }


        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.display_name || "Ismeretlen";
        }

        /**
         * @private
         * @returns {string|undefined}
         */
//        _computeNameOrDisplayName() {
//            return this.partner && this.partner.nameOrDisplayName || this.display_name;
//        }
    }

    Team.fields = {
        id: attr({
            readonly: true,
            required: true,
        }),
        display_name: attr({
            compute: '_computeDisplayName',
        }),
        model: attr({
            default: 'mail.activity.team',
        }),
    };
    Team.identifyingFields = ['id'];
    Team.modelName = 'mail.team';

    return Team;
}

registerNewModel('mail.team', factory);
