import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { Dispatch, AnyAction } from "redux";
import { ModelActions, ModelSelectors, ModelState } from "../store/models";
import { AbstractModelsWrapper } from "./form";

export const ContextModelsWrapper = React.createContext<ModelsWrapper>(undefined);

export type ModelWrapper = {
    updateModel: (value: ModelState) => void;
    hookModel: () => ModelState;
}

export class ModelsWrapper extends AbstractModelsWrapper<ModelState, unknown> {
    modelActions: ModelActions;
    modelSelectors: ModelSelectors;
    dispatch: Dispatch<AnyAction>;

    constructor({ modelActions, modelSelectors }: { modelActions: ModelActions, modelSelectors: ModelSelectors }) {
        super();
        this.modelActions = modelActions;
        this.modelSelectors = modelSelectors;

        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    getModel = (modelName: string, state: any) => {
        return this.modelSelectors.selectModel(modelName)(state);
    }

    updateModel = (modelName: string, value: ModelState) => {
        console.log("dispatching update to ", modelName, " changing to value ", value);
        this.dispatch(this.modelActions.updateModel({
            name: modelName,
            value
        }))
    }

    hookModel = (modelName: string) => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectModel(modelName));
    }

    getFieldFromModel(fieldName: string, model: ModelState): unknown {
        return model[fieldName];
    }
    setFieldInModel(fieldName: string, model: ModelState, value: unknown): ModelState {
        let m = {...model};
        m[fieldName] = value;
        return m;
    }

    saveToServer = (simulationInfo: any, modelNames: string[], state: any) => {
        let models = modelNames.map(mn => this.getModel(mn, state));
        simulationInfo.models = models;
        fetch("/save-simulation", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(simulationInfo)
        }).then(resp => {
            // TODO: error handling
        })
    }
}
