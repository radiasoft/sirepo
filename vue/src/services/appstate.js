
import { PubSub } from '@/services/pubsub.js';

export const appState = {
    models: {
        dog: {
            first_name:'Scooby',
            last_name: 'Doo',
            balance: 1.26,
            treats: '2x',
        },
    },

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
        PubSub.publish('modelChanged', Object.keys(values));
    },

    getUIContext(name) {
        return {
            first_name: {
                label: 'First Name',
                val: this.models.dog.first_name,
                widget: 'static',
                visible: true,
                cols: 5,
            },
            last_name: {
                label: 'Last Name',
                val: this.models.dog.last_name,
                widget: 'text',
                enabled: true,
                visible: true,
                cols: 5,
            },
            balance: {
                label: 'Balance',
                val: this.models.dog.balance,
                widget: 'float',
                enabled: true,
                visible: true,
                cols: 3,
                tooltip: 'Account balance',
            },
            treats: {
                label: 'Treats',
                val: this.models.dog.treats,
                widget: 'select',
                enabled: true,
                choices: [
                    '1x',
                    '2x',
                    '3x',
                    '4x',
                    '5x',
                ].map(v => ({ code: v, display: v })),
                visible: true,
                cols: 5,
            },
        };
    }
};
