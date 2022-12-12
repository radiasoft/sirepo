import React from "react"
import { Route, Routes } from "react-router"

export const LoginRouter = (props) => {
    return (
        <Routes>
            <Route path="/login/*" element={<LoginRoot/>}/>
            <Route path="/*" element={props.children}/>
        </Routes>
    )
}

export const LoginRoot = (props) => {
    return (
        <>LOGIN TEST</>
    )
}
