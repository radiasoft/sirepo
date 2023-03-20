import React from "react";
import { Col, Row } from "react-bootstrap";
import { LAYOUTS } from "./layouts";
import { LayoutProps, Layout } from "./layout";
import { ReportAnimationController, useAnimationReader } from "./report"
import { SchemaLayout } from "../utility/schema";
import { SimulationFrame } from "../data/report";
import { useWindowSize } from "../hook/breakpoint";

export type MultiPanelConfig = {
    items: SchemaLayout[],
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
        // allow subplots to respond to window resize
        useWindowSize();
        let animationReader = useAnimationReader(reportName, reportGroupName, frameIdFields);
        if (! animationReader) {
            return <></>
        }
        let showAnimationController = animationReader.getFrameCount() > 1;
        let mapLayoutsToComponents = (views: Layout[], currentFrameIndex: number) => views.map((child, idx) => {
            let LayoutComponent = child.component;
            return (
                <Col sm="4" key={idx} className="p-0">
                    <LayoutComponent key={idx} currentFrameIndex={currentFrameIndex}></LayoutComponent>
                </Col>
            );
        });
        return (
            <Row className="ps-3 pt-3">
                <ReportAnimationController
                    animationReader={animationReader}
                    showAnimationController={showAnimationController}
                    currentFrameIndex={undefined}
                >
                    {
                        (currentFrame: SimulationFrame) => {
                            let mainChildren = mapLayoutsToComponents(this.items, currentFrame.index);
                            return <>
                                {mainChildren}
                            </>
                        }
                    }
                </ReportAnimationController>
            </Row>
        )
    }
}
