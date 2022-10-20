import { createContext, useContext } from "react";

const CanvasContext = createContext({ ctx: null });
const useCanvas = () => useContext(CanvasContext).ref;
const useCanvasContext = () => useContext(CanvasContext).getCtx();

//TODO(pjm): use visx canvas when available
//code from https://codesandbox.io/s/xorr68vzqz?file=/src/CanvasContext.js
export { CanvasContext, useCanvas, useCanvasContext };
