//import { React }
import { useContext, useEffect, useState } from "react";
import { Col, Form } from "react-bootstrap";
import { ContextAppName, ContextSimulationInfoPromise } from "./context";
import { pollStatefulCompute } from "./utility/compute";

export class rsType {
    constructor({ isRequired }) {
        //this.colSize = this.hasValue(colSize) ? colSize : 5;
        this.isRequired = this.hasValue(isRequired) ? isRequired : true;
    }

    component = (props) => {
        let {value, valid, touched, onChange, ...otherProps} = props;

        let InputComponent = this.inputComponent;
        return (
            <Col>
                <InputComponent
                {...otherProps}
                value={this.hasValue(value) ? value : ""}
                isInvalid={!valid && touched}
                onChange={onChange}/>
            </Col>
        )
    }

    dbValue = (value) => {
        return value;
    }
    hasValue = (value) => {
        return value !== undefined && value != null;
    }
    validate = (value) => {
        return false;
    }
}

export class rsString extends rsType {
    constructor(props) {
        super(props);
        this.align = "text-start";
    }
    inputComponent = (props) => {
        return (
            <Form.Control className={this.align} type="text" {...props}></Form.Control>
        )
    }
    validate = (value) => {
        return (!this.isRequired) || (this.hasValue(value) && value.length > 0);
    }
}

export class rsAbstrNumber extends rsType {
    constructor(props) {
        super(props);
        this.align = "text-end";
    }

    inputComponent = (props) => {
        return (
            <Form.Control className={this.align} type="text" {...props}></Form.Control>
        )
    }
}

export class rsFloat extends rsAbstrNumber {
    static REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
    dbValue = (value) => {
        return Number.parseFloat(value);
    }
    validate = (value) => {
        return (!this.isRequired) || (this.hasValue(value) && rsFloat.REGEXP.test(value));
    }
}

export class rsInteger extends rsAbstrNumber {
    static REGEXP = /^[-+]?\d+$/;
    dbValue = (value) => {
        return Number.parseInt(value);
    }
    validate = (value) => {
        return (!this.isRequired) || (this.hasValue(value) && rsInteger.REGEXP.test(value));
    }
}

export class rsBoolean extends rsType {
    constructor({ isRequired }) {
        super({ isRequired });
    }

    dbValue = (value) => {
        return (value === "true" || value === true) ? "1" : "0"; // TODO ???????? why arent these just booleans?
    }

    validate = (value) => {
        return (!this.isRequired) || this.hasValue(value);
    }

    inputComponent = (props) => {
        // checkboxes are really dumb so we need more settings here
        let onChange = (event) => {
            event.target.value = event.target.checked;
            props.onChange(event);
        }
        let value = props.value == true || props.value == "true";
        return <Form.Check {...props} onChange={onChange} checked={value}></Form.Check>
    }
}

export class rsFile extends rsType {
    constructor({ isRequired, pattern }) {
        super({ isRequired })
        this.pattern = (pattern && new RegExp(pattern)) || undefined;
    }

    dbValue = (value) => {
        return value;
    }

    validate = (value) => {
        // TODO
        return (!this.isRequired) || (this.hasValue(value) && value.length > 0);
    }

    inputComponent = (props) => {
        let { dependency, ...otherProps } = props;

        let contextFn = useContext;
        let stateFn = useState;
        let effectFn = useEffect;

        let appName = contextFn(ContextAppName);
        let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);

        let [fileNameList, updateFileNameList] = stateFn(undefined);

        effectFn(() => {
            let fileListPromise = new Promise((resolve, reject) => {
                simulationInfoPromise.then(({ simulationId, version }) => {
                    //TODO, how should this be generated
                    let fileFieldName = dependency.modelName + "-" + dependency.fieldName;
                    fetch(`/file-list/${appName}/unused/${fileFieldName}?${version}`).then(response => {
                        if(response.status !== 200) {
                            reject();
                        }
                        response.json().then(fileNameList => {
                            // TODO: does this filter need to be here?
                            if(this.pattern) {
                                fileNameList = (fileNameList || []).filter(fileName => fileName && !!fileName.match(this.pattern));
                            }
                            resolve(fileNameList);
                        })
                    })
                })
            })

            fileListPromise.then(updateFileNameList);
        }, [])

        // TODO: loading indicator
        // TODO: file upload

        let options = (fileNameList || []).map(fileName => (
            <option key={fileName} value={fileName}>{fileName}</option>
        ))

        return <Form.Select {...otherProps}>
            {options}
        </Form.Select>
    }
}

export class rsPartEnumStatefulComputeResult extends rsType {
    constructor({ isRequired, computeMethod, resultName }) {
        super({ isRequired });
        this.computeMethod = computeMethod;
        this.resultName = resultName;
    }

    validate = (value) => {
        // TODO
        return true;
    }

    inputComponent = (props) => {
        let contextFn = useContext;
        let stateFn = useState;
        let effectFn = useEffect;

        let appName = contextFn(ContextAppName);
        let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);

        let [optionList, updateOptionList] = stateFn(undefined);

        effectFn(() => {
            let enumOptionsPromise = new Promise((resolve, reject) => {
                simulationInfoPromise.then(({simulationId, version}) => {
                    pollStatefulCompute({
                        pollInterval: 500,
                        method: this.computeMethod,
                        appName,
                        simulationId,
                        callback: (respObj) => {
                            let result = respObj[this.resultName];
                            resolve(result);
                        }
                    })
                })
            })

            enumOptionsPromise.then(result => updateOptionList(result));
        }, [])

        // TODO: this is more of a mock element since this does not have
        // a working example right now
        return <Form.Select {...props}></Form.Select>
    }
}

export const partialTypes = {
    'File': (settings) => new rsFile(settings),
    'Enum': (settings) => {
        settings.allowedValues = (settings.allowedValues || []).map(allowedValue => {
            let [value, displayName] = allowedValue;
            return {
                value,
                displayName
            }
        })
        return new rsEnum(settings)
    },
    'StatefulComputeEnum': (settings) => new rsPartEnumStatefulComputeResult(settings)
}

export const globalTypes = {
    'OptionalString': new rsString({
        isRequired: false
    }),
    'String': new rsString({
        isRequired: true
    }),
    'Float': new rsFloat({ isRequired: true }),
    'OptionalFloat': new rsFloat({ isRequired: false }),
    'File': new rsFile({ isRequired:  true }),
    'OptionalFile': new rsFile({ isRequired: false }),
    'Text': new rsString({ isRequired: false }),
    'Integer': new rsInteger({ isRequired: true }),
    'OptionalInteger': new rsInteger({ isRequired: false }),
    'Boolean': new rsBoolean({ isRequired: true }),
    'OptionalBoolean': new rsBoolean({ isRequired: false })
}

export class rsEnum extends rsType {
    constructor({ isRequired, allowedValues }) {
        super({ isRequired });
        this.allowedValues = allowedValues;
    }

    inputComponent = (props) => {
        const options = this.allowedValues.map(allowedValue => (
            <option key={allowedValue.value} value={allowedValue.value}>{allowedValue.displayName}</option>
        ));
        return <Form.Select {...props}>
            {options}
        </Form.Select>
    }

    validate = (value) => {
        return (!this.isRequired) || (this.hasValue(value) && this.allowedValues.filter(av => av.value == value).length > 0);
    };
}
