import * as base from '@jupyter-widgets/base';
import { Kernel } from '@jupyterlab/services';
import { HTMLManager } from '@jupyter-widgets/html-manager';
import './widgets.css';
export declare class WidgetManager extends HTMLManager {
    constructor(kernel: Kernel.IKernelConnection, el: HTMLElement);
    display_view(msg: any, view: any, options: any): Promise<any>;
    /**
     * Create a comm.
     */
    _create_comm(target_name: string, model_id: string, data?: any, metadata?: any): Promise<base.shims.services.Comm>;
    /**
     * Get the currently-registered comms.
     */
    _get_comm_info(): Promise<any>;
    /**
     * Load a class and return a promise to the loaded object.
     */
    protected loadClass(className: string, moduleName: string, moduleVersion: string): Promise<any>;
    kernel: Kernel.IKernelConnection;
    el: HTMLElement;
}
