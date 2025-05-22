
import { pubSub } from '@/services/pubsub.js';

class UIContext {
    // accessPath: keyed path into object or array data
    // ex. "electronBeam" or "beamline#3" or "volumes.air.material.components#3"
    //TODO(pjm): implement complex accessPath
    constructor(accessPath, viewName, fieldDef="basic") {
        if (! accessPath) {
            throw Error('Missing UIContext accessPath');
        }
        this.accessPath = accessPath;
        this.viewName = viewName || accessPath;
        this.fieldDef = fieldDef
        this.viewSchema = appState.schema.view[this.viewName];
        if (! this.viewSchema) {
            throw Error(`No schema view for name: ${this.viewName}`);
        }
        if (! this.viewSchema[this.fieldDef]) {
            throw Error(`Missing fieldDev: ${this.fieldDef} for viewName: ${this.viewName}`);
        }
        this.fields = this.#buildFields();
    }

    #buildFields() {
        const r = {};
        const sm = appState.schema.model[this.viewSchema.model || this.viewName];
        for (const f of this.viewSchema[this.fieldDef]) {
            //TODO(pjm): could be a structure of tabs or columns of fields
            if (f.includes('.')) {
                //TODO(pjm): f could be a "model.field" value which would refer to a different model
            }
            r[f] = {
                label: sm[f][0],
                val: this.#fieldValue(f, sm[f][2]),
                visible: true,
                enabled: true,
            };
            this.#updateFieldForType(r[f], sm[f]);
        }
        return r;
    }

    #fieldValue(fieldName, defaultValue) {
        const m = appState.models[this.accessPath];
        if (m && fieldName in m) {
            return m[fieldName];
        }
        return defaultValue;
    }

    #updateFieldForType(field, def) {
        field.cols = 5;
        field.tooltip = def[3];
        const t = def[1];
        if (t in appState.schema.enum) {
            field.widget = 'select';
            field.choices = appState.schema.enum[t].map((v) => {
                return {
                    code: v[0],
                    display: v[1],
                };
            });
        }
        else if (t === 'String') {
            field.widget = 'text';
        }
        else if (t === 'OptionalString') {
            field.widget = 'text';
            field.optional = true;
        }
        else if (t === 'Float') {
            field.widget = 'float';
            field.cols = 3;
        }
        else if (t === 'Email') {
            field.widget = 'email';
        }
        else {
            throw new Error(`unhandled field type: ${t}`);
        }
    }

    cancelChanges(proxy) {
        const m = appState.models[this.accessPath];
        for (const f in m) {
            // must use proxy not this for updates to ensure reactivity
            if (f in proxy.fields) {
                proxy.fields[f].val = m[f];
                proxy.fields[f].dirty = false;
            }
        }
    }

    isDirty() {
        for (const f in this.fields) {
            if (this.fields[f].dirty) {
                return true;
            }
        }
        return false;
    }

    isInvalid() {
        for (const f in this.fields) {
            if (this.fields[f].visible && this.fields[f].invalid) {
                return true;
            }
        }
        return false;
    }

    saveChanges() {
        const v = {};
        for (const f in this.fields) {
            v[f] = this.fields[f].val;
        }
        appState.saveChanges({
            [this.accessPath]: v,
        });
    }
}

class AppState {

    //TODO(pjm): AppState is not the right spot for viewLogic
    #viewLogic = {};

    initViewLogic(viewName, ui_ctx) {
        const v = this.#viewLogic[viewName];
        if (v) {
            v(ui_ctx);
        }
    }

    registerViewLogic(viewName, useFunction) {
        //TODO(pjm): breaks on dev reload
        //if (this.#viewLogic[viewName]) {
        //    throw new Error(`view logic already registered for view name: ${viewName}`);
        //}
        this.#viewLogic[viewName] = useFunction;
    }

    init(simulationType, schema) {
        if (this.simulationType || this.schema) {
            throw new Error('AppState already initialized');
        }
        this.simulationType = simulationType;
        this.schema = schema;
    }

    getUIContext(accessPath, fieldDef="basic", viewName=accessPath) {
        return new UIContext(accessPath, viewName, fieldDef);
    }

    loadModels(models) {
        this.models = models;
    }

    saveChanges(values) {
        for (const m in values) {
            if (this.models[m]) {
                for (const f in values[m]) {
                    if (f in this.models[m]) {
                        this.models[m][f] = values[m][f];
                    }
                }
            }
        }
        pubSub.publish(MODEL_CHANGED_EVENT, Object.keys(values));
    }
}

export const MODEL_CHANGED_EVENT = 'modelChanged';

export const appState = new AppState();
