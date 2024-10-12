import React from "react";
import { IconButton, Snackbar } from "@mui/material";
import { Close } from "@mui/icons-material";


export default function CustomSnackbar({ snackbarOpen, setSnackbarOpen, snackbarMessage, color="generic" }: { snackbarOpen: boolean, setSnackbarOpen: (open: boolean) => void, snackbarMessage: string, color?: "error" | "success" | "generic" }) {
    const action = (
        <React.Fragment>
            <IconButton
                size="small"
                aria-label="close"
                color="inherit"
                onClick={() => setSnackbarOpen(false)}
            >
                <Close fontSize="small" />
            </IconButton>
        </React.Fragment>
    );

    const bgColor = color === "error" ? "#ff3333" : color === "success" ? "#4a934a" : "primary.light";

    return <Snackbar
        open={snackbarOpen}
        autoHideDuration={1000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
        ContentProps={{
            sx: {
                backgroundColor: bgColor,
            }
        }} 
        action={action}
    />
}