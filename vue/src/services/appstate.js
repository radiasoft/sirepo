
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

    isLoadedRef = ref(false);
    #lastAutoSaveData = null;

    #resetAutoSaveTimer() {
    }

    #deepEqualsNoSimulationStatus() {
        return false;
    }

    //TODO(pjm): currently no autosave timer. Is it needed?
    autoSave(callback) {
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
        requestSender.sendRequest(
            'saveSimulationData',
            (response) => {
                if (response.error) {
                    //TODO(pjm): errorService
                    //errorService.alertText(resp.error);
                    throw new Error(resp.error);
                    return;
                }
                this.#lastAutoSaveData = this.clone(response);
                ['simulationSerial', 'name', 'lastModified'].forEach(f => {
                    this.models.simulation[f] = this.#lastAutoSaveData.models.simulation[f];
                });
                if (callback) {
                    callback(response);
                }
            },
            this.#lastAutoSaveData,
            (response) => {
                // give the user some feedback that the save failed
                if (! response || response.error === 'Server Error') {
                    //TODO(pjm): errorService
                    //errorService.alertText('Save failed due to a server error');
                    throw new Error('Save failed due to a server error');
                }
                else {
                    //TODO(pjm): errorService
                    //errorService.alertText(response.error);
                    throw new Error(response.error);
                }
            },
        );
    }

    clearModels(emptyValues) {
        if (this.isLoadedRef.value) {
            this.autoSave(() => this.#clearModels(emptyValues));
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

    deleteSimulation(simulationId, callback) {
        requestSender.sendRequest(
            'deleteSimulation',
            callback,
            {
                simulationId,
            },
        );
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

    loadModels(simulationId, callback) {
        if (this.isLoadedRef.value) {
            throw new Error('loadModels() may only be called in an unloaded state');
        }
        this.clearModels();
        requestSender.sendRequest(
            'simulationData',
            (response) => {
                if (response.notFoundCopyRedirect) {
                    throw new Error('not yet implemented:', response);
                }
                this.models = response.models;
                this.isLoadedRef.value = true;
                if (callback) {
                    callback();
                }
            },
            {
                simulation_id: simulationId,
                pretty: false
            });
    }

    saveChanges(values, callback) {
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
        this.autoSave(() => {
            //TODO(pjm): update reports
            if (callback) {
                callback();
            }
        });
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
