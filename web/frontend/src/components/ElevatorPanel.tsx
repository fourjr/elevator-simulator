import Grid from '@mui/material/Unstable_Grid2';

import ElevatorComponent from "@/components/ElevatorComponent";

import Elevator from "@/models/Elevator";


export default function ElevatorPanel({elevators}: {elevators: Elevator[]}) {
    return <Grid container spacing={3} m={1}>{
        elevators.map(elevator => <ElevatorComponent key={elevator.id} elevator={elevator} />)
    }
    </Grid>
}