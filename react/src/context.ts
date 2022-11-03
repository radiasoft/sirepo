import React from 'react';
import { Schema } from './utility/schema';

export const CSimulationListPromise = React.createContext<Promise<any>>(undefined);
export const CSimulationInfoPromise = React.createContext<Promise<any>>(undefined);
export const CAppName = React.createContext<string>(undefined);
export const CSchema = React.createContext<Schema>(undefined);
