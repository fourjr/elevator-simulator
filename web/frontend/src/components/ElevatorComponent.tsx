import { Box, Card, Paper, Typography } from "@mui/material";
import { makeStyles } from "@mui/styles";
import Elevator from "@/models/Elevator";
import Grid from '@mui/material/Unstable_Grid2';

export default function ElevatorComponent({ elevator }: { elevator: Elevator }) {
    return <Grid xs={2}>
        <Card variant="outlined" sx={{padding: 1.5}}>
            <Typography>Elevator {elevator.id}</Typography>
            <Typography>{elevator.currentFloor}</Typography>
            {elevator.destinationFloor !== null && <Typography>
                →{elevator.destinationFloor}</Typography>
            }
            {elevator.loads.length} PAX
        </Card>
    </Grid>
}
