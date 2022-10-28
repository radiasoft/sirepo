import { mapProperties } from "../utility/object";
import { useDispatch, useSelector } from "react-redux";
import { useShown, ValueSelector } from "../hook/shown";

export let formStateFromModel = (model, modelSchema) => mapProperties(modelSchema, (fieldName, { type }) => {
    const valid = type.validate(model[fieldName])
    return {
        valid: valid,
        value: valid ? model[fieldName] : "",
        touched: false,
        active: true
    }
})

export class FormState {
    constructor({ formActions, formSelectors }) {
        this.formActions = formActions;
        this.formSelectors = formSelectors;

        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    getModel = (modelName, state) => {
        return this.formSelectors.selectFormState(modelName)(state);
    }

    forModel = (modelName) => {
        return {
            updateModel: (value) => {
                return this.updateModel(modelName, value);
            },
            hookModel: () => {
                return this.hookModel(modelName);
            },
            forField: (fieldName) => {
                return {
                    updateField: (value) => {
                        return this.updateField(modelName, fieldName, value);
                    }
                }
            }
        }
    }

    updateModel = (modelName, value) => {
        console.log("dispatching update form to ", modelName, " changing to value ", value);
        this.dispatch(this.formActions.updateFormState({
            name: modelName,
            value
        }))
    }

    updateField = (modelName, fieldName, value) => {
        console.log("dispatching update form to ", modelName, " changing to value ", value);
        this.dispatch(this.formActions.updateFormFieldState({
            name: modelName,
            field: fieldName,
            value
        }))
    }

    hookModel = (modelName) => {
        let selectFn = useSelector;
        return selectFn(this.formSelectors.selectFormState(modelName));
    }
}

export class FormController {
    constructor({ formState, hookedDependencies }) {
        this.formState = formState;

        this.hookedModels = {};

        this.hookedFields = hookedDependencies.map(hookedDependency => {
            let { fieldName, modelName } = hookedDependency;

            if(!(modelName in this.hookedModels)) {
                let formStateModel = this.formState.forModel(modelName);

                this.hookedModels[modelName] = {
                    dependency: hookedDependency.model,
                    value: { ...formStateModel.hookModel() },
                    ...formStateModel
                }
            }

            let model = this.hookedModels[modelName];

            let currentValue = model.value[fieldName];

            let shownFn = useShown;
            let active = shownFn(hookedDependency.shown, true, formState, ValueSelector.Fields);

            currentValue = {
                ...currentValue,
                active
            }

            let formStateField = model.forField(fieldName);

            return {
                fieldName,
                modelName,
                model,
                value: currentValue,
                dependency: hookedDependency,
                updateValue: (v) => {
                    formStateField.updateField({
                        value: v,
                        valid: hookedDependency.type.validate(v),
                        touched: true,
                        active: currentValue.active
                    });
                }
            }
        })
    }

    getHookedField = (dependency) => {
        return this.hookedFields.find(hookedDependency => {
            return (dependency.modelName === hookedDependency.modelName &&
                dependency.fieldName === hookedDependency.fieldName);
        })
    }

    saveToModels = () => {
        Object.entries(this.hookedModels).forEach(([modelName, model]) => {
            let changedFields = Object.keys(model.value)
            .map(fieldName => this.getHookedField({ fieldName, modelName }))
            .filter(hookedField => !!hookedField);

            let changesObj = Object.fromEntries(changedFields.map(hookedField => {
                return [
                    hookedField.fieldName,
                    hookedField.dependency.type.dbValue(model.value[hookedField.fieldName].value)
                ]
            }))

            let nextModelValue = { ...model.dependency.value };
            Object.assign(nextModelValue, changesObj);

            console.log("submitting value ", nextModelValue, " to ", modelName);
            model.dependency.updateModel(nextModelValue);
            // this should make sure that if any part of the reducers are inconsistent / cause mutations
            // then the form state should remain consistent with saved model copy
            // TODO: this line has been changed with recent update, evaluate
            model.updateModel(formStateFromModel(nextModelValue, model.dependency.schema));
        })
    }

    cancelChanges = () => {
        Object.entries(this.hookedModels).forEach(([modelName, model]) => {
            model.updateModel(formStateFromModel(model.dependency.value, model.dependency.schema));
        })
    }

    isFormStateDirty = () => {
        //let d = Object.values(this.hookedFields).map(({ value: { active, touched } }) => active && touched).includes(true);
        return Object.values(this.hookedFields).map(({ value: { touched } }) => !!touched).includes(true);
    }
    isFormStateValid = () => {
        //let v = !Object.values(this.hookedFields).map(({ value: { active, valid } }) => !active || valid).includes(false); // TODO: check completeness (missing defined variables?)
        return !Object.values(this.hookedFields).map(({ value: { valid } }) => !!valid).includes(false);;
    }
}
