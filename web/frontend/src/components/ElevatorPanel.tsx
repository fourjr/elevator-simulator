import { Box, Typography } from "@mui/material";
import Elevator from "@/models/Elevator";

export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    return <Box>{
        elevators.map(elevator => 
            <Typography key={elevator.id}>Elevator {elevator.id} at floor {elevator.currentFloor}{elevator.destinationFloor === null ? "" : `, going to ${elevator.destinationFloor}`}</Typography>
        )
    }
    </Box>
}