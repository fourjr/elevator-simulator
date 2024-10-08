'use client';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2

import ElevatorStatusPanel from '@/components/ElevatorStatusPanel';
import ElevatorPanel from '@/components/ElevatorPanel';
import ControlPanel from '@/components/ControlPanel';
import StatsPanel from '@/components/StatsPanel';
import LogPanel from '@/components/LogPanel';
import { useMemo, useState } from 'react';

import { ClientMessage, ServerMessage, ClientCommand, ServerCommand } from '@/models/Packet';
import WSEvent from '@/models/WSEvent';
import { ElevatorAlgorithm, ElevatorPacket, RegisterPacket } from '@/models/enums';
import Elevator from '@/models/Elevator';

export default function Home() {
    const [floors, setFloors] = useState<number>(-1);
    const [algorithm, setAlgorithm] = useState<ElevatorAlgorithm>(ElevatorAlgorithm.DESTINATION_DISPATCH);
    const [maxLoad, setMaxLoad] = useState<number>(15);
    const [simulationSpeed, setSimulationSpeed] = useState<number>(3);
    const [updateSpeed, setUpdateSpeed] = useState<number>(1);

    const [elevators, setElevators] = useState<Elevator[]>([]);
    const elevatorIds = useMemo(() => elevators.map(e => e.id), [elevators.map(e => e.id)]);

    const isBrowser = typeof window !== "undefined";
    const wsInstance = useMemo(() => isBrowser ? new WebSocket("ws://localhost:5555") : null, [isBrowser]);

    if (wsInstance) {
        wsInstance.onopen = () => {
            const registerMessage = new ClientMessage(ClientCommand.REGISTER)
            registerMessage.send(wsInstance);
        }
        wsInstance.onmessage = messageEvent => {
            messageEvent.data.arrayBuffer().then((data: ArrayBuffer) => {
                const message = new ServerMessage(data);
                const event = new Event('wsMessage') as WSEvent;
                event.message = message;
                document.dispatchEvent(event);
                console.log(`Message received from server: ${ServerCommand[message.command]}`)

                if (message.command === ServerCommand.REGISTER) {
                    setFloors(message.data[RegisterPacket.floors]);
                    setMaxLoad(message.data[RegisterPacket.maxLoad]);
                    setAlgorithm(message.data[RegisterPacket.algorithm]);
                    setSimulationSpeed(message.data[RegisterPacket.simulationSpeed]);
                    setUpdateSpeed(message.data[RegisterPacket.updateSpeed]);
                }

                if (message.command === ServerCommand.ADD_ELEVATOR) {
                    const newElevator = new Elevator(
                        message.data[ElevatorPacket.id],
                        message.data[ElevatorPacket.currentFloor],
                    );
                    setElevators([...elevators, newElevator]);
                }

                if (message.command === ServerCommand.REMOVE_ELEVATOR) {
                    const elevatorId = message.data[ElevatorPacket.id];
                    setElevators(elevators.filter(elevator => elevator.id !== elevatorId));
                }
            });
        }
    }

    return (
        <main>
            <h1 style={{ "height": "6vh", "padding": 0, "margin": 0 }}>Simulating elevators</h1>
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
                        <ElevatorPanel elevators={elevators} />
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "33%",
                    }}>
                        <ControlPanel wsInstance={wsInstance} elevatorIds={elevatorIds} floors={floors} maxLoad={maxLoad} algorithm={algorithm} simulationSpeed={simulationSpeed} updateSpeed={updateSpeed} />
                    </Grid>
                </Grid>
                <Grid xs={12} sm={2}>
                    <ElevatorStatusPanel floors={floors} />
                </Grid>
                <Grid xs={12} sm={4}>
                    <Grid xs={8} sx={{
                        height: "40%",
                    }}>
                        <StatsPanel wsInstance={wsInstance} />
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "60%",
                    }}>
                        <LogPanel wsInstance={wsInstance} />
                    </Grid>
                </Grid>
            </Grid>
        </main>
    )
}
