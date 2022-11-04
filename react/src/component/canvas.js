import React, { useRef, useState, useEffect } from "react";
import { CanvasContext } from "./canvascontext";

//TODO(pjm): use visx canvas when available
// code from https://codesandbox.io/s/xorr68vzqz?file=/src/Canvas.js
export function Canvas({ width, height, children, ...restProps }) {
    const canvasRef = useRef();
    const [state, setState] = useState(() => ({
        ref: canvasRef,
        getCtx: () => {}
    }));
    useEffect(
        () => {
            setState(() => ({
                ref: canvasRef,
                getCtx: () => {
                    return canvasRef.current.getContext("2d", { willReadFrequently: true });
                }
            }));
        },
        [state.ref]
    );
    return (
        <canvas ref={canvasRef} width={width} height={height} {...restProps}>
            <CanvasContext.Provider value={state}>
                {state.ref.current && children}
            </CanvasContext.Provider>
        </canvas>
    );
}
