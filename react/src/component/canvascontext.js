import { createContext, useContext } from "react";

const CCanvas = createContext({ ctx: null });
const useCanvas = () => useContext(CCanvas).ref;
const useCanvasContext = () => useContext(CCanvas).getCtx();

//TODO(pjm): use visx canvas when available
//code from https://codesandbox.io/s/xorr68vzqz?file=/src/CanvasContext.js
export { CCanvas, useCanvas, useCanvasContext };
