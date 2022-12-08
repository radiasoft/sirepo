// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import React, { useState } from 'react';
import { Axis } from '@visx/visx';
import { format } from "d3-format";
import "./axis.scss";

export type DynamicAxisProps = {
    graphSize: number
} & Axis.SharedAxisProps<Axis.AxisScale>

export function DynamicAxis({ orientation, graphSize, ...props }: DynamicAxisProps) {
    const isX = orientation == 'bottom';
    const AxisType = isX ? Axis.AxisBottom : Axis.AxisLeft;
    const [ticks, setTicks] = useState(0);
    const t = Math.max(Math.round(graphSize / (isX ? 110 : 70)), 2);
    if (t != ticks) {
        setTicks(t);
    }
    return (
        <>
            <AxisType
                stroke={"#888"}
                tickStroke={"#888"}
                tickFormat={format(",.2e")}
                labelClassName={"sr-axis-label"}
                tickLabelProps={() => ({
                    fontSize: 13,
                    textAnchor: isX ? "middle" : "end",
                    verticalAnchor: "middle",
                })}
                numTicks={ticks}
                labelOffset={isX ? 15 : 60}
                {...props}
            />
        </>
    )
}
