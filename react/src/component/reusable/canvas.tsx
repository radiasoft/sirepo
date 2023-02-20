import React, { useRef, useState, useEffect, createContext, MutableRefObject } from "react";

export type CanvasContext = {
    ref: MutableRefObject<HTMLCanvasElement>,
    getCanvasContext: () => CanvasRenderingContext2D
}

export const CCanvas = createContext<CanvasContext>(undefined);

//TODO(pjm): use visx canvas when available
// code from https://codesandbox.io/s/xorr68vzqz?file=/src/CanvasContext.js
// code from https://codesandbox.io/s/xorr68vzqz?file=/src/Canvas.js
export function Canvas({ width, height, children, ...restProps }) {
    const canvasRef = useRef<HTMLCanvasElement>();
    const [ctx, setCtx] = useState<CanvasContext>(undefined);
    useEffect(
        () => {
            setCtx(() => ({
                ref: canvasRef,
                getCanvasContext: () => {
                    return canvasRef.current.getContext("2d", { willReadFrequently: true });
                }
            }));
        },
        [ctx?.ref]
    );
    return (
        <canvas ref={canvasRef} width={width} height={height} {...restProps}>
            <CCanvas.Provider value={ctx}>
                {ctx?.ref.current && children}
            </CCanvas.Provider>
        </canvas>
    );
}
