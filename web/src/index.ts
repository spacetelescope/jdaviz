import 'font-awesome/css/font-awesome.css';

import {
    WidgetManager
} from './manager';

import {
    Kernel, ServerConnection, KernelMessage
} from '@jupyterlab/services';

let BASEURL = 'http://localhost:8888';
let WSURL = 'ws:' + BASEURL.split(':').slice(1).join(':');

var Manager = { kernel: null };

// Mount the manager on the browser window global so the kernel connection
// can be accessed from other js sources loaded on the page.
window['Manager'] = Manager;

document.addEventListener('DOMContentLoaded', function(event) {

    // Connect to the notebook webserver.
    let connectionInfo = ServerConnection.makeSettings({
        baseUrl: BASEURL,
        wsUrl: WSURL
    });

    Kernel.getSpecs(connectionInfo).then(kernelSpecs => {
        return Kernel.startNew({
            name: kernelSpecs.default,
            serverSettings: connectionInfo
        });
    }).then(kernel => {
        Manager.kernel = kernel;

        let code = require('../widget_code.json').join('\n');

        // Create the widget area and widget manager
        let widgetarea = document.getElementsByClassName('widgetarea')[0] as HTMLElement;
        let manager = new WidgetManager(kernel, widgetarea);

        // Run backend code to create the widgets.
        let execution = kernel.requestExecute({ code: code });

        execution.onIOPub = (msg) => {
            // If we have a display message, display the widget.
            if (KernelMessage.isDisplayDataMsg(msg)) {
                let widgetData: any = msg.content.data['application/vnd.jupyter.widget-view+json'];

                if (widgetData !== undefined && widgetData.version_major === 2) {
                    let model = manager.get_model(widgetData.model_id);
                    if (model !== undefined) {
                        model.then(model => {
                            manager.display_model(msg, model);
                        });
                    }
                }
            }
        };
    });
});

