import Elevator from "@/models/Elevator";
import { ServerCommand } from "@/models/Packet";
import WSEvent from "@/models/WSEvent";
import { Box, Typography } from "@mui/material";
import { useEffect } from "react";

export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    return <Box>{
        elevators.map(elevator => 
            <Typography key={elevator.id}>Elevator {elevator.id} at floor {elevator.currentFloor}{elevator.destinationFloor === null ? "" : `, going to ${elevator.destinationFloor}`}</Typography>
        )
    }
    </Box>
}