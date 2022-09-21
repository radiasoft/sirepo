import { Nav , Modal, Button} from "react-bootstrap";
import { Routes, Route, Navigate, useRoutes, Outlet, Link } from "react-router-dom";
import { NavbarContainerId } from "../component/simulation";
import { ContextModelsWrapper, ContextRelativeFormController, ContextSimulationInfoPromise } from "../context";
import { useInterpolatedString } from "../hook/string";
import { useContext, useState } from "react";
import { View } from "./layout";
import usePortal from "react-useportal"; 
import { useStore } from "react-redux";
import { ViewPanelActionButtons } from "../component/panel";

export class NavBarModalButton extends View {
    getChildLayouts = (config) => {
        let { modal } = config;
        return modal.items.map(layoutConfig => {
            return {
                layout: this.layoutsWrapper.getLayoutForConfig(layoutConfig),
                config: layoutConfig
            }
        });
    }

    getFormDependencies = (config) => {
        return this.getChildLayouts(config).map(child => child.layout.getFormDependencies(child.config)).flat();
    }

    component = (props) => {
        let { config } = props;

        let models = useContext(ContextModelsWrapper);
        let title = useInterpolatedString(models, config.title);

        let [modalShown, updateModalShown] = useState(false);

        let formController = useContext(ContextRelativeFormController);
        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let modelsWrapper = useContext(ContextModelsWrapper);
        
        let store = useStore();

        let _cancel = () => {
            updateModalShown(false);
            formController.cancelChanges();
        }

        let _submit = () => {
            formController.saveToModels();
            simulationInfoPromise.then(simulationInfo => {
                modelsWrapper.saveToServer(simulationInfo, store.getState());
            })
        }

        let children = this.getChildLayouts(config).map((child, idx) => {
            let LayoutElement = child.layout.component;
            return <LayoutElement key={idx} config={child.config}></LayoutElement>
        })

        let isDirty = formController.isFormStateDirty();
        let isValid = formController.isFormStateValid();
        let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

        let { Portal: NavbarPortal } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        return (
            <>
                <NavbarPortal>
                    <Button onClick={() => updateModalShown(true)} variant="secondary">
                        {title}
                    </Button>
                </NavbarPortal>

                <Modal show={modalShown} onHide={() => _cancel()} size="lg">
                    <Modal.Header className="lead bg-info bg-opacity-25">
                        {title}
                    </Modal.Header>
                    <Modal.Body>
                        {children}
                        {isDirty && actionButtons}
                    </Modal.Body>
                </Modal>
            </>
        )
    }
}

export class NavTabsLayout extends View {
    getFormDependencies = (config) => {
        // TODO
        return [];
    }

    tabComponent = (props) => {
        let { tab } = props;

        let children = tab.items.map((layoutConfig, idx) => {
            let layout = this.layoutsWrapper.getLayoutForConfig(layoutConfig);
            let LayoutComponent = layout.component;
            return <LayoutComponent key={idx} config={layoutConfig}/>
        })

        return <>{children}</>;
    }

    component = (props) => {
        let { config } = props;
        let { tabs } = config;

        let modelsWrapper = useContext(ContextModelsWrapper);

        let { Portal: NavbarPortal } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        if(tabs.length == 0) {
            throw new Error("navtabs component contained no tabs");
        }

        let firstTabName = tabs[0].name;

        let routedElement = useRoutes([
            {
                path: '/',
                element: <Navigate to={`${firstTabName}`}></Navigate>
            },
            ...tabs.map(tab => {
                let TabComponent = this.tabComponent;

                return {
                    path: `${tab.name}`,
                    element: <TabComponent key={tab.name} tab={tab}></TabComponent>
                }
            })
        ])

        return (
            <>
                <NavbarPortal>
                    <Nav variant="tabs" >
                        {
                            tabs.map(tab => (
                                <Nav.Item key={tab.name}>
                                    <Nav.Link eventKey={`${tab.name}`} as={Link} href={`${tab.name}`} to={`${tab.name}`}>
                                        {useInterpolatedString(modelsWrapper, tab.title)}
                                    </Nav.Link>
                                </Nav.Item>
                            ))
                        }
                    </Nav>
                </NavbarPortal>

                {routedElement}
            </>
        )
    }
}
