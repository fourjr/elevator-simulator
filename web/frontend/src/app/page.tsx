'use client';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2

import ElevatorStatusPanel from '@/components/ElevatorStatusPanel';
import ElevatorPanel from '@/components/ElevatorPanel';
import ControlPanel from '@/components/ControlPanel';
import StatsPanel from '@/components/StatsPanel';
import LogPanel from '@/components/LogPanel';
import { useMemo } from 'react';

import { ClientMessage, ServerMessage, ClientCommand, ServerCommand } from '@/models/message';

export default function Home() {
    const isBrowser = typeof window !== "undefined";
    const wsInstance = useMemo(() => isBrowser ? new WebSocket("ws://localhost:5555") : null, [isBrowser]);
    console.log('rerender')
    if (wsInstance) {
        wsInstance.onopen = () => {
            const registerMessage = new ClientMessage(ClientCommand.REGISTER)
            registerMessage.send(wsInstance);
        }
        wsInstance.onmessage = messageEvent => {
            messageEvent.data.arrayBuffer().then((data: ArrayBuffer) => {
                const message = new ServerMessage(data);
                console.log(`Message received from server: ${ServerCommand[message.command]}`)
            });
        }
    }

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
                        <ElevatorPanel wsInstance={wsInstance}/>
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "33%",
                    }}>
                        <ControlPanel wsInstance={wsInstance}/>
                    </Grid>
                </Grid>
                <Grid xs={12} sm={2}>
                    <ElevatorStatusPanel wsInstance={wsInstance}/>
                </Grid>
                <Grid xs={12} sm={4}>
                    <Grid xs={8} sx={{
                        height: "40%",
                    }}>
                        <StatsPanel wsInstance={wsInstance}/>
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "60%",
                    }}>
                        <LogPanel wsInstance={wsInstance}/>
                    </Grid>
                </Grid>
            </Grid>
        </main>
    )
}
