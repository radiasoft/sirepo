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

export function Panel(props) {
    let {title, buttons, panelBodyShown, ...otherProps} = props;
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
    let {canSave, onSave, onCancel, ...otherProps} = props;
    return (
        <Col className="text-center" sm={12}>
            <Button onClick={onSave} disabled={! canSave } variant="primary">Save Changes</Button>
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

    let [advancedModalShown, updateAdvancedModalShown] = useState(false);
    let [panelBodyShown, updatePanelBodyShown] = useState(true);

    let headerButtons = (
        <Fragment>
            <a className="ms-2" onClick={() => updateAdvancedModalShown(true)}><FontAwesomeIcon icon={Icon.faPencil} fixedWidth /></a>
            <a className="ms-2" onClick={() => updatePanelBodyShown(! panelBodyShown)}><FontAwesomeIcon icon={panelBodyShown ? Icon.faChevronUp : Icon.faChevronDown} fixedWidth /></a>
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
                    { title }
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

export function TabLayout(props) {
    let { config } = props;

    let tabs = config.tabs;

    let tabEls = [];

    let firstTabKey = undefined;

    for(let tabConfig of tabs) {
        let name = tabConfig.name;
        let layouts = tabConfig.items;
        firstTabKey = firstTabKey || name;
        tabEls.push(
            <Tab key={name} eventKey={name} title={name}>
                <ViewLayouts configs={layouts}/>
            </Tab>
        )
    }

    return (
        <Tabs defaultActiveKey={firstTabKey}>
            {tabEls}
        </Tabs>
    )
}

function SpacedLayout(layoutElement) {
    let ChildElement = layoutElement;
    return (props) => {
        return (
            <div className="sr-form-layout">
                <ChildElement {...props}/>
            </div>
        )
    }
}

export function MissingLayout(props) {
    return <>Missing layout!</>;
}

export function elementForLayoutName(layoutName) {
    switch(layoutName) {
        case "fieldList":
            return SpacedLayout(FieldListLayout);
        case "fieldTable":
            return SpacedLayout(FieldGridLayout);
        case "tabs":
            return TabLayout;
        default: 
            return MissingLayout;

    }
}

export function ViewLayout(props) {
    let { config } = props;
    let LayoutElement = elementForLayoutName(config.layout);
    return <LayoutElement config={config}></LayoutElement>
}

export function ViewLayouts(props) { 
    let { configs } = props;
    // uses index as a key only because schema wont change, bad practice otherwise!
    return <>
        {configs.map((config, idx) => <ViewLayout key={idx} config={config}/>)}
    </>
}

export let ViewLayoutsPanel = ({ schema }) => ({ view, viewName }) => {
    let ViewLayoutsPanelComponent = (props) => {
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

        let mainChildren = (!!basic) ? <ViewLayouts configs={basic}/> : undefined;
        let modalChildren = (!!advanced) ? <ViewLayouts configs={basic}/> : undefined;

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: view.title || viewName,
            id: {viewName}
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
