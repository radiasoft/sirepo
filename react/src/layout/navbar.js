import { Nav , Modal, Tabs, Tab} from "react-bootstrap";
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

    component = (props) => {
        let { config } = props;
        let { tabs } = config;

        let modelsWrapper = useContext(ContextModelsWrapper);

        let { Portal: NavbarPortal } = usePortal({
            bindTo: document && document.getElementById(NavbarContainerId)
        })

        const ContentContainerId = "nav-content-container";

        let { Portal: ContentPortal } = usePortal({
            bindTo: document && document.getElementById(ContentContainerId)
        })

        if(tabs.length == 0) {
            throw new Error("navtabs component contained no tabs");
        }

        let firstTabName = tabs[0].name;

        return (
            <>
                <NavbarPortal>
                    <Tabs defaultActiveKey={firstTabName}>
                        {
                            tabs.map(tab => {
                                let children = tab.items.map((layoutConfig, idx) => {
                                    let layout = this.layoutsWrapper.getLayoutForConfig(layoutConfig);
                                    let LayoutComponent = layout.component;
                                    return <LayoutComponent key={idx} config={layoutConfig}/>
                                })
                
                                return (
                                    <Tab key={tab.name} eventKey={tab.name} title={useInterpolatedString(modelsWrapper, tab.title)}>
                                        <ContentPortal>
                                            {children}
                                        </ContentPortal>
                                    </Tab>
                                )
                            })
                        }
                    </Tabs>
                </NavbarPortal>
                
                <div id="nav-content-container">
                </div>
            </>
        )
    }
}
