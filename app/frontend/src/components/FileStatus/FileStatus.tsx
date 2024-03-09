// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import { useState, useEffect } from "react";
import { Dropdown, DropdownMenuItemType, IDropdownOption, IDropdownStyles } from '@fluentui/react/lib/Dropdown';
import { Stack,
    Dialog, 
    DialogType, 
    DialogFooter, 
    DefaultButton, 
    PrimaryButton } from "@fluentui/react";
import { DocumentsDetailList, IDocument } from "./DocumentsDetailList";
import { Delete24Regular,
    Send24Regular,
    ArrowClockwise24Filled
    } from "@fluentui/react-icons";
import { animated, useSpring } from "@react-spring/web";
import { getAllUploadStatus, FileUploadBasicStatus, GetUploadStatusRequest, FileState, getFolders, getTags } from "../../api";
import { deleteItem, DeleteItemRequest, resubmitItem, ResubmitItemRequest } from "../../api";

import styles from "./FileStatus.module.css";

const dropdownTimespanStyles: Partial<IDropdownStyles> = { dropdown: { width: 150 } };
const dropdownFileStateStyles: Partial<IDropdownStyles> = { dropdown: { width: 200 } };
const dropdownFolderStyles: Partial<IDropdownStyles> = { dropdown: { width: 200 } };
const dropdownTagStyles: Partial<IDropdownStyles> = { dropdown: { width: 200 } };

const dropdownTimespanOptions = [
    { key: 'Time Range', text: 'End time range', itemType: DropdownMenuItemType.Header },
    { key: '4hours', text: '4 hours' },
    { key: '12hours', text: '12 hours' },
    { key: '24hours', text: '24 hours' },
    { key: '7days', text: '7 days' },
    { key: '30days', text: '30 days' },
    { key: '-1days', text: 'All' },
  ];

const dropdownFileStateOptions = [
    { key: 'FileStates', text: 'File States', itemType: DropdownMenuItemType.Header },
    { key: FileState.All, text: 'All' },
    { key: FileState.Complete, text: 'Completed' },
    { key: FileState.Error, text: 'Error' },
    { key: FileState.Processing, text: 'Processing' },
    { key: FileState.Indexing, text: 'Indexing' },
    { key: FileState.Queued, text: 'Queued' },
    { key: FileState.Skipped, text: 'Skipped'},
    { key: FileState.UPLOADED, text: 'Uploaded'},
    { key: FileState.THROTTLED, text: 'Throttled'},    
    { key: FileState.DELETING, text: 'Deleting'},  
    { key: FileState.DELETED, text: 'Deleted'},  
  ];


interface Props {
    className?: string;
}

export const FileStatus = ({ className }: Props) => {
    const [selectedTimeFrameItem, setSelectedTimeFrameItem] = useState<IDropdownOption>();
    const [selectedFileStateItem, setSelectedFileStateItem] = useState<IDropdownOption>();
    const [SelectedFolderItem, setSelectedFolderItem] = useState<IDropdownOption>();
    const [SelectedTagItem, setSelectedTagItem] = useState<IDropdownOption>();
    const [folderOptions, setFolderOptions] = useState<IDropdownOption[]>([]);
    const [tagOptions, setTagOptions] = useState<IDropdownOption[]>([]);
    const [files, setFiles] = useState<IDocument[]>();
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const onTimeSpanChange = (event: React.FormEvent<HTMLDivElement>, item: IDropdownOption<any> | undefined): void => {
        setSelectedTimeFrameItem(item);
    };

    const onFileStateChange = (event: React.FormEvent<HTMLDivElement>, item: IDropdownOption<any> | undefined): void => {
        setSelectedFileStateItem(item);
    };

    const onFolderChange = (event: React.FormEvent<HTMLDivElement>, item: IDropdownOption<any> | undefined): void => {
        setSelectedFolderItem(item);
    };    

    const onTagChange = (event: React.FormEvent<HTMLDivElement>, item: IDropdownOption<any> | undefined): void => {
        setSelectedTagItem(item);
    };  

    const onFilesSorted = (items: IDocument[]): void => {
        setFiles(items);
    };

    const onGetStatusClick = async () => {
        setIsLoading(true);
        var timeframe = 4;
        switch (selectedTimeFrameItem?.key as string) {
            case "4hours":
                timeframe = 4;
                break;
            case "12hours":
                timeframe = 12;
                break;
            case "24hours":
                timeframe = 24;
                break;
            case "7days":
                timeframe = 168;
                break;
            case "30days":
                timeframe = 720;
                break;
            case "-1days":
                timeframe = -1;
                break;
            default:
                timeframe = 4;
                break;
        }

        const request: GetUploadStatusRequest = {
            timeframe: timeframe,
            state: selectedFileStateItem?.key == undefined ? FileState.All : selectedFileStateItem?.key as FileState,
            folder: SelectedFolderItem?.key == undefined ? 'Root' : SelectedFolderItem?.key as string,
            tag: SelectedTagItem?.key == undefined ? 'All' : SelectedTagItem?.key as string
        }
        const response = await getAllUploadStatus(request);
        const list = convertStatusToItems(response.statuses);
        setIsLoading(false);
        setFiles(list);
    }

    // Notification of processing
    // Define a type for the props of Notification component
    interface NotificationProps {
        message: string;
    }


    // *************************************************************
    // Resubmit processing
    // New state for managing resubmit dialog visibility and selected items
    const [isResubmitDialogVisible, setIsResubmitDialogVisible] = useState(false);
    const [selectedItemsForResubmit, setSelectedItemsForResubmit] = useState<IDocument[]>([]);

    const [notification, setNotification] = useState({ show: false, message: '' });

    const Notification = ({ message }: NotificationProps) => {
        // Ensure to return null when notification should not be shown
        if (!notification.show) return null;
    
        return <div className={styles.notification}>{message}</div>;
    };

    useEffect(() => {
        if (notification.show) {
            const timer = setTimeout(() => {
                setNotification({ show: false, message: '' });
            }, 3000); // Hides the notification after 3 seconds
            return () => clearTimeout(timer);
        }
    }, [notification]);



    // Function to open the resubmit dialog with selected items
    const showResubmitConfirmation = () => {
        // const selectedItems = selectionRef.current.getSelection() as IDocument[];
        // setSelectedItemsForResubmit(selectedItems);
        // setIsResubmitDialogVisible(true);
    };

    // Function to handle actual resubmission
    const handleResubmit = () => {
        setIsResubmitDialogVisible(false);
        console.log("Items to resubmit:", selectedItemsForResubmit);
        selectedItemsForResubmit.forEach(item => {
            console.log(`Resubmitting item: ${item.name}`);
            // resubmit this item
            const request: ResubmitItemRequest = {
                path: item.filePath
            }
            const response = resubmitItem(request);
        });
        // Notification after resubmission
        setNotification({ show: true, message: 'Processing resubmit. Hit \'Refresh\' to track progress' });
    };
    

    // *************************************************************
    // Delete processing
    // New state for managing dialog visibility and selected items
    const [isDeleteDialogVisible, setIsDeleteDialogVisible] = useState(false);
    const [selectedItemsState, setSelectedItemsState] = useState<IDocument[]>([]);

    const onSelectionChange = (selectedItems: IDocument[]) => {
        console.log("incoming selectedItems", selectedItems);
        setSelectedItemsState(selectedItems);
    };

    useEffect(() => {
        console.log("user effect selectedItemsState:", selectedItemsState);
    }, [selectedItemsState]);

    // Function to open the dialog with selected items
    const showDeleteConfirmation = () => {
        setIsDeleteDialogVisible(true);
    };

    // Sandbox to demo empty array
    const handleDelete = () => {
        console.log("Items to delete:", selectedItemsState);
    };    


    // // Function to handle actual deletion
    // const handleDelete = () => {
    //     setIsDeleteDialogVisible(false);
    //     console.log("Items to delete:", selectedItemsState);
    //     selectedItemsState.forEach(item => {
    //         console.log(`Deleting item: ${item.name}`);
    //         // delete this item
    //         const request: DeleteItemRequest = {
    //             path: item.filePath
    //         }
    //         const response = deleteItem(request);
    //     });
    //     // Notification after deletion
    //     setNotification({ show: true, message: 'Processing deletion. Hit \'Refresh\' to track progress' });
    // };    

    // Function to handle the delete button click
    const handleDeleteClick = () => {
        showDeleteConfirmation();
    };

    // ********************************************************************

    // fetch unique folder names from Azure Blob Storage
    const fetchFolders = async () => {
        try {
            const folders = await getFolders(); // Await the promise
            const rootOption = { key: 'Root', text: 'Root' }; // Create the "Root" option            
            const folderDropdownOptions = [rootOption, ...folders.map((folder: string) => ({ key: folder, text: folder }))];
            setFolderOptions(folderDropdownOptions);
        }
        catch (e) {
            console.log(e);
        }
    };

    // fetch unique tag names from Azure Cosmos DB
    const fetchTags = async () => {
        try {
            const tags = await getTags(); // Await the promise
            const AllOption = { key: 'All', text: 'All' }; // Create the "ALL" option            
            const TagsDropdownOptions = [AllOption, ...tags.map((tag: string) => ({ key: tag, text: tag }))];
            setTagOptions(TagsDropdownOptions);
        }
        catch (e) {
            console.log(e);
        }
    };



    // Effect to fetch folders & tags on mount
    useEffect(() => {
        fetchFolders();
        fetchTags();        
    }, []);

    function convertStatusToItems(fileList: FileUploadBasicStatus[]) {
        const items: IDocument[] = [];
        for (let i = 0; i < fileList.length; i++) {
            let fileExtension = fileList[i].file_name.split('.').pop();
            fileExtension = fileExtension == undefined ? 'Folder' : fileExtension.toUpperCase()
            try {
                items.push({
                    key: fileList[i].id,
                    name: fileList[i].file_name,
                    iconName: FILE_ICONS[fileExtension.toLowerCase()],
                    fileType: fileExtension,
                    filePath: fileList[i].file_path,
                    state: fileList[i].state,
                    state_description: fileList[i].state_description,
                    upload_timestamp: fileList[i].start_timestamp,
                    modified_timestamp: fileList[i].state_timestamp,
                    status_updates: fileList[i].status_updates.map(su => ({
                        status: su.status,
                        status_timestamp: su.status_timestamp,
                        status_classification: su.status_classification,
                    })),
                    value: fileList[i].id,
                    tags: fileList[i].tags
                });
            }
            catch (e) {
                console.log(e);
            }
        }
        return items;
    }

    const FILE_ICONS: { [id: string]: string } = {
        "csv": 'csv',
        "docx": 'docx',
        "pdf": 'pdf',
        "pptx": 'pptx',
        "txt": 'txt',
        "html": 'xsn'
    };

    const animatedStyles = useSpring({
        from: { opacity: 0 },
        to: { opacity: 1 }
    });

    return (
        <div className={styles.container}>
            <div className={`${styles.options} ${className ?? ""}`} >
                <Dropdown
                        label="Uploaded in last:"
                        defaultSelectedKey='4hours'
                        onChange={onTimeSpanChange}
                        placeholder="Select a time range"
                        options={dropdownTimespanOptions}
                        styles={dropdownTimespanStyles}
                        aria-label="timespan options for file statuses to be displayed"
                    />
                <Dropdown
                        label="File State:"
                        defaultSelectedKey={'ALL'}
                        onChange={onFileStateChange}
                        placeholder="Select file states"
                        options={dropdownFileStateOptions}
                        styles={dropdownFileStateStyles}
                        aria-label="file state options for file statuses to be displayed"
                    />
                <Dropdown
                    label="Folder:"
                    defaultSelectedKey={'Root'}
                    onChange={onFolderChange}
                    placeholder="Select folder"
                    options={folderOptions}
                    styles={dropdownFolderStyles}
                    aria-label="folder options for file statuses to be displayed"
                />
                <Dropdown
                    label="Tag:"
                    defaultSelectedKey={'All'}
                    onChange={onTagChange}
                    placeholder="Select a tag"
                    options={tagOptions}
                    styles={dropdownTagStyles}
                    aria-label="tag options for file statuses to be displayed"
                />
                <div className={styles.refresharea} onClick={onGetStatusClick} aria-label="Refresh displayed file statuses">
                    <ArrowClockwise24Filled className={styles.refreshicon} />
                    <span className={styles.refreshtext}>Refresh</span>
                </div>
                <div className={styles.buttonsContainer}>
                <div className={styles.refresharea} onClick={onGetStatusClick} aria-label="Refresh displayed file statuses">
                    <ArrowClockwise24Filled className={styles.refreshicon} />
                    <span className={styles.refreshtext}>Refresh</span>
                </div>
                <div className={`${styles.refresharea} ${styles.divSpacing}`} onClick={handleDeleteClick} aria-label="Delete">
                    <Delete24Regular className={styles.refreshicon} />
                    <span className={`${styles.refreshtext} ${styles.centeredText}`}>Delete</span>
                </div>
                <div className={`${styles.refresharea} ${styles.divSpacing}`} onClick={onGetStatusClick} aria-label="Resubmit">
                    <Send24Regular className={styles.refreshicon} />
                    <span className={`${styles.refreshtext} ${styles.centeredText}`}>Resubmit</span>
                </div>
            </div>
            </div>
            {isLoading ? (
                <animated.div style={{ ...animatedStyles }}>
                     <Stack className={styles.loadingContainer} verticalAlign="space-between">
                        <Stack.Item grow>
                            <p className={styles.loadingText}>
                                Getting file statuses
                                <span className={styles.loadingdots} />
                            </p>
                        </Stack.Item>
                    </Stack>
                </animated.div>
            ) : (
                <div className={styles.resultspanel}>
                    <DocumentsDetailList items={files == undefined ? [] : files} 
                    onFilesSorted={onFilesSorted}
                    onSelectionChange={onSelectionChange}
                    />
                </div>
            )}
            {/* Dialog for delete confirmation */}
            <Dialog
                hidden={!isDeleteDialogVisible}
                onDismiss={() => setIsDeleteDialogVisible(false)}
                dialogContentProps={{
                    type: DialogType.normal,
                    title: 'Delete Confirmation',
                    subText: 'Are you sure you want to delete the selected items?'
                }}
                modalProps={{
                    isBlocking: true,
                    styles: { main: { maxWidth: 450 } }
                }}
            >
                <DialogFooter>
                    <PrimaryButton onClick={handleDelete} text="Delete" />
                    <DefaultButton onClick={() => setIsDeleteDialogVisible(false)} text="Cancel" />
                </DialogFooter>
            </Dialog>
            {/* Dialog for resubmit confirmation */}
            <Dialog
                hidden={!isResubmitDialogVisible}
                onDismiss={() => setIsResubmitDialogVisible(false)}
                dialogContentProps={{
                    type: DialogType.normal,
                    title: 'Resubmit Confirmation',
                    subText: 'Are you sure you want to resubmit the selected items?'
                }}
                modalProps={{
                    isBlocking: true,
                    styles: { main: { maxWidth: 450 } }
                }}
            >
                <DialogFooter>
                    <PrimaryButton onClick={handleResubmit} text="Resubmit" />
                    <DefaultButton onClick={() => setIsResubmitDialogVisible(false)} text="Cancel" />
                </DialogFooter>
            </Dialog>
            <div>
                <Notification message={notification.message} />
            </div>           







        </div>
    );
};