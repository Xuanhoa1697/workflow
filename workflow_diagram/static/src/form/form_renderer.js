/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onWillStart, onRendered, onWillRender } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { ensureJQuery } from '@web/core/ensure_jquery';

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.fieldNodes = {}
        onWillStart(async () => {
            await ensureJQuery();
        })

        onRendered(async () => {
            if (this.model.root.data && this.model.root.data.x_workflow_diagram_fields) {
                var x_workflow_diagram_fields = this.model.root.data.x_workflow_diagram_fields.split(",");
                for(var i = 0; i < x_workflow_diagram_fields.length; i++) {
                    for (var y = 0; y < 5; y++) {
                        var key_field = x_workflow_diagram_fields[i] + `_${y}`;
                        if (!(key_field in this.fieldNodes) && key_field in this.archInfo.fieldNodes) {
                            this.fieldNodes[key_field] = this.archInfo.fieldNodes[key_field].readonly
                        }
                        if (key_field in this.archInfo.fieldNodes) {
                            this.archInfo.fieldNodes[key_field].readonly = ' True'
                        }
                    }
                    
                }
                
            } 
            
            if(this.model.root.data && 
                'x_workflow_diagram_fields' in this.model.root.data && 
                (this.model.root.data.x_workflow_diagram_fields == '' || !this.model.root.data.x_workflow_diagram_fields)) {
                for(var i in this.fieldNodes) {
                    this.archInfo.fieldNodes[i].readonly = this.fieldNodes[i]
                }
            }
            
            var result = await this.checkApply(); 
            $('.workflow_diagram_button_view').remove();    
            if (!result.is_continue) {
                return
            }

            await this.fetch_data(result.btn_hold);
        });
    },

    async checkApply() {
        var datas = await this.orm.call(
            "workflow.config",
            'check_apply',
            [this.props.resModel, this.model.root.data.x_workflow_diagram_config_id]
        );
        return datas
    },

    async fetch_data(btn_hold) {
        var self = this;
        $('.workflow_diagram_button_view').remove();
        var resId = this.model.root.resId || this.model.root.data.res_id
        if (!resId) return
        var datas = await this.orm.call(
            "workflow.config",
            'get_data_button_header',
            [resId, this.props.resModel,  this.model.root.data.x_workflow_diagram_config_id]
        );
        
        this.props.nameWfl = datas.name
        $('.workflow_diagram_button_view').remove();
        btn_hold.forEach(element => {
            $(`button[name=${element}]`).removeClass('d-none');
        });
        // if (!datas.is_apply) return
        if ($('.o_statusbar_buttons ').length === 0) {
            setTimeout(() => {
                self.appendButton(datas, btn_hold)
            }, 2000);
        } else {
            self.appendButton(datas, btn_hold)
        }
        
    },

    appendButton(datas, btn_hold) {
        $('.workflow_diagram_button_view').remove();
        const elm = renderToElement("workflow_diagram.workflow_diagram_button_view", {
            nameWfl: datas.name,
            env: this,
            isStart: datas.isStart,
            isProgress: datas.isProgress,
            withDraft: datas.withDraft,
            withCancel: datas.withCancel,
            isEnd: datas.isEnd,
            isTransferToOthers: datas.isTransferToOthers,
            isAdditionalSignatories: datas.isAdditionalSignatories,
            isOption: datas.isTransferToOthers && datas.isAdditionalSignatories,
            is_apply: datas.is_apply
        });
        $('.o_statusbar_buttons ').prepend(elm);
    },

    async applyDiagram(type=false) {
        const context = {
            'default_res_model': this.props.resModel,
            'default_res_id': this.model.root.resId,
            'default_state': type,
            'default_workflow_id': this.model.root.data.x_workflow_diagram_config_id[0]
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "approve.history",
            views: [[false, "form"]],
            context: context,
            target: "new",
            name: "Approve"
        }, {
            onClose: async () => {
                await this.model.load()
            }
        })
    },  

    async applyTransferDiagram(type) {
        var last_history_id = await this.orm.call("approve.history", 'transfer_to_user', [this.model.root.resId, this.props.resModel])
        const context = {
            'is_transfer': type == 'is_transfer',
            'is_additional_signatories': type === 'is_additional_signatories'
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "approve.history",
            res_id: last_history_id,
            views: [[false, "form"]],
            context: context,
            target: "new",
            name: "Transfer"
        }, {
            onClose: async () => {
                await this.model.load()
            }
        })
    },  

    diagramPreview() {
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'workflow_diagram_preview',
            name: _t('Workflow'),
            target: 'new',
            context: {
                'res_model': this.props.resModel,
                'res_id': this.model.root.resId
            }
        });
    }
});