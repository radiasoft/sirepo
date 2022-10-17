import { Nav , Modal, Col, Row, Container } from "react-bootstrap";
import { Routes, Route, Navigate, useRoutes, Outlet, Link, useResolvedPath, useParams } from "react-router-dom";
import { NavbarContainerId } from "../component/navbar";
import { ContextModelsWrapper, ContextRelativeFormController, ContextRelativeRouterHelper, ContextSimulationInfoPromise } from "../context";
import { useInterpolatedString } from "../hook/string";
import { useContext, useState } from "react";
import { View } from "./layout";
import usePortal from "react-useportal"; 
import { useStore } from "react-redux";
import { ViewPanelActionButtons } from "../component/panel";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { RouteHelper } from "../hook/route";

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
        let modalTitle = useInterpolatedString(models, config.modal.title);

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

        let { Portal: NavbarPortal, portalRef } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        if(portalRef && portalRef.current) {
            portalRef.current.classList.add("float-left");
            portalRef.current.classList.add("col");
        }

        let { icon } = config;
        let iconElement = undefined;
        if(icon && icon != "") {
            iconElement = <FontAwesomeIcon fixedWidth icon={Icon[icon]}></FontAwesomeIcon>;
        }

        // TODO fix button cursor on hover
        return (
            <>
                <NavbarPortal>
                    <Col>
                        <div onClick={() => updateModalShown(true)} variant="secondary">
                            <span>{title}<a className="ms-2">{iconElement}</a></span>
                        </div>
                    </Col>
                </NavbarPortal>

                <Modal show={modalShown} onHide={() => _cancel()} size="lg">
                    <Modal.Header className="lead bg-info bg-opacity-25">
                        {modalTitle}
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

    TabsContent = (props) => {
        let { tab, ...otherProps } = props;

        let children = tab.items.map((layoutConfig, idx) => {
            let layout = this.layoutsWrapper.getLayoutForConfig(layoutConfig);
            let LayoutComponent = layout.component;
            return <LayoutComponent key={idx} config={layoutConfig} {...otherProps}/>
        })

        return (
            <Container fluid className="mt-3">
                <Row>
                    {children}
                </Row>
            </Container>
        );
    }

    TabsSwitcher = (props) => {
        let { config } = props;
        let { tabs } = config;

        let { tabName: selectedTabName } = useParams();

        let modelsWrapper = useContext(ContextModelsWrapper);
        let routerHelper = useContext(ContextRelativeRouterHelper);

        let { Portal: NavbarPortal, portalRef } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        return (
            <>
                <NavbarPortal>
                    <Nav variant="tabs" defaultActiveKey={selectedTabName}>
                        {
                            tabs.map(tab => {
                                let route = routerHelper.getRelativePath(tab.name);
                                return (
                                    <Nav.Item key={tab.name}>
                                        <Nav.Link eventKey={`${tab.name}`} as={Link} href={`${tab.name}`} to={`${route}`}>
                                            {useInterpolatedString(modelsWrapper, tab.title)}
                                        </Nav.Link>
                                    </Nav.Item>
                                )
                            })
                        }
                    </Nav>
                </NavbarPortal>
                {
                    tabs.map(tab => (
                        <div key={tab.name} style={tab.name !== selectedTabName ? { display: 'none' } : undefined}>
                            <this.TabsContent key={tab.name} tab={tab}/>
                        </div>
                    ))
                }              
            </>
        )
    }

    component = (props) => {
        let { config } = props;
        let { tabs } = config;

        
        if(tabs.length == 0) {
            throw new Error("navtabs component contained no tabs");
        }

        let firstTabName = tabs[0].name;

        let location = useResolvedPath('');

        let routeHelper = new RouteHelper(location);

        let routedElement = useRoutes([
            {
                path: '/',
                element: <Navigate to={`${firstTabName}`}></Navigate>
            },
            {
                path: '/:tabName/*',
                element: <this.TabsSwitcher config={config}/>
            }
        ])

        return (
            <ContextRelativeRouterHelper.Provider value={routeHelper}>
                {routedElement}
            </ContextRelativeRouterHelper.Provider> 
        )
    }
}
