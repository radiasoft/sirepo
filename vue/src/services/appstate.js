
import { pubSub } from '@/services/pubsub.js';
import { ref } from 'vue';
import { requestSender } from '@/services/requestsender.js';

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
        this.fieldDef = fieldDef;
        if (! appState.schema) {
            //TODO(pjm): consider changing appState interface to support reloads
            throw new Error(`
                appState.schema is not set, possibly HMR reload lost the state.
                Refresh the browser window to continue.
            `);
        }
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
                tooltip: sm[f][3],
                widget: sm[f][1],
            };
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

    async saveChanges() {
        const v = {};
        for (const f in this.fields) {
            v[f] = this.fields[f].val;
        }
        await appState.saveChanges({
            [this.accessPath]: v,
        });
    }
}

class AppState {

    // for components, appState.isLoadedRef must be imported into the root level for reactivity:
    //   ex. const isLoadedRef = appState.isLoadedRef;
    isLoadedRef = ref(false);
    #lastAutoSaveData = null;

    #resetAutoSaveTimer() {
    }

    #deepEqualsNoSimulationStatus() {
        return false;
    }

    //TODO(pjm): currently no autosave timer. Is it needed?
    async autoSave() {
        if (! this.isLoadedRef.value ||
            this.#lastAutoSaveData && this.#deepEqualsNoSimulationStatus(
                this.#lastAutoSaveData.models, this.models)
        ) {
            if (callback) {
                callback({'state': 'noChanges'});
            }
            return;
        }
        this.#resetAutoSaveTimer();
        this.#lastAutoSaveData = {
            models: this.clone(this.models),
        };
        const r = await requestSender.sendRequest('saveSimulationData', this.#lastAutoSaveData);
        if (r.error) {
            throw new Error(r);
        }
        this.#lastAutoSaveData = this.clone(r);
        ['simulationSerial', 'name', 'lastModified'].forEach(f => {
            this.models.simulation[f] = this.#lastAutoSaveData.models.simulation[f];
        });
        return r;
    }

    async clearModels(emptyValues) {
        if (this.isLoadedRef.value) {
            await this.autoSave();
            this.#clearModels(emptyValues);
        }
        else {
            this.#clearModels(emptyValues);
        }
    }

    #clearModels(emptyValues) {
        this.models = emptyValues || {};
        this.isLoadedRef.value = false;
    }

    clone(obj) {
        return window.structuredClone
             ? window.structuredClone(obj)
             : JSON.parse(JSON.stringify(obj));
    }

    deleteSimulation(simulationId) {
        return requestSender.sendRequest('deleteSimulation', { simulationId });
    }

    getUIContext(accessPath, fieldDef="basic", viewName=accessPath) {
        return new UIContext(accessPath, viewName, fieldDef);
    }

    init(simulationType, schema) {
        if (this.simulationType || this.schema) {
            throw new Error('AppState already initialized');
        }
        this.simulationType = simulationType;
        this.schema = schema;
    }

    async loadModels(simulationId) {
        if (this.isLoadedRef.value) {
            throw new Error('loadModels() may only be called in an unloaded state');
        }
        this.clearModels();
        const r = await requestSender.sendRequest(
            'simulationData',
            {
                simulation_id: simulationId,
                pretty: false,
            });
        if (r.notFoundCopyRedirect) {
            throw new Error('not yet implemented:', r);
        }
        this.models = r.models;
        this.isLoadedRef.value = true;
    }

    async saveChanges(values) {
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
        await this.autoSave();
        //TODO(pjm): update reports
    }

    setModelDefaults(model, modelName) {
        // set model defaults from schema
        const m = this.schema.model[modelName];
        for (const f of Object.keys(m)) {
            if (! model[f]) {
                const v = m[f][2];
                model[f] = v && typeof b === 'object'
                             ? this.clone(v)
                             : v;
            }
        }
        return model;
    };
}

export const MODEL_CHANGED_EVENT = 'modelChanged';

export const appState = new AppState();
