import { ServerCommand } from "@/models/Packet";
import WSEvent from "@/models/WSEvent";
import { Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { RegisterPacket } from "@/models/enums"

export default function ControlPanel({floors}: {floors: number}) {

    useEffect(() => {
        document.addEventListener('wsMessage', (event) => {
            const message = (event as WSEvent).message;
        })
    }, [])
    return <Typography>floors: {floors !== -1 ? floors : "loading" }</Typography>
}
