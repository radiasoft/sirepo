import { useDispatch, useStore } from "react-redux";
import { ContextModels, ContextRelativeFormState, ContextSchema } from '../components/context'
import { useContext, useEffect, useState } from "react";
import { useSetup } from "../hooks";
import { selectModels } from '../store/models';
import {
    selectFormState,
    updateFormState,
    updateFormFieldState
} from '../store/formState'

import "./form.scss";
import { FormState } from "../data/form";


export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(ContextSchema);

    let models = useContext(ContextModels);
    let formState = new FormState({
        formActions: {
            updateFormFieldState,
            updateFormState
        },
        formSelectors: {
            selectFormState
        }
    })

    useEffect(() => {
        Object.entries(models.getModels()).forEach(([modelName, model]) => {
            if (modelName in schema.models) { // TODO non-model data should not be stored with models in store
                formState.updateModel(modelName, formStateFromModel(model, schema.models[modelName]))
            }
        })
        updateHasInit(true);
    }, [])
    
    return hasInit && (
        <ContextRelativeFormState.Provider value={formState}>
            {props.children}
        </ContextRelativeFormState.Provider>
    );
}
