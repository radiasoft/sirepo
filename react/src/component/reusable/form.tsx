import {
    Form,
    Row,
    Col
} from "react-bootstrap";
import { LabelTooltip } from "./label";
import React, {
    useState,
    useContext,
    useEffect
} from "react";
import {
    formActions,
    formSelectors
} from "../../store/formState";
import { FormController, formStateFromModel } from "../../data/formController";
import { useStore } from "react-redux";
import { CModelsWrapper, CFormStateWrapper, FormStateWrapper, ModelsWrapper, AbstractModelsWrapper } from "../../data/wrapper";
import { CSchema, CSimulationInfoPromise } from "../../data/appwrapper";
import { SimulationInfo } from "../simulation";
import { Schema } from "../../utility/schema";
import { AnyAction, Store } from "redux";

export function FormField(props) {
    let { label, tooltip, ...passedProps } = props;
    return (
        <Form.Group {...passedProps} size="sm" as={Row} className="mb-2 justify-content-center">
            <Form.Label column className="text-end">
                {label}
                {tooltip &&
                    <LabelTooltip text={tooltip} />
                }
            </Form.Label>
            <Col>
                {props.children}
            </Col>
        </Form.Group>
    )
}

export function EditorForm(props) {
    return (
        <Form>
            {props.children}
        </Form>
    );
}

export function formActionFunctions(formController: FormController, store: Store<any, AnyAction>, simulationInfoPromise: Promise<SimulationInfo>, schema: Schema, modelsWrapper: ModelsWrapper): { cancel: () => void, submit: () => void } {
    return {
        cancel: () => formController.cancelChanges(store.getState()),
        submit: () => {
            formController.saveToModels(store.getState());
            simulationInfoPromise.then(simulationInfo => {
                modelsWrapper.saveToServer(simulationInfo, Object.keys(schema.models), store.getState())
            })
        }
    } 
}

export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(CSchema);

    let store = useStore();

    let models = useContext(CModelsWrapper);
    let formState = new FormStateWrapper({
        formActions,
        formSelectors
    })

    let modelNames = (models as ModelsWrapper).getModelNames(store.getState());

    useEffect(() => {
        let state = store.getState();
        modelNames.map(mn => {
            return {
                modelName: mn,
                value: models.getModel(mn, state)
            }
        }).forEach(({ modelName, value }) => {
            if(!value) {
                throw new Error(`could not get model=${modelName}`);
            }
            let modelSchema = schema.models[modelName];
            if(!modelSchema) {
                throw new Error(`could not get schema for model=${modelName}`);
            }
            formState.updateModel(modelName, formStateFromModel(value, modelSchema, schema), store.getState());
        });

        updateHasInit(true);
    }, [])

    return hasInit && (
        <CFormStateWrapper.Provider value={formState}>
            {props.children}
        </CFormStateWrapper.Provider>
    );
}
