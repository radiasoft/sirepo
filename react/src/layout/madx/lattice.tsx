import { ClipPath } from "@visx/visx";
import { Zoom } from "@visx/zoom";
import React, { useRef } from "react";
import { FunctionComponent } from "react";
import { useGraphContentBounds } from "../../utility/component";
import { Layout } from "../layout";

export type LatticeConfig = {}

export class LatticeLayout extends Layout<LatticeConfig> {
    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        const ref = useRef(null);
        const gc = useGraphContentBounds(ref, 9 / 16.0);
        
        return (
            <div ref={ref}>
                <Zoom<SVGRectElement>
                width={gc.width}
                height={gc.height}>
                    {(zoom) => {
                        let clipId = `graph-clip${Math.random()}`;
                        return (
                            <svg
                                style={{'userSelect': 'none'}}
                                viewBox={`${0} ${0} ${gc.contentWidth} ${gc.contentHeight}`}
                            >
                                <ClipPath.RectClipPath id={clipId} width={gc.width} height={gc.height}/>
                                {

                                }
                            </svg>
                        )
                    }}
                </Zoom>
            </div>
            
        )
    }
}

type BeamlineSettings = {
    flatten: boolean
}

type BeamlineElementProps<T> = {
    children?: React.ReactNode,
    type: string,
    settings: BeamlineSettings
} & T

const BeamlineElements: {[key: string]: FunctionComponent} = {
    /*bend: (props: BeamlineElementProps<{angle: number, length: number, enterEdge: number, exitEdge: number}>) => {
        var points = [
            [enter[0] - Math.sin(-enterEdge) * height / 2,
            enter[1] - Math.cos(-enterEdge) * height / 2],
            [enter[0] + Math.sin(-enterEdge) * height / 2,
            enter[1] + Math.cos(-enterEdge) * height / 2],
            [exit[0] + Math.sin(exitAngle) * height / 2,
            exit[1] + Math.cos(exitAngle) * height / 2],
            [exit[0] - Math.sin(exitAngle) * height / 2,
            exit[1] - Math.cos(exitAngle) * height / 2],
        ];
        // trim overlap if necessary
        if (length >= 0) {
            if (points[1][0] > points[2][0]) {
                points[1] = points[2] = lineIntersection(points);
            }
            else if (points[0][0] > points[3][0]) {
                points[0] = points[3] = lineIntersection(points);
            }
        }
        else {
            if (points[1][0] < points[2][0]) {
                points[1] = points[2] = lineIntersection(points);
            }
            else if (points[0][0] < points[3][0]) {
                points[0] = points[3] = lineIntersection(points);
            }
        }


        return (
            <g transform={`rotate()`}>
                <polygon>

                </polygon>
            </g>
        )
    }*/
}

// TODO: real implementation
const rpnValue = (x) => x;

function degreesToRadians(deg): number {
    return deg * Math.PI / 180;
}

function latticeFromData() {
    let rotate = (angle, x, y) => {
        var radAngle = degreesToRadians(angle);
        return {
            x: rpnValue(x) * Math.cos(radAngle) - rpnValue(y) * Math.sin(radAngle),
            y: rpnValue(x) * Math.sin(radAngle) + rpnValue(y) * Math.cos(radAngle)
        }
    }

    let itemTrackHash = (item, group, length, angle) => {
        return group.items.length + '-' + item.name + '-' + item._id + '-' + length + '-'
            + group.rotate + '-' + group.rotateX + '-' + group.rotateY + '-' + (angle || 0)
            + '-' + item.beamlineIndex + '-' + (item.elemedge || 0)
            + '-' + (item.open_side || '');
    }
}
