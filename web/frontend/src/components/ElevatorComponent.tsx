import { Box, Card, Paper, Typography } from "@mui/material";
import Elevator from "@/models/Elevator";
import Grid from '@mui/material/Unstable_Grid2';
import React from "react";

export default function ElevatorComponent({ elevator }: { elevator: Elevator }) {
    return <Grid xs={2}>
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
