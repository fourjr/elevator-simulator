import { Grid2 as Grid } from "@mui/material";

import ElevatorComponent from "@/components/ElevatorComponent";

import Elevator from "@/models/Elevator";


export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    return <Grid container spacing={3} m={1}>{
        elevators.map(elevator => <ElevatorComponent key={elevator.id} elevator={elevator} />)
    }
    </Grid>
}