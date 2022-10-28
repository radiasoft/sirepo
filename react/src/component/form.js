import {
    Form,
    Row,
    Col
} from "react-bootstrap";
import { LabelTooltip } from "../component/label";
import {
    useState,
    useContext,
    useEffect
} from "react";
import {
    ContextSchema,
    ContextModelsWrapper,
    ContextRelativeFormState
} from "../context";
import { FormState } from "../data/form";
import {
    updateFormFieldState,
    updateFormState,
    selectFormState
} from "../store/formState";
import { formStateFromModel } from "../data/form";
import { useStore } from "react-redux";

export function FormField(props) {
    let { label, tooltip, ...passedProps } = props;
    return (
        <Form.Group {...passedProps} size="sm" as={Row} className="sr-form-row justify-content-center">
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

    let schema = useContext(ContextSchema);

    let store = useStore();

    let models = useContext(ContextModelsWrapper);
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
        Object.entries(models.getModels(store.getState())).forEach(([modelName, model]) => {
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
