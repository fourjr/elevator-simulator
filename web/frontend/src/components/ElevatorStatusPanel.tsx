import { useEffect } from "react";
import { Typography } from "@mui/material";

import WSEvent from "@/models/WSEvent";

export default function ControlPanel({floors}: {floors: number}) {

    useEffect(() => {
        document.addEventListener('wsMessage', (event) => {
            const message = (event as WSEvent).packet;
        })
    }, [])
    return <Typography>floors: {floors !== -1 ? floors : "loading" }</Typography>
}
