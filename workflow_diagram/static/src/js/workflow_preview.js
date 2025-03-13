/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, onMounted, onPatched, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WorkflowPreview extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.res_id = this.props.action.context.res_id;
        this.res_model = this.props.action.context.res_model;
        onWillStart(async () => {
            await this.fetch_datas()
        })

        onMounted(async () => {
            $('.modal-dialog-centered').addClass('modal-xl')
        })
    }

    async fetch_datas() {
        this.history_ids =  await this.orm.call(
            "approve.history",
            'get_histoty',
            [this.res_id, this.res_model],
            {}
        );
        if (this.history_ids.length > 0) {
            var last_history = {...this.history_ids[this.history_ids.length - 1], isLastApprove: true, id: this.history_ids[this.history_ids.length - 1].id++};
            this.history_ids.push(last_history)
        }
    }
}
WorkflowPreview.props = {
  action: Object,
  actionId: { type: Number, optional: true },
  fcy: { type: String, optional: true },
//   updateActionState: { type: Function, optional: true },
};
WorkflowPreview.template = "workflow_diagram.workflow_diagram_preview"
registry.category("actions").add("workflow_diagram_preview", WorkflowPreview);