import React from "react"
import { Route, Routes } from "react-router"

export const LoginWrapper = (props) => {
    return (
        <Routes>
            <Route path="/login/*" element={<LoginRoot/>}/>
            <Route path="/*" element={props.children}/>
        </Routes>
    )
}

export const LoginRoot = (props) => {
    return 
}
