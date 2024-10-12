import React from "react";
import { Grid2 as Grid } from "@mui/material";

import Load from "@/models/Load";


interface FloorInfo {
    goingUp: number;
    goingDown: number;
}

export default function ElevatorStatusPanel({floors, loads}: {floors: number, loads: Load[]}) {
    const passengersInFloors: FloorInfo[] = [];
    for (let i = 0; i < floors; i++) {
        passengersInFloors.push({goingUp: 0, goingDown: 0})
    }
    for (const load of loads) {
        if (load.elevator === null) {
            if (load.initialFloor < load.destinationFloor) {
                passengersInFloors[load.initialFloor - 1].goingUp++
            } else {
                passengersInFloors[load.initialFloor - 1].goingDown++
            }
        }
    }

    return <Grid container m={2} rowSpacing={1}>
        <Grid size={4}></Grid>
        <Grid size={4}>↑</Grid>
        <Grid size={4}>↓</Grid>
        {passengersInFloors.map((floor, index) => {
            return <React.Fragment key={index}>
                <Grid size={4}>{index + 1}</Grid>
                <Grid size={4}>{floor.goingUp}</Grid>
                <Grid size={4}>{floor.goingDown}</Grid>
            </React.Fragment>
        })}
    </Grid>
}
