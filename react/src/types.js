//import { React }
import { useContext, useEffect, useState } from "react";
import { Col, Form } from "react-bootstrap";
import { ContextAppName, ContextSimulationInfoPromise } from "./components/context";

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
        return true;
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
        if (this.isRequired) {
            return this.hasValue(value) && value.length > 0;
        }
        return true;
    }
}

export class rsNumber extends rsString {
    constructor(props) {
        super(props);
        this.align = "text-end";
    }
}

export class rsFloat extends rsNumber {
    static REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
    dbValue = (value) => {
        return Number.parseFloat(value);
    }
    validate = (value) => {
        return this.hasValue(value) && rsFloat.REGEXP.test(value);
    }
}

export class rsInteger extends rsNumber {
    static REGEXP = /^[-+]?\d+$/;
    dbValue = (value) => {
        return Number.parseInt(value);
    }
    validate = (value) => {
        return this.hasValue(value) && rsInteger.REGEXP.test(value);
    }
}

export class rsFile extends rsType {
    constructor({ isRequired }) {
        super({ isRequired })
    }

    dbValue = (value) => {
        return value;
    }

    validate = (value) => {
        // TODO
        return !!value && value.length > 0;
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
                simulationInfoPromise.then(simulationInfo => {
                    let { simulationId, version } = simulationInfo;
                    //TODO, how should this be generated
                    let fileFieldName = dependency.modelName + "-" + dependency.fieldName; 
                    fetch(`/file-list/${appName}/unused/${fileFieldName}?${version}`).then(response => {
                        if(response.status !== 200) {
                            reject();
                        }
                        response.json().then(fileNameList => {
                            resolve(fileNameList);
                        })
                    })
                })
            })

            fileListPromise.then(updateFileNameList);
        }, [])

        // TODO: loading indicator

        let options = (fileNameList || []).map(fileName => (
            <option key={fileName} value={fileName}>{fileName}</option>
        ))

        return <Form.Select {...otherProps}>
            {options}
        </Form.Select>
    }
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
    'OptionalInteger': new rsInteger({ isRequired: false })
}

export function enumTypeOf(allowedValues) {
    return new (class extends rsType {
        inputComponent = (props) => {
            const options = allowedValues.map(allowedValue => (
                <option key={allowedValue.value} value={allowedValue.value}>{allowedValue.displayName}</option>
            ));
            return <Form.Select {...props}>
                {options}
            </Form.Select>
        }
        validate = (value) => {
            return this.hasValue(value) && allowedValues.filter(av => av.value == value).length > 0;
        };
    })({});
}
