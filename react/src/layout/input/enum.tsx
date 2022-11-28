import React, { ChangeEventHandler, useContext, useEffect, useState } from "react";
import { FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { CAppName, CSimulationInfoPromise } from "../../data/appwrapper";
import { pollStatefulCompute } from "../../utility/compute";
import { LayoutProps } from "../layout";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";

export type EnumAllowedValues = { value: string, displayName: string }[]

export type EnumConfig = {
    allowedValues: EnumAllowedValues
} & InputConfigBase

export class EnumInputLayout extends InputLayout<EnumConfig, string, string> {
    constructor(config: EnumConfig) {
        super(config);
    }

    toModelValue: (value: string) => string = (v) => v;
    fromModelValue: (value: string) => string = (v) => v;

    validate: (value: string) => boolean = (value: string) => {
        return (!this.config.isRequired) || (this.hasValue(value) && this.config.allowedValues.filter(av => av.value == value).length > 0);
    };

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        const options = this.config.allowedValues.map(allowedValue => (
            <option key={allowedValue.value} value={allowedValue.value}>{allowedValue.displayName}</option>
        ));

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        return <Form.Select {...props} onChange={onChange}>
            {options}
        </Form.Select>
    }
}

export type ComputeResultEnumConfig = {
    computeMethod: string,
    resultName: string
} & InputConfigBase

export class ComputeResultEnumInputLayout extends InputLayout<ComputeResultEnumConfig, string, string> {
    constructor(config) {
        super(config);
    }

    fromModelValue: (value: string) => string = (v) => v;
    toModelValue: (value: string) => string = (v) => v;

    validate: (value: string) => boolean = (v) => {
        // TODO: implement when working example of this input is available
        return true;
    };

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let appName = useContext(CAppName);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);

        let [optionList, updateOptionList] = useState(undefined);

        useEffect(() => {
            let enumOptionsPromise = new Promise((resolve, reject) => {
                simulationInfoPromise.then(({simulationId, version}) => {
                    pollStatefulCompute({
                        pollInterval: 500,
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

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        // TODO: this is more of a mock element since this does not have
        // a working example right now
        return <Form.Select {...props} onChange={onChange}></Form.Select>
    }
}
