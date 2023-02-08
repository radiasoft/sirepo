import React, { useState } from 'react';
import { Axis } from '@visx/visx';
import { format } from "d3-format";
import "./axis.scss";

export type DynamicAxisProps = {
    graphSize: number
} & Axis.SharedAxisProps<Axis.AxisScale>

const axisInfoByOrientation = {
    bottom: {
        type: Axis.AxisBottom,
        tickSpace: 110,
        anchor: "middle",
        labelOffset: 15,
    },
    left: {
        type: Axis.AxisLeft,
        tickSpace: 70,
        dx: -3,
        anchor: "end",
        labelOffset: 38,
    },
    right: {
        type: Axis.AxisRight,
        tickSpace: 70,
        dx: 3,
        anchor: "start",
        labelOffset: 63,
    }
};
export function DynamicAxis({ orientation, graphSize, ...props }: DynamicAxisProps) {
    const info = axisInfoByOrientation[orientation];
    const AxisType = info.type;
    const [ticks, setTicks] = useState(0);
    const t = Math.max(Math.round(graphSize / info.tickSpace), 2);
    if (t !== ticks) {
        setTicks(t);
    }

    const f = format(",.3e");
    function shortFormat(value) {
        return f(value).replace(/\.0+e/, 'e')
                       .replace(/0+e/, 'e')
                       .replace(/^e\+/, '');
    }
    return (
        <>
            <AxisType
                stroke={"#888"}
                tickStroke={"#888"}
                tickFormat={shortFormat}
                labelClassName={"sr-axis-label"}
                tickLabelProps={() => ({
                    fontSize: 13,
                    textAnchor: info.anchor,
                    verticalAnchor: "middle",
                    dx: info.dx || 0,
                })}
                numTicks={ticks}
                labelOffset={info.labelOffset}
                {...props}
            />
        </>
    )
}
