import {
    ContextModelsWrapper,
    ContextSimulationInfoPromise,
    ContextRelativeFormController,
} from "../context";
import { useContext } from "react";
import { useInterpolatedString } from "../hook/string";
import { View } from "./layout";
import { useStore } from "react-redux";
import { EditorPanel } from "../component/panel";
import "./panel.scss";
import { Col } from "react-bootstrap";

export class PanelLayout extends View {
    getChildLayoutByConfig = (layoutConfig) => {
        return {
            layout: this.layoutsWrapper.getLayoutForConfig(layoutConfig),
            config: layoutConfig
        }
    }

    getChildLayouts = (config) => {
        let { basic, advanced } = config;
        return [...(basic || []), ...(advanced || [])].map(this.getChildLayoutByConfig);
    }

    getFormDependencies = (config) => {
        return this.getChildLayouts(config).map(childLayout => childLayout.layout.getFormDependencies(childLayout.config)).flat();
    }

    component = (props) => {
        let { config } = props;
        let { basic, advanced } = config;

        if(!config) {
            throw new Error("view missing config: " + config.name);
        }

        let modelsWrapper = useContext(ContextModelsWrapper);
        let formController = useContext(ContextRelativeFormController);
        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);

        let store = useStore();

        let title = useInterpolatedString(modelsWrapper, config.title);

        let mapLayoutConfigsToElements = (layoutConfigs) => layoutConfigs.map(this.getChildLayoutByConfig).map((child, idx) => {
            let LayoutComponent = child.layout.component;
            return <LayoutComponent key={idx} config={child.config}></LayoutComponent>;
        });

        let mainChildren = (!!basic) ? mapLayoutConfigsToElements(basic) : undefined;
        let modalChildren = (!!advanced) ? mapLayoutConfigsToElements(advanced) : undefined;

        let submit = () => {
            formController.saveToModels();
            simulationInfoPromise.then(simulationInfo => {
                modelsWrapper.saveToServer(simulationInfo, store.getState());
            })

        }

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: title || config.name,
            id: config.name
        }

        return (
            <Col md={6} xl={4} className="mb-3">
                <EditorPanel {...formProps}>
                </EditorPanel>
            </Col>
        )
    }
}
