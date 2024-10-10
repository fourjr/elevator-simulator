import { Box, Typography } from "@mui/material";
import Elevator from "@/models/Elevator";
import ElevatorComponent from "./ElevatorComponent";
import Grid from '@mui/material/Unstable_Grid2';

export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    return <Grid container spacing={3} m={1}>{
        elevators.map(elevator => <ElevatorComponent key={elevator.id} elevator={elevator} />)
    }
    </Grid>
}