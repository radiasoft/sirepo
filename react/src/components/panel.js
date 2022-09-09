import { Card, Modal, Col, Button, Form, Tab, Tabs } from "react-bootstrap";
import { useState, Fragment, useContext } from 'react';
import { useStore } from "react-redux";
import { FormController, FieldGridLayout, FieldListLayout } from "./form";
import { Dependency, HookedDependencyGroup } from "../dependency";
import {
    ContextRelativeHookedDependencyGroup,
    ContextRelativeFormController,
    ContextReduxFormActions,
    ContextReduxFormSelectors,
    ContextSimulationInfoPromise,
    ContextModels as ContextRelativeModels
} from "./context";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useRenderCount } from "../hooks";

import "./panel.scss";
import { SimulationLayout } from "./simulation";
import { Graph2dFromApi } from "./graph2d";

export function Panel(props) {
    let { title, buttons, panelBodyShown, ...otherProps } = props;
    return (
        <Card>
            <Card.Header className="lead bg-info bg-opacity-25">
                {title}
                <div className="float-end">
                    {buttons}
                </div>
            </Card.Header>
            {panelBodyShown &&
                <Card.Body>
                    {props.children}
                </Card.Body>
            }
        </Card>
    );
}

function ViewPanelActionButtons(props) {
    let { canSave, onSave, onCancel, ...otherProps } = props;
    return (
        <Col className="text-center sr-form-action-buttons" sm={12}>
            <Button onClick={onSave} disabled={!canSave} variant="primary">Save Changes</Button>
            <Button onClick={onCancel} variant="light" className="ms-1">Cancel</Button>
        </Col>
    )
}

function EditorForm(props) {
    return (
        <Form>
            {props.children}
        </Form>
    );
}

export function EditorPanel(props) {
    let {
        submit,
        cancel,
        showButtons,
        mainChildren,
        modalChildren,
        formValid,
        title,
        id
    } = props;

    useRenderCount("EditorPanel");

    let [advancedModalShown, updateAdvancedModalShown] = useState(false);
    let [panelBodyShown, updatePanelBodyShown] = useState(true);

    let hasModalChildren = !!modalChildren && modalChildren !== [];

    let headerButtons = (
        <Fragment>
            {hasModalChildren && <a className="ms-2" onClick={() => updateAdvancedModalShown(true)}><FontAwesomeIcon icon={Icon.faPencil} fixedWidth /></a>}
            <a className="ms-2" onClick={() => updatePanelBodyShown(!panelBodyShown)}><FontAwesomeIcon icon={panelBodyShown ? Icon.faChevronUp : Icon.faChevronDown} fixedWidth /></a>
        </Fragment>
    );

    let _cancel = () => {
        updateAdvancedModalShown(false);
        cancel();
    }

    let _submit = () => {
        updateAdvancedModalShown(false);
        submit();
    }

    let actionButtons = <ViewPanelActionButtons canSave={formValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

    // TODO: should this cancel changes on modal hide??
    return (
        <Panel title={title} buttons={headerButtons} panelBodyShown={panelBodyShown}>
            <EditorForm key={id}>
                {mainChildren}
            </EditorForm>

            {hasModalChildren && <Modal show={advancedModalShown} onHide={() => _cancel()} size="lg">
                <Modal.Header className="lead bg-info bg-opacity-25">
                    {title}
                </Modal.Header>
                <Modal.Body>
                    <EditorForm key={id}>
                        {modalChildren}
                    </EditorForm>
                    {showButtons &&
                        <Fragment>
                            {actionButtons}
                        </Fragment>
                    }
                </Modal.Body>
            </Modal>}
            {showButtons && actionButtons}
        </Panel>
    )
}

export let TabLayout = {
    getDependencies: (config) => {
        let fields = [];

        for (let tab of config.tabs) {
            for (let layoutConfig of tab.items) {
                let ele = elementForLayoutName(layoutConfig.layout);
                fields.push(...ele.getDependencies(layoutConfig));
            }
        }

        return fields;
    },

    element: (props) => {
        let { config } = props;

        let renderCountFn = useRenderCount;
        renderCountFn("TabLayout");

        let tabs = config.tabs;

        let tabEls = [];

        let firstTabKey = undefined;

        for (let tabConfig of tabs) {
            let name = tabConfig.name;
            let layouts = tabConfig.items;
            let layoutElements = layouts.map((layoutConfig, idx) => {
                let ele = elementForLayoutName(layoutConfig.layout)
                let LayoutElement = ele.element;
                return <LayoutElement key={idx} config={layoutConfig}></LayoutElement>
            })
            firstTabKey = firstTabKey || name;
            tabEls.push(
                <Tab key={name} eventKey={name} title={name}>
                    {layoutElements}
                </Tab>
            )
        }

        return (
            <Tabs defaultActiveKey={firstTabKey}>
                {tabEls}
            </Tabs>
        )
    }
}

function SpacedLayout(layoutElement) {
    let ChildElement = layoutElement.element;
    return {
        getDependencies: layoutElement.getDependencies,

        element: (props) => {
            let renderCountFn = useRenderCount;
            renderCountFn("SpacedLayout");

            return (
                <div className="sr-form-layout">
                    <ChildElement {...props} />
                </div>
            )
        }
    }
}

export let MissingLayout = {
    getDependencies: () => {
        return [];
    },

    element: (props) => {
        return <>Missing layout!</>;
    }
}

let layoutElements = {
    "fieldList": SpacedLayout(FieldListLayout),
    "fieldTable": SpacedLayout(FieldGridLayout),
    "tabs": TabLayout,
    "graph2d": SimulationLayout(Graph2dFromApi)
}

export function elementForLayoutName(layoutName) {
    return layoutElements[layoutName] || MissingLayout
}

export let ViewLayoutsPanel = ({ schema }) => ({ view, viewName }) => {
    let ViewLayoutsPanelComponent = (props) => {
        useRenderCount("ViewLayoutsPanel");

        let formActions = useContext(ContextReduxFormActions); // TODO: make these generic
        let formSelectors = useContext(ContextReduxFormSelectors);

        let models = useContext(ContextRelativeModels);

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);

        let store = useStore();

        let getModels = () => {
            return models.getModels(store.getState());
        }

        let saveToServer = (models) => {
            simulationInfoPromise.then((simulationInfo) => {
                simulationInfo.models = models;
                fetch("/save-simulation", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(simulationInfo)
                }).then(resp => {
                    // TODO: error handling
                    console.log("resp", resp);
                })
            })
        }

        let basic = view.config.basic || [];
        let advanced = view.config.advanced || [];

        let dependencies = [...basic, ...advanced].map(layoutConfig => {
            let ele = elementForLayoutName(layoutConfig.layout);
            return ele.getDependencies(layoutConfig);
        }).flat().map(dependencyString => new Dependency(dependencyString));

        let hookedDependencyGroup = new HookedDependencyGroup({ schemaModels: schema.models, models, dependencies });

        let hookedDependencies = dependencies.map(hookedDependencyGroup.getHookedDependency);

        let formController = new FormController({ formActions, formSelectors, hookedDependencies });

        let submit = () => {
            let models = getModels();
            formController.submitChanges();
            saveToServer(models);
        }

        let mapLayoutToElement = (layoutConfig, idx) => {
            let ele = elementForLayoutName(layoutConfig.layout);
            let LayoutElement = ele.element;
            return <LayoutElement key={idx} config={layoutConfig}></LayoutElement>;
        }

        let mainChildren = (!!basic) ? basic.map(mapLayoutToElement) : undefined;
        let modalChildren = (!!advanced) ? advanced.map(mapLayoutToElement) : undefined;

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: view.title || viewName,
            id: { viewName }
        }

        return (
            <ContextRelativeHookedDependencyGroup.Provider value={hookedDependencyGroup}>
                <ContextRelativeFormController.Provider value={formController}>
                    <EditorPanel {...formProps}>
                    </EditorPanel>
                </ContextRelativeFormController.Provider>
            </ContextRelativeHookedDependencyGroup.Provider>
        )
    }
    return ViewLayoutsPanelComponent;
}
