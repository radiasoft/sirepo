import { Nav , Modal, Col, Row, Container } from "react-bootstrap";
import { Routes, Route, Navigate, useRoutes, Outlet, Link, useResolvedPath, useParams } from "react-router-dom";
import { NavbarContainerId } from "../component/reusable/navbar";
import { useInterpolatedString, ValueSelectors } from "../hook/string";
import { useContext, useState } from "react";
import { LayoutProps, View } from "./layout";
import usePortal from "react-useportal"; 
import { useStore } from "react-redux";
import { ViewPanelActionButtons } from "../component/reusable/panel";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { CRelativeRouterHelper, RouteHelper } from "../utility/route";
import React from "react";
import { CFormController } from "../data/formController";
import { CModelsWrapper } from "../data/wrapper";
import { CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { SchemaView } from "../utility/schema";
import { LAYOUTS } from "./layouts";

export type NavBarModalButtonConfig = {
    modal: {
        title: string,
        items: SchemaView[]
    },
    title: string,
    icon: string
}

export class NavBarModalButton extends View<NavBarModalButtonConfig, {}> {
    children: View[];

    constructor(config: NavBarModalButtonConfig) {
        super(config);

        this.children = config.modal.items.map(schemaView => {
            return LAYOUTS.getLayoutForSchemaView(schemaView);
        });
    }

    getFormDependencies = () => {
        return this.children.map(child => child.getFormDependencies()).flat();
    }

    component = (props: LayoutProps<{}>) => {
        let formController = useContext(CFormController);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let modelsWrapper = useContext(CModelsWrapper);

        let title = useInterpolatedString(modelsWrapper, this.config.title, ValueSelectors.Models);
        let modalTitle = useInterpolatedString(modelsWrapper, this.config.modal.title, ValueSelectors.Models);

        let [modalShown, updateModalShown] = useState(false);

        let schema = useContext(CSchema);

        
        
        let store = useStore();

        let _cancel = () => {
            updateModalShown(false);
            formController.cancelChanges();
        }

        let _submit = () => {
            formController.saveToModels();
            simulationInfoPromise.then(simulationInfo => {
                modelsWrapper.saveToServer(simulationInfo, Object.keys(schema.models), store.getState());
            })
        }

        let children = this.children.map((child, idx) => {
            let LayoutElement = child.component;
            return <LayoutElement key={idx}></LayoutElement>
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

        let { icon } = this.config;
        let iconElement = undefined;
        if(icon && icon != "") {
            iconElement = <FontAwesomeIcon fixedWidth icon={Icon[icon]}></FontAwesomeIcon>;
        }

        // TODO fix button cursor on hover
        return (
            <>
                <NavbarPortal>
                    <Col>
                        <div onClick={() => updateModalShown(true)}>
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

export type NavTab = {
    name: string,
    title: string,
    items: SchemaView[]
}

export type NavTabsConfig = {
    tabs: NavTab[];
}

export type NavTabWithLayouts = {
    layouts: View[]
} & NavTab

export class NavTabsLayout extends View<NavTabsConfig, {}> {
    tabs: NavTabWithLayouts[]

    constructor(config: NavTabsConfig) {
        super(config);

        this.tabs = config.tabs.map(t => {
            return {
                ...t,
                layouts: t.items.map(LAYOUTS.getLayoutForSchemaView)
            };

        })
    }

    getFormDependencies = () => {
        // TODO
        return [];
    }

    TabsContent = (props: { tab: NavTabWithLayouts }) => {
        let { tab, ...otherProps } = props;

        let children = tab.layouts.map((layout, idx) => {
            let LayoutComponent = layout.component;
            return <LayoutComponent key={idx} {...otherProps}/>
        })

        return (
            <Container fluid className="mt-3">
                <Row>
                    {children}
                </Row>
            </Container>
        );
    }

    TabsSwitcher = (props: LayoutProps<{}>) => {
        let { tabName: selectedTabName } = useParams();

        let modelsWrapper = useContext(CModelsWrapper);
        let routerHelper = useContext(CRelativeRouterHelper);

        let { Portal: NavbarPortal, portalRef } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        return (
            <>
                <NavbarPortal>
                    <Nav variant="tabs" defaultActiveKey={selectedTabName}>
                        {
                            this.tabs.map(tab => {
                                let route = routerHelper.getRelativePath(tab.name);
                                return (
                                    <Nav.Item key={tab.name}>
                                        <Nav.Link eventKey={`${tab.name}`} as={Link} href={`${tab.name}`} to={`${route}`}>
                                            {useInterpolatedString(modelsWrapper, tab.title, ValueSelectors.Models)}
                                        </Nav.Link>
                                    </Nav.Item>
                                )
                            })
                        }
                    </Nav>
                </NavbarPortal>
                {
                    this.tabs.map(tab => (
                        <div key={tab.name} style={tab.name !== selectedTabName ? { display: 'none' } : undefined}>
                            <this.TabsContent key={tab.name} tab={tab}/>
                        </div>
                    ))
                }              
            </>
        )
    }

    component = (props: LayoutProps<{}>) => {
        if(this.config.tabs.length == 0) {
            throw new Error("navtabs component contained no tabs");
        }

        let firstTabName = this.config.tabs[0].name;

        let location = useResolvedPath('');

        let routeHelper = new RouteHelper(location);

        let routedElement = useRoutes([
            {
                path: '/',
                element: <Navigate to={`${firstTabName}`}></Navigate>
            },
            {
                path: '/:tabName/*',
                element: <this.TabsSwitcher/>
            }
        ])

        return (
            <CRelativeRouterHelper.Provider value={routeHelper}>
                {routedElement}
            </CRelativeRouterHelper.Provider> 
        )
    }
}
