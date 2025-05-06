
import { PubSub } from '@/services/pubsub.js';

const _schema = {
    enum: {
        Treats: [
            ["1x", "1x"],
            ["2x", "2x"],
            ["3x", "3x"],
            ["4x", "4x"],
            ["5x", "5x"],
        ],


        Gender: [
            ["male", "Male"],
            ["female", "Female"]
        ],
        DogDisposition: [
            ["aggressive", "Aggressive"],
            ["friendly", "Friendly"],
            ["submissive", "Submissive"]
        ],
    },
    model: {
        dog: {
            first_name: ["First Name", "String"],
            last_name: ["Last Name", "String"],
            balance: ["Balance", "Float", 0, "Account balance"],
            treats: ["Treats", "Treats", "1x"],


            breed: ["Breed", "String"],
            gender: ["Gender", "Gender", "male"],
            height: ["Height [cm]", "Float", 50.0, "Distance from front paws to withers"],
            weight: ["Weight [lbs]", "Float", 60.5],
            disposition: ["Disposition", "DogDisposition", "friendly"],
            favoriteTreat: ["Favorite Treat", "OptionalString", ""],
        },
        heightWeightReport: {}
    },
    view: {
        dog: {
            title: "Dog",
            basic: [
                "first_name",
                "last_name",
                "balance",
                "treats",

                "breed",
                "weight",
                "height",
                "disposition",
                "favoriteTreat",
            ],
            advanced: [
                "breed",
                "gender",
                "weight",
                "height",
            ],
        },
        heightWeightReport: {
            title: "Physical Characteristics",
            advanced: [],
        },
    },
};

export const appState = {
    models: {
        dog: {
            first_name:'Scooby',
            last_name: 'Doo',
            balance: 1.27,
            treats: '2x',

            breed: 'Great Dane',
            weight: 70.25,
            height: 81.28,
            disposition: "friendly",
            favoriteTreat: "",
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

    getUIContext(accessPath, viewName, fieldDef="basic") {
        // accessPath: keyed path into object data
        // ex. "electronBeam" or "beamline#3" or "volumes.air.material.components#3"

        viewName = viewName || accessPath;
        const r = {
            /*
            _ui_ctx: {
                accessPath,
                viewName,
                fieldDef,
            },
            */
        };

        const updateFieldForType = (field, def) => {
            field.cols = 5;
            field.tooltip = def[3];
            const t = def[1];
            if (t in _schema.enum) {
                field.widget = 'select';
                field.choices = _schema.enum[t].map((v) => {
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
            else {
                throw new Error(`unhandled field type: ${t}`);
            }
        };

        const sv = _schema.view[viewName];
        //TODO(pjm): need a better structure for this
        r._view = sv;
        const sm = _schema.model[sv.model || viewName];
        for (const f of sv[fieldDef]) {
            //TODO(pjm): could be a structure of tabs or columns of fields
            if (f.includes('.')) {
                //TODO(pjm): f could be a "model.field" value which would refer to a different model
            }
            r[f] = {
                label: sm[f][0],
                val: this.models[accessPath][f],
                visible: true,
                enabled: true,
            };
            updateFieldForType(r[f], sm[f]);
        }
        return r;
    }
};
