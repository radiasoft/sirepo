
import { schema } from '@/services/schema.js';
import { singleton } from '@/services/singleton.js';

class Strings {

    formatKey(key, modelName) {
        return this.ucfirst(this.get(key, modelName));
    }

    formatTemplate(template, args) {
        return template.replace(
            /{(\w*)}/g,
            (m, k) => {
                if (! (k in (args || {}))) {
                    if (! (k in schema.strings)) {
                        throw new Error(`k=${k} not found in args=${args} or strings=${schema.strings}`);
                    }
                    return schema.strings[k];
                }
                return args[k];
            },
        );
    }

    get(key, modelName) {
        let s;
        if (modelName && schema.strings[modelName] && schema.strings[modelName][key]) {
            s = schema.strings[modelName][key];
        }
        return s || schema.strings[key];
    }

    newSimulationLabel() {
        return `New ${this.formatKey('simulationDataType')}`;
    }

    saveButtonLabel(modelName) {
        return this.get('save', modelName) || 'Save';
    }

    startButtonLabel(modelName) {
        return `Start New ${this.typeOfSimulation(modelName)}`;
    }

    stopButtonLabel(modelName) {
        return `End ${this.typeOfSimulation(modelName)}`;
    }

    typeOfSimulation(modelName) {
        return this.ucfirst(this.get('typeOfSimulation', modelName));
    }

    ucfirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

export const strings = singleton.add('strings', () => new Strings());
