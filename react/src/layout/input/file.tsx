import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import React, { ChangeEventHandler, useEffect, useRef } from "react";
import { FunctionComponent, useContext, useState } from "react";
import { Button, Form, Modal } from "react-bootstrap";
import { CAppName } from "../../data/appwrapper";
import { interpolate } from "../../utility/string";
import { downloadAs } from "../../utility/download";
import { SchemaLayout } from "../../utility/schema";
import { LayoutProps } from "../layout";
import { LAYOUTS } from "../layouts";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";
import "./file.scss";
import { CRouteHelper } from "../../utility/route";
import { CHandleFactory } from "../../data/handle";
import { StoreTypes } from "../../data/data";
import { useSimulationInfo } from "../../hook/simulationInfo";

export type FileInputConfig = {
    pattern: string,
    inspectModal: { items: SchemaLayout[], title: string } // TODO: create modal type when this is used again
} & InputConfigBase

export class FileInputLayout extends InputLayout<FileInputConfig, string, string> {
    toModelValue: (value: string) => string = (v) => v;
    fromModelValue: (value: string) => string = (v) => v;

    validate = (value: string) => {
        // TODO
        return (!this.config.isRequired) || (this.hasValue(value) && value.length > 0);
    }

    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let { dependency, ...otherProps } = props;
        let [dummyState, updateDummyState] = useState({})

        let appName = useContext(CAppName);
        let routeHelper = useContext(CRouteHelper);
        let handleFactory = useContext(CHandleFactory);
        let simulationInfo = useSimulationInfo(handleFactory);

        let [modalShown, updateModalShown] = useState(false);
        let modal = this.config.inspectModal ? {
            items: this.config.inspectModal.items.map((schemaLayout: SchemaLayout, idx: number) => {
                let layout = LAYOUTS.getLayoutForSchema(schemaLayout);
                let Component = layout.component;
                return <Component key={idx}/>
            }),
            title: interpolate(this.config.inspectModal.title).withDependencies(handleFactory, StoreTypes.Models).raw()
        } : undefined;

        let [fileNameList, updateFileNameList] = useState(undefined);

        useEffect(() => {
            let fileListPromise = new Promise((resolve, reject) => {
                let { version } = simulationInfo;
                fetch(routeHelper.globalRoute("listFiles", {
                    simulation_type: appName,
                    simulation_id: "unused", // TODO ???
                    file_type: `${dependency.modelName + "-" + dependency.fieldName}?${version}` // TODO ???
                })).then(response => {
                    if(response.status !== 200) {
                        reject();
                    }
                    response.json().then(fileNameList => {
                        // TODO: does this filter need to be here?
                        if(this.config.pattern) {
                            fileNameList = (fileNameList || []).filter(fileName => fileName && !!fileName.match(this.config.pattern));
                        }
                        resolve(fileNameList);
                    })
                })
            })

            fileListPromise.then(updateFileNameList);
        }, [dummyState])

        // TODO: loading indicator
        // TODO: file upload

        let fileInputRef = useRef<HTMLInputElement>();
        let formSelectRef = useRef<HTMLSelectElement>();

        let options = [
            <option key={"default-file-option"} hidden>No file selected...</option>,
            ...(fileNameList || []).map(fileName => (
                <option key={fileName} value={fileName}>{fileName}</option>
            ))
        ]


        let uploadFile = (event) => {
            let file = event.target.files[0];
            let formData = new FormData();
            formData.append("file", file);
            let { simulationId } = simulationInfo;
            fetch(routeHelper.globalRoute("uploadFile", {
                simulation_type: appName,
                simulation_id: simulationId,
                file_type: dependency.modelName + "-" + dependency.fieldName
            }), {
                method: 'POST',
                body: formData
            }).then(resp => updateDummyState({}))
        }

        let downloadFile = () => {
            // TODO: do this better
            let selectedFileName = formSelectRef.current.selectedOptions[0].innerText;
            fetch(routeHelper.globalRoute("downloadFile", {
                simulation_type: appName,
                simulation_id: "unused",
                filename: `${dependency.modelName + "-" + dependency.fieldName}.${selectedFileName}`
            }))
            .then(res => res.blob())
            .then(res => {
                downloadAs(res, selectedFileName);
            });
        }

        let onChange: ChangeEventHandler<HTMLSelectElement> = (event) => {
            props.onChange(event.target.value);
        }

        return (
            <div className="sr-form-file-upload-row">
                <Form.Select ref={formSelectRef} {...otherProps} onChange={onChange}>
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
    };
}
