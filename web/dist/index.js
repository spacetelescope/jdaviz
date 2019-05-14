"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
require("codemirror/lib/codemirror.css");
require("codemirror/mode/python/python");
require("font-awesome/css/font-awesome.css");
var manager_1 = require("./manager");
var services_1 = require("@jupyterlab/services");
var BASEURL = 'http://localhost:8888';
var WSURL = 'ws:' + BASEURL.split(':').slice(1).join(':');
document.addEventListener('DOMContentLoaded', function (event) {
    // Connect to the notebook webserver.
    var connectionInfo = services_1.ServerConnection.makeSettings({
        baseUrl: BASEURL,
        wsUrl: WSURL
    });
    services_1.Kernel.getSpecs(connectionInfo).then(function (kernelSpecs) {
        return services_1.Kernel.startNew({
            name: kernelSpecs.default,
            serverSettings: connectionInfo
        });
    }).then(function (kernel) {
        // Create a codemirror instance
        var code = require('../widget_code.json').join('\n');
        // let inputarea = document.getElementsByClassName('inputarea')[0] as HTMLElement;
        // let editor = CodeMirror(inputarea, {
        //     value: code,
        //     mode: 'python',
        //     tabSize: 4,
        //     showCursorWhenSelecting: true,
        //     viewportMargin: Infinity,
        //     readOnly: false
        // });
        // Create the widget area and widget manager
        var widgetarea = document.getElementsByClassName('widgetarea')[0];
        var manager = new manager_1.WidgetManager(kernel, widgetarea);
        // Run backend code to create the widgets.
        var execution = kernel.requestExecute({ code: code });
        execution.onIOPub = function (msg) {
            // If we have a display message, display the widget.
            if (services_1.KernelMessage.isDisplayDataMsg(msg)) {
                var widgetData = msg.content.data['application/vnd.jupyter.widget-view+json'];
                if (widgetData !== undefined && widgetData.version_major === 2) {
                    var model = manager.get_model(widgetData.model_id);
                    if (model !== undefined) {
                        model.then(function (model) {
                            manager.display_model(msg, model);
                        });
                    }
                }
            }
        };
    });
});
//# sourceMappingURL=index.js.map