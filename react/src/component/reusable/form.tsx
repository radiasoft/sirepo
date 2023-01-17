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
import { formStateFromModel } from "../../data/formController";
import { useStore } from "react-redux";
import { CModelsWrapper, CFormStateWrapper, FormStateWrapper } from "../../data/wrapper";
import { CSchema } from "../../data/appwrapper";

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

export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(CSchema);

    let store = useStore();

    let models = useContext(CModelsWrapper);
    let formState = new FormStateWrapper({
        formActions,
        formSelectors
    })

    let modelNames = Object.keys(schema.models);

    useEffect(() => {
        let state = store.getState();
        modelNames.map(mn => {
            return {
                modelName: mn,
                value: models.getModel(mn, state)
            }
        }).forEach(({ modelName, value }) => {
            formState.updateModel(modelName, formStateFromModel(value, schema.models[modelName]))
        });

        updateHasInit(true);
    }, [])

    return hasInit && (
        <CFormStateWrapper.Provider value={formState}>
            {props.children}
        </CFormStateWrapper.Provider>
    );
}
