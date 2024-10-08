import { Box, Button, Typography } from "@mui/material";
import { useState } from "react";

export default function ControlPanel({wsInstance}: {wsInstance: WebSocket | null}) {

    const [playState, setPlayState] = useState(false);

    function togglePlay() {
        fetch('http://localhost:8899')
            .then((res) => {
                if (!res.ok) {
                    console.log('we have a problem')
                }
            }
            )
    }

    return <Box>
        <Typography>Control Panel</Typography>
        <Button onClick={togglePlay}>{playState ? "Pause" : "Play"}</Button>
    </Box>
}