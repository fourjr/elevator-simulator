import React from "react";
import { Card, Grid2 as Grid, Typography } from "@mui/material";

import Elevator from "@/models/Elevator";


export default function ElevatorComponent({ elevator }: { elevator: Elevator }) {
    return <Grid size={2}>
        <Card variant="outlined" sx={{padding: 1.5}}>
            <Typography>Elevator {elevator.id}</Typography>
            <Typography>{elevator.currentFloor}
                {elevator.destinationFloor !== null && elevator.currentFloor !== elevator.destinationFloor && <React.Fragment>
                    {' → '}{elevator.destinationFloor}</React.Fragment>
                }
            </Typography>
            <Typography>{elevator.loads.length} PAX</Typography>
        </Card>
    </Grid>
}
