import Elevator from "@/models/Elevator";
import { ServerCommand } from "@/models/Packet";
import WSEvent from "@/models/WSEvent";
import { Box, Typography } from "@mui/material";
import { useEffect } from "react";

export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    useEffect(() => {
        document.addEventListener('wsMessage', (event) => {
            const message = (event as WSEvent).message;
            if (message.command === ServerCommand.ADD_ELEVATOR) {
                console.log('add elevator');
            }
            else if (message.command === ServerCommand.REMOVE_ELEVATOR) {
                console.log('remove elevator');
            }
        })
    }, [])

    return <Box>{
        elevators.map(elevator => 
            <Typography>Elevator {elevator.id} at floor {elevator.currentFloor}{elevator.destinationFloor === null ? "" : `, going to ${elevator.destinationFloor}`}</Typography>
        )
    }
    </Box>
}