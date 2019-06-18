import * as base from '@jupyter-widgets/base';
import * as pWidget from '@phosphor/widgets';

const libs = {
    'plotlywidget': import('plotlywidget'),
    'bqplot': import('bqplot'),
    'jupyter-materialui': import('jupyter-materialui'),
    'bqplot-image-gl': import('bqplot-image-gl'),
    'jupyter-matplotlib': import('jupyter-matplotlib'),
    'jupyter-vuetify': import('jupyter-vuetify')
};

import {
  Kernel
} from '@jupyterlab/services';

import {
    HTMLManager
} from '@jupyter-widgets/html-manager';

import './widgets.css';

export
class WidgetManager extends HTMLManager {
    constructor(kernel: Kernel.IKernelConnection, el: HTMLElement) {
        super();
        this.kernel = kernel;
        this.el = el;

        kernel.registerCommTarget(this.comm_target_name, async (comm, msg) => {
            let oldComm = new base.shims.services.Comm(comm);
            await this.handle_comm_open(oldComm, msg);
        });
    }

    display_view(msg, view, options) {
        return Promise.resolve(view).then((view) => {
            pWidget.Widget.attach(view.pWidget, this.el);
            view.on('remove', function() {
                console.log('view removed', view);
            });
            return view;
        });
    }

    /**
     * Create a comm.
     */
    async _create_comm(target_name: string, model_id: string, data?: any, metadata?: any): Promise<base.shims.services.Comm> {
            let comm = await this.kernel.connectToComm(target_name, model_id);
            if (data || metadata) {
                comm.open(data, metadata);
            }
            return Promise.resolve(new base.shims.services.Comm(comm));
        }

    /**
     * Get the currently-registered comms.
     */
    _get_comm_info(): Promise<any> {
        return this.kernel.requestCommInfo(
            {target: this.comm_target_name}).then(
                reply => reply.content.comms);
    }

    /**
     * Load a class and return a promise to the loaded object.
     */
    protected loadClass(className: string, moduleName: string, moduleVersion: string) {
        console.log(`Attempting load of ${moduleName}.${className}.`);
        return super.loadClass(className, moduleName, moduleVersion).then((result) => {
                return result;
            }
        ).catch((err) => {
            return new Promise((resolve, reject) => {
               resolve(libs[moduleName]);
            }).then((module) => {
               if (module[className]) {
                   return module[className];
               } else {
                   return Promise.reject(`Class ${className} not found in module ${moduleName}@${moduleVersion}`);
               }
            }).catch((err) => console.log(`No module named ${moduleName}.`))
        });
    }

    kernel: Kernel.IKernelConnection;
    el: HTMLElement;
}
