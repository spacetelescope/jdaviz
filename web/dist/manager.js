"use strict";
var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : new P(function (resolve) { resolve(result.value); }).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var base = require("@jupyter-widgets/base");
var pWidget = require("@phosphor/widgets");
var plotlywidget = require("plotlywidget");
var bqplot = require("bqplot");
var jmaterialui = require("jupyter-materialui");
var html_manager_1 = require("@jupyter-widgets/html-manager");
require("./widgets.css");
var WidgetManager = /** @class */ (function (_super) {
    __extends(WidgetManager, _super);
    function WidgetManager(kernel, el) {
        var _this = _super.call(this) || this;
        _this.kernel = kernel;
        _this.el = el;
        kernel.registerCommTarget(_this.comm_target_name, function (comm, msg) { return __awaiter(_this, void 0, void 0, function () {
            var oldComm;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        oldComm = new base.shims.services.Comm(comm);
                        return [4 /*yield*/, this.handle_comm_open(oldComm, msg)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); });
        return _this;
    }
    WidgetManager.prototype.display_view = function (msg, view, options) {
        var _this = this;
        return Promise.resolve(view).then(function (view) {
            pWidget.Widget.attach(view.pWidget, _this.el);
            view.on('remove', function () {
                console.log('view removed', view);
            });
            return view;
        });
    };
    /**
     * Create a comm.
     */
    WidgetManager.prototype._create_comm = function (target_name, model_id, data, metadata) {
        return __awaiter(this, void 0, void 0, function () {
            var comm;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.kernel.connectToComm(target_name, model_id)];
                    case 1:
                        comm = _a.sent();
                        if (data || metadata) {
                            comm.open(data, metadata);
                        }
                        return [2 /*return*/, Promise.resolve(new base.shims.services.Comm(comm))];
                }
            });
        });
    };
    /**
     * Get the currently-registered comms.
     */
    WidgetManager.prototype._get_comm_info = function () {
        return this.kernel.requestCommInfo({ target: this.comm_target_name }).then(function (reply) { return reply.content.comms; });
    };
    /**
     * Load a class and return a promise to the loaded object.
     */
    WidgetManager.prototype.loadClass = function (className, moduleName, moduleVersion) {
        if (moduleName == 'plotlywidget') {
            console.log("Loading class plotlywidget.");
            return new Promise(function (resolve, reject) {
                resolve(plotlywidget);
            }).then(function (module) {
                if (module[className]) {
                    return module[className];
                }
                else {
                    return Promise.reject("Class " + className + " not found in module " + moduleName + "@" + moduleVersion);
                }
            });
        }
        else if (moduleName == 'bqplot') {
            console.log("Loading class plotlywidget.");
            return new Promise(function (resolve, reject) {
                resolve(bqplot);
            }).then(function (module) {
                if (module[className]) {
                    return module[className];
                }
                else {
                    return Promise.reject("Class " + className + " not found in module " + moduleName + "@" + moduleVersion);
                }
            });
        }
        else if (moduleName == 'jupyter-materialui') {
            console.log("Loading class plotlywidget.");
            return new Promise(function (resolve, reject) {
                resolve(jmaterialui);
            }).then(function (module) {
                if (module[className]) {
                    return module[className];
                }
                else {
                    return Promise.reject("Class " + className + " not found in module " + moduleName + "@" + moduleVersion);
                }
            });
        }
        else {
            return _super.prototype.loadClass.call(this, className, moduleName, moduleVersion);
        }
    };
    return WidgetManager;
}(html_manager_1.HTMLManager));
exports.WidgetManager = WidgetManager;
//# sourceMappingURL=manager.js.map