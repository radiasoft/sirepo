import { Nav , Modal} from "react-bootstrap";
import { Routes, Route, Navigate, useRoutes, Outlet, Link } from "react-router-dom";
import { NavbarContainerId } from "../component/simulation";
import { ContextModelsWrapper } from "../context";
import { useInterpolatedString } from "../hook/string";
import { useContext, useState } from "react";
import { View } from "./layout";
import usePortal from "react-useportal"; 

/*export function NavBarModalButton(props) {
    let { config } = props;
    let { modal } = config;

    let models = useContext(ContextModelsWrapper);
    let title = useInterpolatedString(models, config.title);

    let [modalShown, updateModalShown] = useState(false);

    let _cancel = () => {
        updateModalShown(false);
        cancel();
    }

    modal.items.map(layoutConfig => {
        let LayoutElement = elementForLayoutName(layoutConfig.layout).element;
        // TODO unify form functionality
    })

    return (
        <Modal show={modalShown} onHide={() => _cancel()} size="lg">
            <Modal.Header className="lead bg-info bg-opacity-25">
                {title}
            </Modal.Header>
            <Modal.Body>

            </Modal.Body>
        </Modal>
    )
}*/

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
                                    <Nav.Link eventKey={`${tab.name}`} as={Link} to={`${tab.name}`}>
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
