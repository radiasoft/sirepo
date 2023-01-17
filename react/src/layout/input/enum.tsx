import React, { ChangeEventHandler, useContext, useEffect, useState } from "react";
import { FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { AppWrapper, CAppName, CSimulationInfoPromise } from "../../data/appwrapper";
import { CFormController } from "../../data/formController";
import { pollStatefulCompute } from "../../utility/compute";
import { CRouteHelper } from "../../utility/route";
import { LayoutProps } from "../layout";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";
import { Dependency } from "../../data/dependency";

export type EnumAllowedValues = { value: string, displayName: string }[]

export type EnumConfigRaw = {
    allowedValues: [string, string][]
} & InputConfigBase

export type EnumConfig = {
    allowedValues: EnumAllowedValues
} & InputConfigBase

export class EnumInputLayout extends InputLayout<EnumConfig, string, string> {
    constructor(config: EnumConfigRaw) {
        let newConfig = {
            ...config,
            allowedValues: config.allowedValues.map((v) => { return { value: v[0], displayName: v[1] }})
        }
        super(newConfig);
    }

    toModelValue: (value: string) => string = (v) => v;
    fromModelValue: (value: string) => string = (v) => v;

    validate: (value: string) => boolean = (value: string) => {
        return (!this.config.isRequired) || (this.hasValue(value) && this.config.allowedValues.filter(av => av.value === value).length > 0);
    };

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        const options = this.config.allowedValues.map(allowedValue => (
            <option key={allowedValue.value} value={allowedValue.value}>{allowedValue.displayName}</option>
        ));

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        let { valid, touched, ...otherProps } = props;

        return <Form.Select {...otherProps} size="sm" onChange={onChange} isInvalid={!valid && touched}>
            {options}
        </Form.Select>
    }
}

export type ComputeResultEnumConfig = {
    computeMethod: string,
    resultName: string,
    keyName: string,
    displayName: string
} & InputConfigBase

export class ComputeResultEnumInputLayout extends InputLayout<ComputeResultEnumConfig, string, string> {
    fromModelValue: (value: string) => string = (v) => v;
    toModelValue: (value: string) => string = (v) => v;

    validate: (value: string) => boolean = (v) => {
        // TODO: implement when working example of this input is available
        return true;
    };

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let appName = useContext(CAppName);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let routeHelper = useContext(CRouteHelper);

        let [optionList, updateOptionList] = useState(undefined);

        useEffect(() => {
            let enumOptionsPromise = new Promise((resolve, reject) => {
                simulationInfoPromise.then(({simulationId, version}) => {
                    pollStatefulCompute(routeHelper, {
                        method: this.config.computeMethod,
                        appName,
                        simulationId,
                        callback: (respObj) => {
                            let result = respObj[this.config.resultName];
                            resolve(result);
                        }
                    })
                })
            })

            enumOptionsPromise.then(result => updateOptionList(result));
        }, [])

        let {valid, touched, ...otherProps} = props;

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        const options = optionList
            ? optionList.map(v => (
                <option key={v[this.config.keyName]} value={v[this.config.keyName]}>{v[this.config.displayName]}</option>
            ))
            : [];
        return <Form.Select size="sm" {...otherProps} onChange={onChange} isInvalid={!valid && touched}>
            {options}
        </Form.Select>
    }
}

//TODO(pjm): mostly copied from ComputeResultEnumInputLayout above
// need to share more implementation with a base class
export class SimulationListEnumInputLayout extends InputLayout<InputConfigBase, string, string> {
    fromModelValue: (value: string) => string = (v) => v;
    toModelValue: (value: string) => string = (v) => v;

    validate: (value: string) => boolean = (v) => {
        // TODO: implement when working example of this input is available
        return true;
    };

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let routeHelper = useContext(CRouteHelper);
        let [optionList, updateOptionList] = useState(undefined);
        let formController = useContext(CFormController);
        //TODO(pjm): this is specific to the omega app but could be generalized
        let suffix = props.dependency.fieldName.match(/_\d+/);
        let simType = formController.getFormStateAccessor().getFieldValue(new Dependency(
            `simWorkflow.simType${suffix}`)).value as string;
        useEffect(() => {
            if (! simType) {
                return;
            }
            let appWrapper = new AppWrapper(simType, routeHelper);
            appWrapper.getSimulationList().then(list => {
                list.unshift({
                    simulationId: "",
                    name: "",
                    folder: "",
                    isExample: false,
                    simulation: null,
                });
                updateOptionList(list);
            });
        }, [simType])

        let {valid, touched, ...otherProps} = props;

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        const options = optionList
            ? optionList.map(v => (
                <option key={v.simulationId} value={v.simulationId}>{v.name}</option>
            ))
            : [];
        return <Form.Select size="sm" {...otherProps} onChange={onChange} isInvalid={!valid && touched}>
            {options}
        </Form.Select>
    }
}
                                            
