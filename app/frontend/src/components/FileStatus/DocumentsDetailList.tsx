// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import React, { useState, useEffect, useRef, useLayoutEffect } from "react";

import { DetailsList, 
    DetailsListLayoutMode, 
    SelectionMode, 
    IColumn, 
    Selection, 
    TooltipHost,
    Button,
    DefaultButton, 
    Panel,
    PanelType} from "@fluentui/react";
import { retryFile } from "../../api";
import styles from "./DocumentsDetailList.module.css";
import { StatusContent } from "../StatusContent/StatusContent";

export interface IDocument {
    key: string;
    name: string;
    value: string;
    iconName: string;
    fileType: string;
    filePath: string;
    state: string;
    state_description: string;
    upload_timestamp: string;
    modified_timestamp: string;
    status_updates: Array<{
        status: string;
        status_timestamp: string;
        status_classification: string;
    }>;
    isSelected?: boolean; // Optional property to track selection state
    tags: string;
}


interface Props {
    items: IDocument[];
    onFilesSorted?: (items: IDocument[]) => void;
    onSelectionChange?: (selectedItems: IDocument[]) => void;
}

export const DocumentsDetailList = ({ items, onFilesSorted, onSelectionChange}: Props) => {
    const itemsRef = useRef(items);

    const onColumnClick = (ev: React.MouseEvent<HTMLElement>, column: IColumn): void => {
        const newColumns: IColumn[] = columns.slice();
        const currColumn: IColumn = newColumns.filter(currCol => column.key === currCol.key)[0];
        newColumns.forEach((newCol: IColumn) => {
            if (newCol === currColumn) {
                currColumn.isSortedDescending = !currColumn.isSortedDescending;
                currColumn.isSorted = true;
            } else {
                newCol.isSorted = false;
                newCol.isSortedDescending = true;
            }
        });
        const newItems = copyAndSort(items, currColumn.fieldName!, currColumn.isSortedDescending);
        items = newItems as IDocument[];
        setColumns(newColumns);
        onFilesSorted == undefined ? console.log("onFileSorted event undefined") : onFilesSorted(items);
    };

    function copyAndSort<T>(items: T[], columnKey: string, isSortedDescending?: boolean): T[] {
        const key = columnKey as keyof T;
        return items.slice(0).sort((a: T, b: T) => ((isSortedDescending ? a[key] < b[key] : a[key] > b[key]) ? 1 : -1));
    }

    function getKey(item: any, index?: number): string {
        return item.key;
    }

    function onItemInvoked(item: any): void {
        alert(`Item invoked: ${item.name}`);
    }

    const [itemList, setItems] = useState<IDocument[]>(items);
    function retryErroredFile(item: IDocument): void {
        retryFile(item.filePath)
            .then(() => {
                // Create a new array with the updated item
                const updatedItems = itemList.map((i) => {
                    if (i.key === item.key) {
                        return {
                            ...i,
                            state: "Queued"
                        };
                    }
                    return i;
                });
    
                setItems(updatedItems); // Update the state with the new array
                console.log("State updated, triggering re-render");
            })
            .catch((error) => {
                console.error("Error retrying file:", error);
            });
    }
    
    // Initialize Selection with items
    useEffect(() => {
        selectionRef.current.setItems(itemList, false);
    }, [itemList]);

    const selectionRef = useRef(new Selection({
        onSelectionChanged: () => {
            const selectedItems = selectionRef.current.getSelection() as IDocument[];
            setItems(prevItems => prevItems.map((item, index) => ({
                ...item,
                isSelected: selectedItems.includes(item)
            })));
    
            if (onSelectionChange) {
                onSelectionChange(selectedItems);
            }
        }
    }));
    




    // State detail dialog
    const [value, setValue] = useState('Initial value');
    const [stateDialogVisible, setStateDialogVisible] = useState(false);

    const refreshProp = (item: any) => {
        setValue(item);
      };

    const onStateColumnClick = (item: IDocument) => {
        try {
            refreshProp(item);
            setStateDialogVisible(true);
        } catch (error) {
            console.error("Error on state column click:", error);
            // Handle error here, perhaps show an error message to the user
        }
    };

    const dialogStyles = {
        main: {
            width: '400px',  // Set the width to 400 pixels
            maxWidth: '400px', // Set the maximum width to 400 pixels
            maxHeight: '400px', // Set the maximum height to 400 pixels
            overflowY: 'auto', // Enable vertical scrolling for the entire dialog if needed
        },
    };


    useEffect(() => {
        // Scroll to the top when the dialog opens
        window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    }, []);

    const [columns, setColumns] = useState<IColumn[]> ([
        {
            key: 'file_type',
            name: 'File Type',
            className: styles.fileIconCell,
            iconClassName: styles.fileIconHeaderIcon,
            ariaLabel: 'Column operations for File type, Press to sort on File type',
            iconName: 'Page',
            isIconOnly: true,
            fieldName: 'name',
            minWidth: 16,
            maxWidth: 16,
            onColumnClick: onColumnClick,
            onRender: (item: IDocument) => (
                <TooltipHost content={`${item.fileType} file`}>
                    <img src={"https://res-1.cdn.office.net/files/fabric-cdn-prod_20221209.001/assets/item-types/16/" + item.iconName + ".svg"} className={styles.fileIconImg} alt={`${item.fileType} file icon`} />
                </TooltipHost>
            ),
        },
        {
            key: 'name',
            name: 'Name',
            fieldName: 'name',
            minWidth: 210,
            maxWidth: 350,
            isRowHeader: true,
            isResizable: true,
            sortAscendingAriaLabel: 'Sorted A to Z',
            sortDescendingAriaLabel: 'Sorted Z to A',
            onColumnClick: onColumnClick,
            data: 'string',
            isPadded: true,
        },
        {
            key: 'state',
            name: 'State',
            fieldName: 'state',
            minWidth: 70,
            maxWidth: 90,
            isResizable: true,
            ariaLabel: 'Column operations for state, Press to sort by states',
            onColumnClick: onColumnClick,
            data: 'string',
            onRender: (item: IDocument) => (
                <TooltipHost content={`${item.state} `}>
                    <span onClick={() => onStateColumnClick(item)} style={{ cursor: 'pointer' }}>
                        {item.state_description}
                    </span>
                </TooltipHost>
            ),
            isPadded: true,
        },
        {
            key: 'folder',
            name: 'Folder',
            fieldName: 'folder',
            minWidth: 70,
            maxWidth: 90,
            isResizable: true,
            ariaLabel: 'Column operations for folder, Press to sort by folder',
            onColumnClick: onColumnClick,
            data: 'string',
            onRender: (item: IDocument) => (  
                <TooltipHost content={`${item.state} `}>  
                    <span>{item.filePath.split('/').slice(1, -1).join('/')}</span>  
                    {item.filePath === 'Error' && <a href="javascript:void(0);" onClick={() => retryErroredFile(item)}> Retry File</a>}  
                </TooltipHost>  
            ), 
        },
        {
            key: 'tags',
            name: 'Tags',
            fieldName: 'tags',
            minWidth: 70,
            maxWidth: 90,
            isRowHeader: true,
            isResizable: true,
            sortAscendingAriaLabel: 'Sorted A to Z',
            sortDescendingAriaLabel: 'Sorted Z to A',
            onColumnClick: onColumnClick,
            data: 'string',

            isPadded: true,
        },
        {
            key: 'upload_timestamp',
            name: 'Submitted On',
            fieldName: 'upload_timestamp',
            minWidth: 90,
            maxWidth: 120,
            isResizable: true,
            isCollapsible: true,
            ariaLabel: 'Column operations for submitted on date, Press to sort by submitted date',
            data: 'string',
            onColumnClick: onColumnClick,
            onRender: (item: IDocument) => {
                return <span>{item.upload_timestamp}</span>;
            },
            isPadded: true,
        },
        {
            key: 'modified_timestamp',
            name: 'Last Updated',
            fieldName: 'modified_timestamp',
            minWidth: 90,
            maxWidth: 120,
            isResizable: true,
            isSorted: true,
            isSortedDescending: false,
            sortAscendingAriaLabel: 'Sorted Oldest to Newest',
            sortDescendingAriaLabel: 'Sorted Newest to Oldest',
            isCollapsible: true,
            ariaLabel: 'Column operations for last updated on date, Press to sort by last updated date',
            data: 'number',
            onColumnClick: onColumnClick,
            onRender: (item: IDocument) => {
                return <span>{item.modified_timestamp}</span>;
            },
        },
        {
            key: 'state_description',
            name: 'Status Detail',
            fieldName: 'state_description',
            minWidth: 90,
            maxWidth: 200,
            isResizable: true,
            isCollapsible: true,
            ariaLabel: 'Column operations for status detail',
            data: 'string',
            onColumnClick: onColumnClick,
            onRender: (item: IDocument) => (
                <TooltipHost content={`${item.state_description} `}>
                    <span onClick={() => onStateColumnClick(item)} style={{ cursor: 'pointer' }}>
                        {item.state_description}
                    </span>
                </TooltipHost>
            )
        }
    ]);

    return (
        <div>
            <span className={styles.footer}>{"(" + items.length as string + ") records."}</span>
            <DetailsList
                items={itemList}
                compact={true}
                columns={columns}
                selection={selectionRef.current}
                selectionMode={SelectionMode.multiple} // Allow multiple selection
                getKey={getKey}
                setKey="none"
                layoutMode={DetailsListLayoutMode.justified}
                isHeaderVisible={true}
                onItemInvoked={onItemInvoked}
            />
            <span className={styles.footer}>{"(" + items.length as string + ") records."}</span>
            <Panel
                headerText="Status Log"
                isOpen={stateDialogVisible}
                isBlocking={false}
                onDismiss={() => setStateDialogVisible(false)}
                closeButtonAriaLabel="Close"
                onRenderFooterContent={() => <DefaultButton onClick={() => setStateDialogVisible(false)}>Close</DefaultButton>}
                isFooterAtBottom={true}
                type={PanelType.medium}
            >
                <div className={styles.resultspanel}>
                <StatusContent item={value} />
                </div>
            </Panel>
        </div>
    );
}