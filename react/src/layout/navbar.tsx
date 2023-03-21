import { Nav , Modal, Col, Row } from "react-bootstrap";
import { Navigate, useRoutes, Link, useResolvedPath, useParams } from "react-router-dom";
import { NavbarLeftContainerId, NavbarRightContainerId } from "../component/reusable/navbar";
import { interpolate, ValueSelectors } from "../utility/string";
import { useContext, useState } from "react";
import { LayoutProps, Layout } from "./layout";
import { useStore } from "react-redux";
import { ViewPanelActionButtons } from "../component/reusable/panel";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { CRelativeRouterHelper, RelativeRouteHelper } from "../utility/route";
import React from "react";
import { CFormController } from "../data/formController";
import { CModelsWrapper, ModelsWrapper } from "../data/wrapper";
import { CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { SchemaLayout } from "../utility/schema";
import { LAYOUTS } from "./layouts";
import { Portal } from "../component/reusable/portal";
import { formActionFunctions } from "../component/reusable/form";

export type NavBarModalButtonConfig = {
    modal: {
        title: string,
        items: SchemaLayout[]
    },
    title: string,
    icon: string
}

export class NavBarModalButton extends Layout<NavBarModalButtonConfig, {}> {
    children: Layout[];

    constructor(config: NavBarModalButtonConfig) {
        super(config);

        this.children = config.modal.items.map(schemaLayout => {
            return LAYOUTS.getLayoutForSchema(schemaLayout);
        });
    }

    getFormDependencies = () => {
        return this.children.map(child => child.getFormDependencies()).flat();
    }

    component = (props: LayoutProps<{}>) => {
        let formController = useContext(CFormController);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let modelsWrapper = useContext(CModelsWrapper);

        let title = interpolate(this.config.title).withDependencies(modelsWrapper, ValueSelectors.Models).raw();
        let modalTitle = interpolate(this.config.modal.title).withDependencies(modelsWrapper, ValueSelectors.Models).raw();

        let [modalShown, updateModalShown] = useState(false);

        let schema = useContext(CSchema);



        let store = useStore();

        let { submit: _submit, cancel: _cancel } = formActionFunctions(formController, store, simulationInfoPromise, schema, modelsWrapper as ModelsWrapper);

        let children = this.children.map((child, idx) => {
            let LayoutElement = child.component;
            return <LayoutElement key={idx}></LayoutElement>
        })

        let isDirty = formController.isFormStateDirty();
        let isValid = formController.isFormStateValid();
        let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

        let { icon } = this.config;
        let iconElement = undefined;
        if(icon && icon !== "") {
            iconElement = <FontAwesomeIcon fixedWidth icon={Icon[icon]}></FontAwesomeIcon>;
        }

        // TODO fix button cursor on hover
        return (
            <>
                <Portal targetId={NavbarLeftContainerId} className="order-2">
                    <Col>
                        <div onClick={() => updateModalShown(true)}>
                            <span>{title}<a className="ms-2">{iconElement}</a></span>
                        </div>
                    </Col>
                </Portal>

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
    items: SchemaLayout[]
}

export type NavTabsConfig = {
    tabs: NavTab[];
}

export type NavTabWithLayouts = {
    layouts: Layout[]
} & NavTab

export class NavTabsLayout extends Layout<NavTabsConfig, {}> {
    tabs: NavTabWithLayouts[]

    constructor(config: NavTabsConfig) {
        super(config);

        this.tabs = config.tabs.map(t => {
            return {
                ...t,
                layouts: t.items.map(LAYOUTS.getLayoutForSchema)
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
            <Row>
                {children}
            </Row>
        );
    }

    TabsSwitcher = (props: LayoutProps<{}>) => {
        let { tabName: selectedTabName } = useParams();

        let modelsWrapper = useContext(CModelsWrapper);
        let routerHelper = useContext(CRelativeRouterHelper);

        return (
            <>
                <Portal targetId={NavbarRightContainerId} className="order-1">
                    <Nav variant="tabs" defaultActiveKey={selectedTabName}>
                        {
                            this.tabs.map(tab => {
                                let route = routerHelper.getRelativePath(tab.name);
                                return (
                                    <Nav.Item key={tab.name}>
                                        <Nav.Link eventKey={`${tab.name}`} as={Link} href={`${tab.name}`} to={`${route}`}>
                                            {interpolate(tab.title).withDependencies(modelsWrapper, ValueSelectors.Models).raw()}
                                        </Nav.Link>
                                    </Nav.Item>
                                )
                            })
                        }
                    </Nav>
                </Portal>
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
        if(this.config.tabs.length === 0) {
            throw new Error("navtabs component contained no tabs");
        }

        let firstTabName = this.config.tabs[0].name;

        let location = useResolvedPath('');

        let routeHelper = new RelativeRouteHelper(location);

        let routedElement = useRoutes([
            {
                path: '/',
                element: <Navigate to={`${firstTabName}`}></Navigate>
            },
            {
                path: ':tabName/*',
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
