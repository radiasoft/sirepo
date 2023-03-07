import React from "react";
import { CModelsWrapper } from "../data/wrapper";
import { Col, Row } from "react-bootstrap";
import { LAYOUTS } from "./layouts";
import { LayoutProps, Layout } from "./layout";
import { Panel } from "../component/reusable/panel";
import { ReportAnimationController, useAnimationReader } from "./report"
import { SchemaLayout } from "../utility/schema";
import { useContext } from "react";
import { interpolate, ValueSelectors } from "../utility/string";
import { useWindowSize } from "../hook/breakpoint";

export type MultiPanelConfig = {
    items: SchemaLayout[],
    title: string,
    reportName: string,
    reportGroupName: string,
    frameIdFields: string[],
}

export class MultiPanelLayout extends Layout<MultiPanelConfig, {}> {
    items: Layout[];

    constructor(config: MultiPanelConfig) {
        super(config);
        this.items = config.items.map(LAYOUTS.getLayoutForSchema);
    }

    getFormDependencies = () => {
        return [...(this.items)].map(childLayout => childLayout.getFormDependencies()).flat();
    }

    component = (props: LayoutProps<{}>) => {
        let { reportName, reportGroupName, frameIdFields } = this.config;
        let modelsWrapper = useContext(CModelsWrapper);
        let title = interpolate(this.config.title).withDependencies(modelsWrapper, ValueSelectors.Models).raw();
        // allow subplots to respond to window resize
        useWindowSize();
        let animationReader = useAnimationReader(reportName, reportGroupName, frameIdFields);
        if (! animationReader) {
            return <></>
        }
        let showAnimationController = animationReader.getFrameCount() > 1;
        let mapLayoutsToComponents = (views: Layout[], currentFrameIndex) => views.map((child, idx) => {
            let LayoutComponent = child.component;
            return (
                <Col sm="4" key={idx}>
                    <LayoutComponent key={idx} currentFrameIndex={currentFrameIndex}></LayoutComponent>
                </Col>
            );
        });
        return (
            <Col sm={12} className="px-3 py-2">
                <Panel title={title} panelBodyShown={true}>
                    <Row>
                        <ReportAnimationController
                            animationReader={animationReader}
                            showAnimationController={showAnimationController}
                            currentFrameIndex={undefined}
                        >
                            {
                                (currentFrame: any) => {
                                    let mainChildren = mapLayoutsToComponents(this.items, currentFrame?.index);
                                    return <>
                                        {mainChildren}
                                    </>
                                }
                            }
                        </ReportAnimationController>
                    </Row>
                </Panel>
            </Col>
        )
    }
}
