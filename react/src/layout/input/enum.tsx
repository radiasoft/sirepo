import React, { ChangeEventHandler, useContext, useEffect, useState } from "react";
import { AppWrapper, CAppName, CSimulationInfoPromise } from "../../data/appwrapper";
import { CFormController } from "../../data/formController";
import { CRouteHelper } from "../../utility/route";
import { Dependency } from "../../data/dependency";
import { Form } from "react-bootstrap";
import { FunctionComponent } from "react";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";
import { LayoutProps } from "../layout";
import { pollStatefulCompute } from "../../utility/compute";

export type EnumAllowedValues = { value: string, displayName: string }[]

export type EnumConfigRaw = {
    allowedValues: [string, string][]
} & InputConfigBase

export type EnumConfig = {
    allowedValues: EnumAllowedValues
} & InputConfigBase

abstract class EnumInputBaseLayout<C extends EnumConfig = any> extends InputLayout<C, string, string> {

    toModelValue: (value: string) => string = v => v;
    fromModelValue: (value: string) => string = v => v;

    validate: (value: string) => boolean = (value: string) => {
        return ( ! this.config.isRequired) || (
            this.hasValue(value) && this.config.allowedValues.some(v => v.value === value)
        );
    };

    formElement(props) {
        const onChange: ChangeEventHandler<HTMLSelectElement> = event => {
            props.onChange(event.target.value);
        }
        const options = this.config.allowedValues.map(v => (
            <option key={v.value} value={v.value}>
                {v.displayName}
            </option>
        ));
        return <Form.Select {...props} size="sm" onChange={onChange}>
            { options }
        </Form.Select>
    }

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = props => {
        return this.formElement(props)
    }
}

export class EnumInputLayout extends EnumInputBaseLayout<EnumConfig> {
    constructor(config: EnumConfigRaw) {
        super({
            ...config,
            allowedValues: config.allowedValues.map(v => ({ value: v[0], displayName: v[1] })),
        });
    }
}

export type ComputeResultEnumConfig = {
    computeMethod: string,
    resultName: string,
    keyName: string,
    displayName: string
} & EnumConfig

export class ComputeResultEnumInputLayout extends EnumInputBaseLayout<ComputeResultEnumConfig> {

    constructor(config) {
        super({
            ...config,
            allowedValues: [],
        });
    }

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = props => {
        const appName = useContext(CAppName);
        const simulationInfoPromise = useContext(CSimulationInfoPromise);
        const routeHelper = useContext(CRouteHelper);
        const [optionList, updateOptionList] = useState(undefined);
        useEffect(() => {
            let enumOptionsPromise = new Promise<any>((resolve, reject) => {
                simulationInfoPromise.then(({simulationId, version}) => {
                    pollStatefulCompute(routeHelper, {
                        method: this.config.computeMethod,
                        appName,
                        simulationId,
                        callback: respObj => {
                            resolve(respObj[this.config.resultName]);
                        }
                    })
                })
            })
            enumOptionsPromise.then(result => updateOptionList(
                (result || []).map(v => ({
                    value: v[this.config.keyName],
                    displayName: v[this.config.displayName],
                })),
            ));
        }, [])
        this.config.allowedValues = optionList || [];
        return this.formElement(props)
    }
}

export class SimulationListEnumInputLayout extends EnumInputBaseLayout<EnumConfig> {

    constructor(config) {
        super({
            ...config,
            allowedValues: [],
        });
    }

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        const routeHelper = useContext(CRouteHelper);
        const [optionList, updateOptionList] = useState(undefined);
        const formController = useContext(CFormController);
        //TODO(pjm): these 2 lines are specific to the omega app but could be generalized
        const suffix = props.dependency.fieldName.match(/_\d+/);
        const simType = formController.getFormStateAccessor().getFieldValue(new Dependency(
            `simWorkflow.simType${suffix}`)).value as string;
        useEffect(() => {
            if (! simType) {
                return;
            }
            new AppWrapper(simType, routeHelper).getSimulationList().then(list => {
                updateOptionList([
                    {
                        value: "",
                        displayName: "",
                    },
                ].concat((list || []).map(v => ({
                    value: v.simulationId,
                    displayName: v.name,
                }))));
            });
        }, [simType])
        this.config.allowedValues = optionList || [];
        return this.formElement(props);
    }
}
