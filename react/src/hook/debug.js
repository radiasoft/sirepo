import { 
    useRef,
    useEffect
} from "react";

export function useRenderCount(name) {
    const renderCount = useRef(0);
    const domRenderCount = useRef(0);
    ++renderCount.current;
    useEffect(() => {
        ++domRenderCount.current;
        //console.log(`DOM render ${name} ${domRenderCount.current} (${renderCount.current})`);
    })
    //console.log(`Render ${name} ${(++renderCount.current)}`);
}
