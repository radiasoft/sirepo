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
import { LAYOUTS } from "./layouts";

export type PanelConfig = {
    basic: SchemaView[],
    advanced: SchemaView[],
    title: string
}

export class PanelLayout extends View<PanelConfig, {}> {
    getChildLayouts = (): View<unknown, unknown>[] => {
        let { basic, advanced } = this.config;
        return [...(basic || []), ...(advanced || [])].map(LAYOUTS.getLayoutForSchemaView);
    }

    getFormDependencies = () => {
        return this.getChildLayouts().map(childLayout => childLayout.getFormDependencies()).flat();
    }

    component = (props: LayoutProps<{}>) => {
        let { basic, advanced } = this.config;

        let modelsWrapper = useContext(CModelsWrapper);
        let formController = useContext(CFormController);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let schema = useContext(CSchema);

        let store = useStore();

        let title = useInterpolatedString(modelsWrapper, this.config.title, ValueSelectors.Models);

        let mapLayoutConfigsToElements = (schemaViews: SchemaView[]) => schemaViews.map(LAYOUTS.getLayoutForSchemaView).map((child, idx) => {
            let LayoutComponent = child.component;
            return <LayoutComponent key={idx}></LayoutComponent>;
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
