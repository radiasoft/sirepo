//import { React }
import { useContext, useEffect, useRef, useState } from "react";
import { Row, Button, Col, Form, Container, Modal } from "react-bootstrap";
import { ContextAppName, ContextLayouts, ContextModelsWrapper, ContextSimulationInfoPromise } from "./context";
import { pollStatefulCompute } from "./utility/compute";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import "./types.scss"
import { downloadAs } from "./utility/download";
import { useInterpolatedString } from "./hook/string";

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
        let ret = (value === "true" || value === true || value === "1") ? "1" : "0"; // TODO ???????? why arent these just booleans?
        return ret;
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
        let value = props.value == true || props.value == "true" || props.value === "1";
        return <Form.Check {...props} onChange={onChange} checked={value}></Form.Check>
    }
}

export class rsFile extends rsType {
    constructor({ isRequired, pattern, inspectModal }) {
        super({ isRequired })
        this.pattern = (pattern && new RegExp(pattern)) || undefined;
        this.inspectModal = inspectModal;
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
        let interpStrFn = useInterpolatedString;

        let [dummyState, updateDummyState] = stateFn({})

        let appName = contextFn(ContextAppName);
        let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);
        let layoutsWrapper = contextFn(ContextLayouts);
        let models = contextFn(ContextModelsWrapper);

        let [modalShown, updateModalShown] = stateFn(false);
        let modal = this.inspectModal ? {
            items: this.inspectModal.items.map((config, idx) => {
                let layout = layoutsWrapper.getLayoutForConfig(config);
                let Component = layout.component;
                return <Component key={idx} config={config}/>
            }),
            title: interpStrFn(models, this.inspectModal.title)
        } : undefined;

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
        }, [dummyState])

        // TODO: loading indicator
        // TODO: file upload

        let fileInputRef = useRef();
        let formSelectRef = useRef();

        let options = [
            <option hidden>No file selected...</option>,
            ...(fileNameList || []).map(fileName => (
                <option key={fileName} value={fileName}>{fileName}</option>
            ))
        ]
        

        let uploadFile = (event) => {
            let file = event.target.files[0];
            let formData = new FormData();
            formData.append("file", file);
            simulationInfoPromise.then(({ simulationId, version }) => {
                //TODO, how should this be generated
                let fileFieldName = dependency.modelName + "-" + dependency.fieldName;
                fetch(`/upload-file/${appName}/${simulationId}/${fileFieldName}`, {
                    method: 'POST',
                    body: formData
                }).then(resp => updateDummyState({}))
            })
        }

        let downloadFile = () => {
            // TODO: do this better
            let selectedFileName = formSelectRef.current.selectedOptions[0].innerText;
            let fileFieldName = dependency.modelName + "-" + dependency.fieldName;
            fetch(`/download-file/${appName}/unused/${fileFieldName}.${selectedFileName}`)
            .then(res => res.blob())
            .then(res => {
                downloadAs(res, selectedFileName);
            });
        }

        return (
            <div className="sr-form-file-upload-row">
                <Form.Select ref={formSelectRef} {...otherProps}>
                    {options}
                </Form.Select>
                <Button onClick={downloadFile}>
                    <FontAwesomeIcon icon={Icon.faDownload} fixedWidth/>
                </Button>
                {modal && <Button onClick={() => modal && updateModalShown(true)}>
                    <FontAwesomeIcon icon={Icon.faEye} fixedWidth/>
                </Button>}
                <input type="file" ref={fileInputRef} style={{display: 'none'}} onChange={uploadFile}></input>
                <Button onClick={() => {
                    return fileInputRef.current?.click()
                }}>
                    <FontAwesomeIcon icon={Icon.faPlus} fixedWidth/>
                </Button>

                {modal && <Modal show={modalShown} size="lg" onHide={() => updateModalShown(false)}>
                    <Modal.Header>
                        {modal.title}
                    </Modal.Header>
                    <Modal.Body>
                        {modal.items}
                    </Modal.Body>
                </Modal>}
            </div>
            
        )
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
