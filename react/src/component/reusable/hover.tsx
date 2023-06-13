import React from "react";
import { useState } from "react";

export type Hover = {
    aquireHover: (id: any) => void;
    releaseHover: (id: any) => void;
    checkHover: (id: any) => boolean
}

export function HoverController(props: {
    children: (hover: Hover) => React.ReactNode
}) {
    let [hoveredId, updateHoveredId] = useState<any>(undefined);

    let hover: Hover = {
        aquireHover: (id: any) => updateHoveredId(id),
        releaseHover: (id: any) => (hoveredId === id ? updateHoveredId(undefined) : undefined),
        checkHover: (id: any) => hoveredId === id
    }

    return (
        <>
        {
            props.children && props.children(hover)
        }
        </>
    )
}
