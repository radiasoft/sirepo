/**
 * @author Junaid Atari
 * @link https://gist.github.com/blacksmoke26/65f35ee824674e00d858047e852bd270
 *
 * Modified by AgainPsychoX to use TypeScript and `use-debounce` package.
 */

import { useState, useEffect } from 'react';
import { useDebouncedCallback } from "use-debounce";

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
 
export const resolveBreakpoint = (width: number): Breakpoint => {
    if (width < 576)  return 'xs';
    if (width < 768)  return 'sm';
    if (width < 992)  return 'md';
    if (width < 1200) return 'lg';
    if (width < 1440) return 'xl';
    return 'xxl';
};

export const useWindowSize = () => {
    const [size, setSize] = useState<number>(() => window.innerWidth);
    const update = useDebouncedCallback(() => {
        setSize(window.innerWidth);
    }, 200);

    useEffect(() => {
        window.addEventListener('resize', update);
        return () => window.removeEventListener('resize', update);
    }, [update]);

    return size;
}
 
export const useBreakpoint = () => {
    return resolveBreakpoint(useWindowSize());
};
