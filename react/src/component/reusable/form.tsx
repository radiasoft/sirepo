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
    formStatesSlice,
    initialFormStateFromValue
} from "../../store/formState";
import { useStore } from "react-redux";
import { AppWrapper, CSchema } from "../../data/appwrapper";
import { SimulationInfo } from "../simulation";
import { AnyAction, Dispatch, Store } from "redux";
import { FormStateHandleFactory } from "../../data/form";
import { modelsSlice } from "../../store/models";

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

export function formActionFunctions(config: {
    formHandleFactory: FormStateHandleFactory, 
    store: Store<any, AnyAction>, 
    simulationInfoPromise: Promise<SimulationInfo>,
    appWrapper: AppWrapper,
    dispatch: Dispatch<AnyAction>
}): { cancel: () => void, submit: () => void } {
    let {
        formHandleFactory,
        store,
        simulationInfoPromise,
        appWrapper,
        dispatch
    } = config;
    return {
        cancel: () => formHandleFactory.cancel(store.getState(), dispatch),
        submit: () => {
            formHandleFactory.save(store.getState(), dispatch);
            simulationInfoPromise.then(simulationInfo => {
                appWrapper.saveModelsToServer(simulationInfo, store.getState()[modelsSlice.name]);
            })
        }
    } 
}

export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(CSchema);

    let store = useStore();

    let ms = store.getState()[modelsSlice.name]
    let fs = store.getState()[formStatesSlice.name];
    let modelNames = Object.keys(ms);

    useEffect(() => {
        let state = store.getState();
        modelNames.map(mn => {
            return {
                modelName: mn,
                value: ms[mn]
            }
        }).forEach(({ modelName, value }) => {
            if(!value) {
                throw new Error(`could not get model=${modelName}`);
            }
            let modelSchema = schema.models[modelName];
            if(!modelSchema) {
                throw new Error(`could not get schema for model=${modelName}`);
            }
            fs[modelName] = mapProperties(ms, ([_, fv]) => initialFormStateFromValue(fv));
        });

        updateHasInit(true);
    }, [])

    return hasInit && (
        <>{props.children}</>
    );
}
