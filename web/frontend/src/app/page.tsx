'use client';
import { useMemo, useState } from 'react';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2

import ElevatorStatusPanel from '@/components/ElevatorStatusPanel';
import ElevatorPanel from '@/components/ElevatorPanel';
import ControlPanel from '@/components/ControlPanel';
import StatsPanel from '@/components/StatsPanel';
import LogPanel from '@/components/LogPanel';

import { ClientPacket, ServerPacket } from '@/models/Packet';
import { ElevatorAlgorithm, ElevatorPacket, GameState, RegisterPacket, OpCode, GameUpdateType } from '@/models/enums';
import Elevator from '@/models/Elevator';
import WSEvent from '@/models/WSEvent';
import Load from '@/models/Load';


export default function Home() {
    const [floors, setFloors] = useState<number>(-1);
    const [algorithm, setAlgorithm] = useState<ElevatorAlgorithm>(ElevatorAlgorithm.Destination_Dispatch);
    const [maxLoad, setMaxLoad] = useState<number>(900);
    const [simulationSpeed, setSimulationSpeed] = useState<number>(3);
    const [updateSpeed, setUpdateSpeed] = useState<number>(1);
    const [gameState, setGameState] = useState<GameState>(GameState.PAUSED);
    const [loads, setLoads] = useState<Load[]>([]);
    const [currentTick, setCurrentTick] = useState<number>(0);

    const [elevators, setElevators] = useState<Elevator[]>([]);
    const elevatorIds = elevators.map(e => e.id);

    const isBrowser = typeof window !== "undefined";
    const wsInstance = useMemo(() => isBrowser ? new WebSocket("ws://localhost:5555") : null, [isBrowser]);

    if (wsInstance) {
        wsInstance.onopen = () => {
            const registerMessage = new ClientPacket(OpCode.NEW_SIMULATION)
            registerMessage.send(wsInstance);
        }
        wsInstance.onmessage = messageEvent => {
            messageEvent.data.arrayBuffer().then((data: ArrayBuffer) => {
                const packet = new ServerPacket(data);
                console.log(`Message received from server: ${OpCode[packet.command]} ${packet.numData}`)

                switch (packet.command) {
                    case OpCode.NEW_SIMULATION:
                        setFloors(packet.readInt());
                        setMaxLoad(packet.readInt());
                        setAlgorithm(packet.readInt());
                        setSimulationSpeed(packet.readInt());
                        setUpdateSpeed(packet.readInt());
                        setGameState(GameState.PAUSED);
                        setElevators([]);
                        setLoads([]);
                        setCurrentTick(0);
                        break;

                        case OpCode.ADD_ELEVATOR:
                        const newElevator = new Elevator(
                            packet.readInt(),
                            packet.readInt(),
                        );
                        setElevators([...elevators, newElevator]);
                        break;
                    case OpCode.REMOVE_ELEVATOR:
                        const elevatorId = packet.readInt();
                        setElevators(elevators.filter(elevator => elevator.id !== elevatorId));
                        break;
                    case OpCode.SET_SIMULATION_SPEED:
                        setSimulationSpeed(packet.readInt() / 100);
                        break;
                    case OpCode.SET_UPDATE_SPEED:
                        setUpdateSpeed(packet.readInt() / 100);
                        break;
                    case OpCode.SET_ALGORITHM:
                        setAlgorithm(packet.readInt());
                        break;
                    case OpCode.SET_FLOORS:
                        setFloors(packet.readInt());
                        break;
                    case OpCode.SET_MAX_LOAD:
                        setMaxLoad(packet.readInt());
                        break;
                    case OpCode.ADD_PASSENGERS:
                        const count = packet.readInt();
                        const newLoads = [];
                        for (let i = 0; i < count; i++) {
                            const id = packet.readInt();
                            const floor_i = packet.readInt();
                            const floor_f = packet.readInt();
                            newLoads.push(new Load(id, floor_i, floor_f, currentTick));
                        }
                        setLoads([...loads, ...newLoads]);
                        break;
                    case OpCode.START_SIMULATION:
                        setGameState(GameState.RUNNING);
                        break;
                    case OpCode.STOP_SIMULATION:
                        setGameState(GameState.PAUSED);
                        break;
                    case OpCode.DASHBOARD:
                        console.log(packet.readString())
                        break;
                    case OpCode.GAME_UPDATE_STATE:
                        setCurrentTick(packet.readInt());

                        const numEvents = packet.readInt();

                        for (let i = 0; i < numEvents; i++) {
                            const updateType = packet.readInt() as GameUpdateType;
                            const elevatorId = packet.readInt();
                            const parameter = packet.readInt();

                            if (updateType === GameUpdateType.ELEVATOR_MOVE) {
                                const elevator = elevators.find(e => e.id === elevatorId)
                                if (elevator) {
                                    elevator.currentFloor = parameter;
                                }
                            }
                            else if (updateType === GameUpdateType.ELEVATOR_DESTINATION) {
                                const elevator = elevators.find(e => e.id === elevatorId)
                                if (elevator) {
                                    elevator.destinationFloor = parameter;
                                }
                            }
                            else if (updateType === GameUpdateType.LOAD_LOAD) {
                                const load = loads.find(l => l.id === parameter)
                                if (load) {
                                    const elevator = elevators.find(e => e.id === elevatorId)
                                    if (elevator) {
                                        load.elevator = elevator;
                                        elevator.loads.push(load);
                                    }
                                }
                            }
                            else if (updateType === GameUpdateType.LOAD_UNLOAD) {
                                const load = loads.find(l => l.id === parameter)
                                if (load) {
                                    const elevator = elevators.find(e => e.id === elevatorId)
                                    if (elevator) {
                                        elevator.loads = elevator.loads.filter(l => l.id !== parameter);
                                        setLoads(loads.filter(l => l.id !== parameter));
                                    }
                                }
                            }
                        }
                        break;
                    default:
                        console.log(`Unknown command: ${OpCode[packet.command]}`)
                        break;
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
                        maxHeight: "67vh",
                        overflow: "auto",
                        width: "100%"
                    }}>
                        <ElevatorPanel elevators={elevators} />
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "33%",
                        width: "100%"
                    }}>
                        <ControlPanel wsInstance={wsInstance} elevatorIds={elevatorIds} floors={floors} maxLoad={maxLoad} algorithm={algorithm} simulationSpeed={simulationSpeed} updateSpeed={updateSpeed} gameState={gameState} />
                    </Grid>
                </Grid>
                <Grid xs={12} sm={2} sx={{
                    maxHeight: "90vh",
                    overflow: "auto"
                }}>
                    <ElevatorStatusPanel floors={floors} loads={loads} />
                </Grid>
                <Grid xs={12} sm={4}>
                    <Grid xs={8} sx={{
                        height: "40%",
                    }}>
                        <StatsPanel currentTick={currentTick} />
                    </Grid>
                    <Grid xs={4} sx={{
                        height: "60%",
                    }}>
                        <LogPanel />
                    </Grid>
                </Grid>
            </Grid>
        </main>
    )
}
