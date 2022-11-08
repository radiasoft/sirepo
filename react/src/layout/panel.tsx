import { useContext } from "react";
import { useInterpolatedString, ValueSelectors } from "../hook/string";
import { LayoutProps, View } from "./layout";
import { useStore } from "react-redux";
import { EditorPanel } from "../component/reusable/panel";
import "./panel.scss";
import { Col } from "react-bootstrap";
import React from "react";
import { CFormController } from "../data/formController";
import { CModelsWrapper } from "../data/wrapper";
import { CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { SchemaView } from "../utility/schema";

export type PanelConfig = {
    basic: SchemaView[],
    advanced: SchemaView[],
    title: string
}

export class PanelLayout extends View<PanelConfig> {
    getChildLayoutByConfig = (layoutConfig) => {
        return {
            layout: this.layoutsWrapper.getLayoutForName(layoutConfig.layout),
            config: layoutConfig.config
        }
    }

    getChildLayouts = (config) => {
        let { basic, advanced } = config;
        return [...(basic || []), ...(advanced || [])].map(this.getChildLayoutByConfig);
    }

    getFormDependencies = (config) => {
        return this.getChildLayouts(config).map(childLayout => childLayout.layout.getFormDependencies(childLayout.config)).flat();
    }

    component = (props: LayoutProps<PanelConfig>) => {
        let { config } = props;
        let { basic, advanced } = config;

        if(!config) {
            throw new Error("view missing config: " + this.name);
        }

        let modelsWrapper = useContext(CModelsWrapper);
        let formController = useContext(CFormController);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let schema = useContext(CSchema);

        let store = useStore();

        let title = useInterpolatedString(modelsWrapper, config.title, ValueSelectors.Models);

        let mapLayoutConfigsToElements = (layoutConfigs) => layoutConfigs.map(this.getChildLayoutByConfig).map((child, idx) => {
            let LayoutComponent = child.layout.component;
            return <LayoutComponent key={idx} config={child.config.config}></LayoutComponent>;
        });

        let mainChildren = (!!basic) ? mapLayoutConfigsToElements(basic) : undefined;
        let modalChildren = (!!advanced) ? mapLayoutConfigsToElements(advanced) : undefined;

        let submit = () => {
            formController.saveToModels();
            simulationInfoPromise.then(simulationInfo => {
                modelsWrapper.saveToServer(simulationInfo, Object.keys(schema.models), store.getState());
            })

        }

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: title || this.name,
            id: this.name
        }

        return (
            <Col md={6} xl={4} className="mb-3">
                <EditorPanel {...formProps}>
                </EditorPanel>
            </Col>
        )
    }
}
