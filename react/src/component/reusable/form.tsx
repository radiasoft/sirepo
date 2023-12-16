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
    formStatesSlice
} from "../../store/formState";
import { useDispatch, useStore } from "react-redux";
import { AppWrapper, CSchema } from "../../data/appwrapper";
import { SimulationInfo } from "../simulation";
import { AnyAction, Dispatch, Store } from "redux";
import { FormStateHandleFactory, initialFormStateFromValue } from "../../data/form";
import { modelsSlice } from "../../store/models";
import { mapProperties } from "../../utility/object";

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
    dispatch: Dispatch<AnyAction>
}): { cancel: () => void, submit: () => void } {
    let {
        formHandleFactory,
        store,
        dispatch
    } = config;
    return {
        cancel: () => formHandleFactory.cancel(store.getState(), dispatch),
        submit: () => {
            formHandleFactory.save(store.getState(), dispatch);
        }
    } 
}

export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(CSchema);

    let store = useStore();
    let dispatch = useDispatch();

    let ms = store.getState()[modelsSlice.name]
    let modelNames = Object.keys(ms);

    useEffect(() => {
        modelNames.map(mn => {
            return {
                modelName: mn,
                value: ms[mn]
            }
        }).forEach(({ modelName, value }) => {
            if(!value) {
                throw new Error(`could not get model=${modelName}`);
            }
            /*let modelSchema = schema.models[modelName];
            if(!modelSchema) {
                throw new Error(`could not get schema for model=${modelName}`);
            }*/
            dispatch(formActions.updateModel({
                name: modelName,
                value: mapProperties(value, (_, fv) => initialFormStateFromValue(fv))
            }));
        });
        console.log("fs store", store.getState());
        updateHasInit(true);
    })

    return hasInit && (
        <>{props.children}</>
    );
}
