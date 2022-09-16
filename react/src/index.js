import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { BrowserRouter } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.css';
import { RootRouter } from './component/root';
import { AppRoot } from './component/app';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
    <BrowserRouter>
        <RootRouter>
            <AppRoot/>
        </RootRouter>
    </BrowserRouter>
);
