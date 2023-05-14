'use client';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2

import ElevatorStatusPanel from '@/components/ElevatorStatusPanel';
import ElevatorPanel from '@/components/ElevatorPanel';
import ControlPanel from '@/components/ControlPanel';
import StatsPanel from '@/components/StatsPanel';
import LogPanel from '@/components/LogPanel';

export default function Home() {
    return (
        <main>
            <h1 style={{"height": "6vh", "padding": 0, "margin": 0}}>Simulating elevators</h1>
            <Grid container sx={{
                height: "90vh",
                width: "100%",
            }}>
                <Grid container xs={12} sm={6} sx={{
                    flexDirection: "column"
                }}>
                    <Grid xs={8} sx={{
                        height: "67%",
                    }}>
                        <ElevatorPanel/>
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "33%",
                    }}>
                        <ControlPanel/>
                    </Grid>
                </Grid>
                <Grid xs={12} sm={2}>
                    <ElevatorStatusPanel/>
                </Grid>
                <Grid xs={12} sm={4}>
                    <Grid xs={8} sx={{
                        height: "40%",
                    }}>
                        <StatsPanel/>
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "60%",
                    }}>
                        <LogPanel/>
                    </Grid>
                </Grid>
            </Grid>
        </main>
    )
}
