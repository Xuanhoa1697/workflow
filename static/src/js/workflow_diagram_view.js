/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, onMounted, onPatched, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { ensureJQuery } from '@web/core/ensure_jquery';

var templates_xml = `<?xml version="1.0" encoding="UTF-8"?>
  <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI" xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="sid-38422fae-e03e-43a3-bef4-bd33b32041b2" targetNamespace="http://bpmn.io/bpmn" exporter="bpmn-js (https://demo.bpmn.io)" exporterVersion="6.1.2">
    <process id="Process_1" isExecutable="false">
      <startEvent id="StartEvent_1y45yut" name="hunger noticed">
        <outgoing>SequenceFlow_0h21x7r</outgoing>
      </startEvent>
      <task id="Task_1hcentk" name="choose recipe">
        <incoming>SequenceFlow_0h21x7r</incoming>
        <outgoing>SequenceFlow_0wnb4ke</outgoing>
      </task>
      <sequenceFlow id="SequenceFlow_0h21x7r" sourceRef="StartEvent_1y45yut" targetRef="Task_1hcentk" />
      <exclusiveGateway id="ExclusiveGateway_15hu1pt" name="desired dish?">
        <incoming>SequenceFlow_0wnb4ke</incoming>
      </exclusiveGateway>
      <sequenceFlow id="SequenceFlow_0wnb4ke" sourceRef="Task_1hcentk" targetRef="ExclusiveGateway_15hu1pt" />
    </process>
    <bpmndi:BPMNDiagram id="BpmnDiagram_1">
      <bpmndi:BPMNPlane id="BpmnPlane_1" bpmnElement="Process_1">
        
      </bpmndi:BPMNPlane>
    </bpmndi:BPMNDiagram>
  </definitions>`


export class WorkflowDiagramView extends Component {

  setup() {
    this.actionService = useService("action");
    this.dialogService = useService("dialog");
    this.orm = useService("orm");
    this.notification = useService("notification");
    onWillStart(async () => {
      await ensureJQuery();
      Promise.all([
        await loadCSS("https://unpkg.com/camunda-bpmn-js@0.1.0/dist/assets/camunda-platform-modeler.css"),
        await loadJS("https://unpkg.com/camunda-bpmn-js@0.1.0/dist/camunda-platform-modeler.development.js")
      ])
      await this.fetch_data()
    });
    onMounted(async () => {
      await this.renderView();
    });
  }

  async fetch_data() {
    if (this.props.action.context.active_id) {
      this.datas = await this.orm.call(
        "workflow.config",
        'get_data_workflow_diagrams',
        [this.props.action.context.active_id]
      );
      this.is_edit = this.datas.is_edit && this.props.action.context.editMode ? true : false;
      this.active_name = this.datas.name;
    }
  }

  async saveDiagram() {
    if (!this.is_edit) return
    var xmlData = await this.bpmnModeler.saveXML();
    var self = this;
    var result = await this.orm.write("workflow.config", [this.props.action.context.active_id], { bpmnio_xml: xmlData });
    if (result) {
      this.notification.add(_t("Refresh Diagrams"), { type: "success" }, 1000);
      await this.fetch_data();
      await this.renderView()
    }
  }

  backCurrent() {
    window.history.back()
  }

  async renderView() {
    var self = this;
    $('#budget_general_report_view').empty();
    setTimeout(async () => {
      this.bpmnModeler = new BpmnModeler({
        container: '#budget_general_report_view',
        // propertiesPanel: {
        //   parent: '#properties'
        // }
      });

      if (!this.is_edit) {
        $('.djs-palette').remove()
      }

      try {
        var xml = this.datas && this.datas.bpmnio_xml ? this.datas && this.datas.bpmnio_xml : templates_xml;
        await this.bpmnModeler.importXML(xml);
        this.bpmnModeler.get('canvas').zoom('fit-viewport');
      } catch (err) {
        console.error('something went wrong:', err);
      }

      var eventBus = this.bpmnModeler.get("eventBus");
      const elementRegistry = this.bpmnModeler.get('elementRegistry');
      var workflow_config_state_ids = this.datas.workflow_config_state_ids;
      var workflow_transitions_state_ids = this.datas.workflow_transitions_state_ids;
      elementRegistry.getAll().forEach(element => {
        const graphics = this.bpmnModeler.get('elementRegistry').getGraphics(element);
        // if (element.type === 'bpmn:Task' || element.type === "bpmn:StartEvent" || element.type === "bpmn:SequenceFlow" || element.type === 'bpmn:EndEvent') { // Áp dụng cho Task
        //   element.businessObject.name = "Dữ liệu sau khi import";
        //   this.bpmnModeler.get('modeling').updateLabel(element, "Dữ liệu sau khi import");
        //   graphics.querySelector('rect').style.fill = '#30b549'; // Đổi màu nền
        //   graphics.querySelector('rect').style.stroke = '#30b549'; // Đổi màu viền
        // }
        if (element.id in workflow_config_state_ids) {
          var label = workflow_config_state_ids[element.id].name;
          var position_workflow_type = workflow_config_state_ids[element.id].position_workflow_type;
          if (workflow_config_state_ids[element.id].position_workflow) {
            label += `(${workflow_config_state_ids[element.id].position_workflow})`;
          }
          element.businessObject.name = label;
          element.businessObject.workflow_config_state_id = workflow_config_state_ids[element.id].id
          this.bpmnModeler.get('modeling').updateLabel(element, label);

          if (element.type === "bpmn:Task") {
            if (position_workflow_type == 'start_workflow') {
              graphics.querySelector('rect').style.fill = ' #a5f7ff';
            }

            if (position_workflow_type == 'end_workflow') {
              graphics.querySelector('rect').style.fill = '#30b549';
            }

            if (position_workflow_type == 'cancel_workflow') {
              graphics.querySelector('rect').style.fill = '#a40631';
            }

            // if (position_workflow_type == 'refuse_workflow') {
            //   graphics.querySelector('rect').style.fill = '#e4d500';
            // }

          }

          if ((element.type === "bpmn:StartEvent" || element.type === "bpmn:IntermediateThrowEvent")) {
            if (position_workflow_type == 'start_workflow') {
              graphics.querySelector('circle').style.fill = ' #a5f7ff';
            }

            if (position_workflow_type == 'end_workflow') {
              graphics.querySelector('circle').style.fill = '#30b549';
            }

            if (position_workflow_type == 'cancel_workflow') {
              graphics.querySelector('circle').style.fill = '#a40631';
            }

            // if (position_workflow_type == 'refuse_workflow') {
            //   graphics.querySelector('circle').style.fill = '#e4d500';
            // }
          }

          if ((element.type === "bpmn:ExclusiveGateway")) {
            if (position_workflow_type == 'start_workflow') {
              graphics.querySelector('path').style.fill = ' #a5f7ff';
            }

            if (position_workflow_type == 'end_workflow') {
              graphics.querySelector('path').style.fill = '#30b549';
            }

            if (position_workflow_type == 'cancel_workflow') {
              graphics.querySelector('path').style.fill = '#a40631';
            }

            // if (position_workflow_type == 'refuse_workflow') {
            //   graphics.querySelector('circle').style.fill = '#e4d500';
            // }
          }
          
          
        }

        if (element.id in workflow_transitions_state_ids) {
          var labelTransitions = workflow_transitions_state_ids[element.id].name;
          if (element.type === "bpmn:SequenceFlow") {
            element.businessObject.name = labelTransitions;
            element.businessObject.workflow_transitions_state_id = workflow_transitions_state_ids[element.id].id
            this.bpmnModeler.get('modeling').updateLabel(element, labelTransitions);
          }
        }
      });
      eventBus.on("commandStack.shape.delete.execute", async function (event) {
        if (!self.is_edit) return
        const element = event.context.shape;
        if (element.businessObject.workflow_config_state_id) {
          await self.orm.unlink("workflow.config.state", [element.businessObject.workflow_config_state_id]);
        }
        if (element.businessObject.workflow_transitions_state_id) {
          await self.orm.unlink("workflow.transition", [element.businessObject.workflow_transitions_state_id]);
        }
        // await self.renderView();
      })

      eventBus.on('canvas.viewbox.changed', function () {
        const minimap = $('.djs-minimap');
        if (minimap) {
          minimap.addClass('open'); // Luôn bật MiniMap khi zoom/pan
        }
      });
      eventBus.on("element.dblclick", async function (event) {
        if (!self.is_edit) return
        self.global_elm = event.element;
        var elmId = event.element.id;
        if (event.element.type === "bpmn:SequenceFlow") {
          const source = event.element.businessObject.sourceRef; // Phần tử bắt đầu
          const target = event.element.businessObject.targetRef; // Phần tử kết thúc
          var workflow_transition_line_id = await self.orm.searchRead(
            "workflow.transition",
            [
              ["workflow_config_id", "=", self.props.action.context.active_id],
              ['bpmn_id', '=', elmId]
            ],
            []
          );

          var workflow_config_out_line_id = await self.orm.searchRead(
            "workflow.config.state",
            [
              ["workflow_config_id", "=", self.props.action.context.active_id],
              ['bpmn_id', '=', target.id]
            ],
            []
          );
          var workflow_config_from_line_id = await self.orm.searchRead(
            "workflow.config.state",
            [
              ["workflow_config_id", "=", self.props.action.context.active_id],
              ['bpmn_id', '=', source.id]
            ],
            []
          );

          return self.dialogService.add(FormViewDialog, {
            title: ('Workflow Transitions'),
            resModel: 'workflow.transition',
            resId: workflow_transition_line_id.length > 0 ? workflow_transition_line_id[0].id : false,
            context: {
              default_bpmn_id: elmId,
              default_workflow_config_id: self.props.action.context.active_id,
              default_act_to_id: workflow_config_out_line_id.length > 0 ? workflow_config_out_line_id[0].id : false,
              default_act_from_id: workflow_config_from_line_id.length > 0 ? workflow_config_from_line_id[0].id : false,
              default_name: source.name + '-' + target.name
            },
            onRecordSaved: async (result) => await self.saveDiagram(),
          });
        }

        if (event.element.type === "bpmn:StartEvent" || event.element.type === "bpmn:Task" || event.element.type === "bpmn:ExclusiveGateway" || event.element.type === "bpmn:IntermediateThrowEvent") {
          var workflow_config_line_id = await self.orm.searchRead(
            "workflow.config.state",
            [
              ["workflow_config_id", "=", self.props.action.context.active_id],
              ['bpmn_id', '=', elmId]
            ],
            []
          );
          return self.dialogService.add(FormViewDialog, {
            title: ('Workflow State'),
            resModel: 'workflow.config.state',
            resId: workflow_config_line_id.length > 0 ? workflow_config_line_id[0].id : false,
            context: {
              default_bpmn_id: elmId,
              default_workflow_config_id: self.props.action.context.active_id
            },
            onRecordSaved: async (result) => {
              await self.saveDiagram()
            }
          });
        }
      });
    }, 1000);
  }
}
WorkflowDiagramView.props = {
  action: Object,
  actionId: { type: Number, optional: true },
  className: String,
  fcy: { type: String, optional: true },
  updateActionState: { type: Function, optional: true },
  globalState: { type: Object, optional: true },
};
WorkflowDiagramView.template = "workflow_diagram.workflow_diagram_view"
registry.category("actions").add("workflow_diagram_view", WorkflowDiagramView);