
import { pubSub } from '@/services/pubsub.js';
import { ref } from 'vue';
import { requestSender } from '@/services/requestsender.js';
import { schema } from '@/services/schema.js';
import { singleton } from '@/services/singleton.js';
import { util } from '@/services/util.js';

class UIContext {
    constructor(viewName, fieldDef, containerName, model) {
        if (! viewName) {
            throw Error('Missing UIContext viewName');
        }
        this.viewName = viewName;
        this.fieldDef = fieldDef;
        if (containerName) {
            if (! appState.models[containerName]) {
                throw Error(`UIContext containerName: ${containerName} not present in appState`);
            }
            if (! model) {
                throw Error(`UIContext has containerName: ${containerName} but no model`);
            }
            if (! model._id) {
                throw Error(`UIContext has containerName: ${containerName} but no model id: ${model}`);
            }
        }
        this.containerName = containerName;
        this.model = model;
        this.viewSchema = schema.view[this.viewName];
        if (! this.viewSchema) {
            throw Error(`No schema view for name: ${this.viewName}`);
        }
        if (! this.viewSchema[this.fieldDef]) {
            throw Error(`Missing view fieldDef: ${this.viewName}.${this.fieldDef}`);
        }
        this.modelName = this.viewSchema.model || this.viewName;
        this.fields = this.#buildFields();
    }

    #buildFields() {
        const r = {};
        const sm = schema.model[this.modelName];
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
        const m = this.model || appState.models[this.modelName];
        if (m && fieldName in m) {
            return m[fieldName];
        }
        return defaultValue;
    }

    cancelChanges(proxy) {
        const m = this.model || appState.models[this.modelName];
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
        const updateModel = (model, values) => {
            for (const f in values) {
                if (f in model) {
                    model[f] = values[f];
                }
            }
        };
        const v = {};
        for (const f in this.fields) {
            v[f] = this.fields[f].val;
        }
        const names = [this.modelName];
        if (this.containerName) {
            names.push(this.containerName);
            //TODO(pjm): assume containerName references an array for now.
            // Later, it could be an object, in which case searching the nested
            // structure for the model id would be required

            for (const m of appState.models[this.containerName]) {
                if (m._id == this.model._id) {
                    updateModel(m, v);
                    break;
                }
            }
            //TODO(pjm): if model with id does not exist, it should be added to the container
        }
        else {
            updateModel(appState.models[this.modelName], v);
        }
        await appState.saveChanges(names);
    }
}

class AppState {

    // for components, appState.isLoadedRef must be imported into the root level for reactivity:
    //   ex. const isLoadedRef = appState.isLoadedRef;
    isLoadedRef = ref(false);
    #lastAutoSaveData = null;

    #resetAutoSaveTimer() {
        //TODO(pjm): currently no autosave timer. Is it needed?
    }

    async autoSave() {
        if (! this.isLoadedRef.value ||
            this.#lastAutoSaveData && util.deepEquals(
                this.#lastAutoSaveData.models, this.models)
        ) {
            return;
        }
        this.#resetAutoSaveTimer();
        this.#lastAutoSaveData = {
            models: util.clone(this.models),
        };
        const r = await requestSender.sendRequest('saveSimulationData', this.#lastAutoSaveData);
        if (r.error) {
            throw new Error(r);
        }
        this.#lastAutoSaveData = util.clone(r);
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

    deleteSimulation(simulationId) {
        return requestSender.sendRequest('deleteSimulation', { simulationId });
    }

    formatFileType(modelName, fieldName) {
        return `${modelName}-${fieldName}`;
    }

    getUIContext(viewName, fieldDef, { containerName=null, model=null } = {}) {
        return new UIContext(viewName, fieldDef, containerName, model);
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
        this.#lastAutoSaveData = {
            models: util.clone(this.models),
        };
        this.isLoadedRef.value = true;
    }

    async saveChanges(names) {
        pubSub.publish(MODEL_CHANGED_EVENT, names);
        await this.autoSave();
        pubSub.publish(MODEL_SAVED_EVENT, names);
    }

    setModelDefaults(model, modelName) {
        // set model defaults from schema
        const m = schema.model[modelName];
        for (const f of Object.keys(m)) {
            if (! model[f]) {
                const v = m[f][2];
                model[f] = v && typeof b === 'object'
                             ? util.clone(v)
                             : v;
            }
        }
        return model;
    };
}

export const MODEL_CHANGED_EVENT = 'modelChanged';

export const MODEL_SAVED_EVENT = 'modelSaved';

export const appState = singleton.add('appState', () => new AppState());
