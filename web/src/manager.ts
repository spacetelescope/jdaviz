import * as base from '@jupyter-widgets/base';
import * as pWidget from '@phosphor/widgets';
import * as plotlywidget from 'plotlywidget';
import * as bqplot from 'bqplot';
import * as jmaterialui from 'jupyter-materialui';
import * as jastroimage from 'jupyter-astroimage';

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
        if (moduleName == 'plotlywidget') {
            console.log("Loading class plotlywidget.");
            return new Promise((resolve, reject) => {
                resolve(plotlywidget);
            }).then((module) => {
                if (module[className]) {
                    return module[className];
                } else {
                    return Promise.reject(`Class ${className} not found in module ${moduleName}@${moduleVersion}`);
                }
            });
        }
        else if (moduleName == 'bqplot') {
            console.log("Loading class bqplot.");
            return new Promise((resolve, reject) => {
                resolve(bqplot);
            }).then((module) => {
                if (module[className]) {
                    return module[className];
                } else {
                    return Promise.reject(`Class ${className} not found in module ${moduleName}@${moduleVersion}`);
                }
            });
        }
        else if (moduleName == 'jupyter-materialui') {
            console.log("Loading class jupyter-materialui.");
            return new Promise((resolve, reject) => {
                resolve(jmaterialui);
            }).then((module) => {
                if (module[className]) {
                    return module[className];
                } else {
                    return Promise.reject(`Class ${className} not found in module ${moduleName}@${moduleVersion}`);
                }
            });
        }
        else if (moduleName == 'jupyter-astroimage') {
            console.log("Loading class jupyter-astroimage.");
            return new Promise((resolve, reject) => {
                resolve(jastroimage);
            }).then((module) => {
                if (module[className]) {
                    return module[className];
                } else {
                    return Promise.reject(`Class ${className} not found in module ${moduleName}@${moduleVersion}`);
                }
            });
        } else {
            return super.loadClass(className, moduleName, moduleVersion);
        }
    }

    kernel: Kernel.IKernelConnection;
    el: HTMLElement;
}
