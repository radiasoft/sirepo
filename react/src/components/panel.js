import { Card, Modal, Col, Button, Form, Tab, Tabs } from "react-bootstrap";
import { useState, Fragment, useContext } from 'react';
import { useStore } from "react-redux";
import { FormController, FieldGridLayout, FieldListLayout } from "./form";
import { DependencyCollector } from "../dependency";
import {
    ContextRelativeDependencyCollector,
    ContextRelativeFormController,
    ContextReduxFormActions,
    ContextReduxFormSelectors,
    ContextReduxModelActions,
    ContextReduxModelSelectors,
    ContextSimulationInfoPromise
} from "./context";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useRenderCount } from "../hooks";

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
        <Col className="text-center" sm={12}>
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

    let headerButtons = (
        <Fragment>
            <a className="ms-2" onClick={() => updateAdvancedModalShown(true)}><FontAwesomeIcon icon={Icon.faPencil} fixedWidth /></a>
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

            <Modal show={advancedModalShown} onHide={() => _cancel()} size="lg">
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
            </Modal>
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

        console.log("TabLayout");

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
    "tabs": TabLayout
}

export function elementForLayoutName(layoutName) {
    console.log("layoutName", layoutName);
    return layoutElements[layoutName] || MissingLayout
}

/*export function ViewLayout(props) {
    let { config } = props;

    useRenderCount("ViewLayout");

    let LayoutElement = elementForLayoutName(config.layout);
    return <LayoutElement config={config}></LayoutElement>
}

export function ViewLayouts(props) { 
    let { configs } = props;

    useRenderCount("ViewLayouts");

    // uses index as a key only because schema wont change, bad practice otherwise!
    return <>
        {configs.map((config, idx) => <ViewLayout key={idx} config={config}/>)}
    </>
}*/

export let ViewLayoutsPanel = ({ schema }) => ({ view, viewName }) => {
    let ViewLayoutsPanelComponent = (props) => {
        useRenderCount("ViewLayoutsPanel");

        let formActions = useContext(ContextReduxFormActions); // TODO: make these generic
        let formSelectors = useContext(ContextReduxFormSelectors);
        let modelActions = useContext(ContextReduxModelActions);
        let modelSelectors = useContext(ContextReduxModelSelectors);

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);

        let store = useStore();

        let getModels = () => {
            console.log("state", store.getState());
            return modelSelectors.selectModels(store.getState());
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

        let dependencyCollector = new DependencyCollector({ modelActions, modelSelectors, schema });
        let formController = new FormController({ formActions, formSelectors, simulationInfoPromise });

        let submit = () => {
            let models = getModels();
            formController.submitChanges();
            saveToServer(models);
        }

        let basic = view.config.basic;
        let advanced = view.config.advanced;

        let mapLayoutToElement = (layoutConfig, idx) => {
            console.log("layout", layoutConfig);
            let ele = elementForLayoutName(layoutConfig.layout);
            ele.getDependencies(layoutConfig).map(depStr => formController.hookField(dependencyCollector.hookModelDependency(depStr)));
            let LayoutElement = ele.element;
            console.log("LayoutElement", LayoutElement);
            return <LayoutElement key={idx} config={layoutConfig}></LayoutElement>;
        }

        let mainChildren = (!!basic) ? basic.map(mapLayoutToElement) : undefined;
        let modalChildren = (!!advanced) ? advanced.map(mapLayoutToElement) : undefined;

        console.log("mainChildren", mainChildren);

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
            <ContextRelativeDependencyCollector.Provider value={dependencyCollector}>
                <ContextRelativeFormController.Provider value={formController}>
                    <EditorPanel {...formProps}>
                    </EditorPanel>
                </ContextRelativeFormController.Provider>
            </ContextRelativeDependencyCollector.Provider>
        )
    }
    return ViewLayoutsPanelComponent;
}
