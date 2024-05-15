// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import { Button, ButtonGroup } from "react-bootstrap";
import { Label } from "@fluentui/react";

import styles from "./ResponseLengthButtonGroup.module.css";

interface Props {
    className?: string;
    onClick: (_ev: any) => void;
    defaultValue?: number;
}

export const ResponseLengthButtonGroup = ({ className, onClick, defaultValue }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Label>Response length:</Label>
            <ButtonGroup className={`${styles.buttongroup ?? ""}`} onClick={onClick}>
                <Button id="Summarised" className={`${defaultValue == 256? styles.buttonleftactive : styles.buttonleft ?? ""}`} size="sm" value={256} bsPrefix='ia'>{"Summarised"}</Button>
                <Button id="Standard" className={`${defaultValue == 1024? styles.buttonmiddleactive : styles.buttonmiddle ?? ""}`} size="sm" value={1024} bsPrefix='ia'>{"Standard"}</Button>
                <Button id="Thorough" className={`${defaultValue == 2048? styles.buttonrightactive : styles.buttonright ?? ""}`} size="sm" value={2048} bsPrefix='ia'>{"Thorough"}</Button>
            </ButtonGroup>
        </div>
    );
};
