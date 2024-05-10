// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    { text: "What are Capitec's main sources of income?", value: "What are Capitec's main sources of income?" },
    { text: "Give a breakdown of Capitec's profatibility during 2021.", value: "Give a breakdown of Capitec's profatibility during 2021." },
    { text: "What are some of the current economic challenges?", value: "What are some of the current economic challenges?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
