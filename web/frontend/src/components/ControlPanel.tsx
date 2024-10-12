import React, { useEffect, useState } from "react";
import { Box, Button, MenuItem, Select, SelectChangeEvent, TextField, Typography } from "@mui/material";
import Grid from '@mui/material/Unstable_Grid2';

import { ElevatorAlgorithm, GameState, OpCode } from "@/models/enums";
import { ClientPacket } from "@/models/Packet";
import { clamp, getEnumKeys } from "@/utils";


export default function ControlPanel(
    { wsInstance, elevatorIds, floors: floorCount,
        maxLoad, algorithm, simulationSpeed, updateRate, gameState
    }: {
        wsInstance: WebSocket | null, elevatorIds: number[],
        floors: number, algorithm: ElevatorAlgorithm, maxLoad: number,
        simulationSpeed: number, updateRate: number, gameState: GameState
    }) {

    const [newElevatorFloor, setNewElevatorFloor] = useState(1);
    const [removeElevatorId, setRemoveElevatorId] = useState(1);
    const [addPassengerStartFloor, setAddPassengerStartFloor] = useState(1);
    const [addPassengerEndFloor, setAddPassengerEndFloor] = useState(2);
    const [addRandomPassengerCount, setAddRandomPassengerCount] = useState<number | null>(50);

    const [floorInput, setFloorInput] = useState<number | null>(floorCount);
    const [maxLoadInput, setMaxLoadInput] = useState<number | null>(maxLoad);
    const [simulationSpeedInput, setSimulationSpeedInput] = useState<string>(simulationSpeed.toFixed(2));
    const [updateRateInput, setUpdateRateInput] = useState<string>(updateRate.toString());

    useEffect(() => {
        if (elevatorIds.length > 0) {
            setRemoveElevatorId(elevatorIds[0]);
        }
    }, [elevatorIds])

    useEffect(() => {
        setFloorInput(floorCount);
        setMaxLoadInput(maxLoad);
        setSimulationSpeedInput(simulationSpeed.toFixed(2));
        setUpdateRateInput(updateRate.toString());
    }, [floorCount, maxLoad, simulationSpeed, updateRate])

    function addElevator() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(OpCode.ADD_ELEVATOR, [newElevatorFloor]);
            packet.send(wsInstance);
        }
    }

    function removeElevator() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(OpCode.REMOVE_ELEVATOR, [removeElevatorId]);
            packet.send(wsInstance);
        }
    }

    function addPassenger() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(OpCode.ADD_PASSENGERS, [1, addPassengerStartFloor, addPassengerEndFloor]);
            packet.send(wsInstance);
        }
    }

    function addRandomPassengers() {
        if (wsInstance !== null && addRandomPassengerCount !== null) {
            const count = addRandomPassengerCount;
            let values = [count];
            let floor_i, floor_f;
            for (let i = 0; i < count; i++) {
                floor_i = Math.floor(Math.random() * floorCount) + 1;
                while ((floor_f = Math.floor(Math.random() * floorCount) + 1) === floor_i);
                values.push(floor_i, floor_f);
            }
            const packet = new ClientPacket(OpCode.ADD_PASSENGERS, values);
            packet.send(wsInstance);
        }
    }

    function changeAlgorithm(algorithmName: keyof typeof ElevatorAlgorithm) {
        if (wsInstance !== null) {
            const algorithm_id: number = ElevatorAlgorithm[algorithmName];
            const packet = new ClientPacket(OpCode.SET_ALGORITHM, [algorithm_id]);
            packet.send(wsInstance);
        }
    }

    function FloorsInputField({ value, setValue }: { value: number, setValue: (value: number) => void }) {
        return <TextField sx={{ width: `${floorCount.toString().length}ch` }} value={value} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
            let val = clamp(parseInt(event.target.value), 1, floorCount);
            if (isNaN(val)) {
                val = 1;
            }
            setValue(val);
        }} variant="standard" />
    }

    function togglePlay() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(gameState === GameState.RUNNING ? OpCode.STOP_SIMULATION : OpCode.START_SIMULATION);
            packet.send(wsInstance);
        }
    }

    function sendReset() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(OpCode.NEW_SIMULATION);
            packet.send(wsInstance);
        }
    }

    function updateCol2() {
        if (wsInstance !== null) {
            if (floorInput !== floorCount && floorInput !== null) {
                const packet = new ClientPacket(OpCode.SET_FLOORS, [floorInput]);
                packet.send(wsInstance);
            }
            if (maxLoadInput !== maxLoad && maxLoadInput !== null) {
                const packet = new ClientPacket(OpCode.SET_MAX_LOAD, [maxLoadInput]);
                packet.send(wsInstance);
            }
            let simSpeedFloat = parseFloat(simulationSpeedInput);
            if (0.01 <= simSpeedFloat && simSpeedFloat <= 100 && simSpeedFloat !== simulationSpeed) {
                const packet = new ClientPacket(OpCode.SET_SIMULATION_SPEED, [Math.floor(simSpeedFloat * 100)]);
                packet.send(wsInstance);
            }
            let updateRateInt = parseInt(updateRateInput);
            if (1 <= updateRateInt && updateRateInt <= 100 && updateRateInt !== updateRate) {
                const packet = new ClientPacket(OpCode.SET_UPDATE_RATE, [updateRateInt]);
                packet.send(wsInstance);
            }
        }
    }

    function getDashboard() {
        if (wsInstance !== null) {
            const packet = new ClientPacket(OpCode.DASHBOARD);
            packet.send(wsInstance);
        }
    }

    return <React.Fragment>
        <Grid container m={3} mt={0}>
            <Grid xs={7}>
                <Box m={1}>
                    <Typography m={1} display="inline">Elevator</Typography>
                    <FloorsInputField value={newElevatorFloor} setValue={setNewElevatorFloor} />
                    <Button onClick={addElevator}>Add</Button>
                    {elevatorIds.length > 0 &&
                        <Box display="inline" mx={1}>
                            <Select id="remove-elevator-id" variant="standard" value={removeElevatorId.toString()} onChange={(event: SelectChangeEvent) => {
                                setRemoveElevatorId(parseInt(event.target.value));
                            }}>
                                {elevatorIds.map(id => <MenuItem key={id} value={id.toString()}>{id}</MenuItem>)}
                            </Select>
                            <Button onClick={removeElevator}>Remove</Button>
                        </Box>
                    }
                </Box>
                <Box m={1}>
                    <Typography m={1} display="inline">PAX</Typography>
                    <FloorsInputField value={addPassengerStartFloor} setValue={setAddPassengerStartFloor} />
                    <Typography m={1} display="inline">→</Typography>
                    <FloorsInputField value={addPassengerEndFloor} setValue={setAddPassengerEndFloor} />
                    <Button onClick={addPassenger}>Add</Button>

                    <Box display="inline" p={1.5} style={{ border: "0.5px black dotted" }}>
                        <TextField sx={{ width: "3ch" }} value={addRandomPassengerCount !== null ? addRandomPassengerCount : ""} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                            let val: number | null = clamp(parseInt(event.target.value), 1, 100);
                            if (isNaN(val)) {
                                val = null;
                            }
                            setAddRandomPassengerCount(val);
                        }} variant="standard"></TextField>
                        <Button onClick={addRandomPassengers}>Random</Button>
                    </Box>

                </Box>
                <Box m={1}>
                    <Typography m={1} display="inline">Algorithm</Typography>
                    <Select id="algorithm-id" variant="standard" value={ElevatorAlgorithm[algorithm] !== undefined ? ElevatorAlgorithm[algorithm].toString() : ""} onChange={(event: SelectChangeEvent) => {
                        changeAlgorithm(event.target.value as keyof typeof ElevatorAlgorithm);
                    }}>
                        {getEnumKeys(ElevatorAlgorithm).map(name => <MenuItem key={name} value={name}>{name.replace("_", " ")}</MenuItem>)}
                    </Select>
                </Box>


                <Box>
                    <Button onClick={togglePlay}>{gameState === GameState.RUNNING ? "Pause" : "Play"}</Button>
                    <Button onClick={sendReset}>Reset</Button>
                </Box>
            </Grid>
            <Grid xs={5}>
                <Box m={1}>
                    <Typography m={1} display="inline">Floors</Typography>
                    <TextField sx={{ width: "4ch" }} value={floorInput !== null ? floorInput : ""} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                        let val: number | null = clamp(parseInt(event.target.value), 1, 100);
                        if (isNaN(val)) {
                            val = null;
                        }
                        setFloorInput(val);
                    }} variant="standard"></TextField>
                </Box>
                <Box m={1}>
                    <Typography m={1} display="inline">Max Load</Typography>
                    <TextField sx={{ width: "4ch" }} value={maxLoadInput !== null ? maxLoadInput / 60 : ""} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                        let val: number | null = clamp(parseInt(event.target.value), 1, 100);
                        if (isNaN(val)) {
                            val = null;
                        }
                        else {
                            val *= 60
                        }
                        setMaxLoadInput(val);
                    }} variant="standard"></TextField>
                </Box>
                <Box m={1}>
                    <Typography m={1} display="inline">Speed</Typography>
                    <TextField sx={{ width: "4ch" }} label="sim" value={simulationSpeedInput} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                        let val = parseFloat(event.target.value);
                        if (val < 0.01 || val > 100) {
                            setSimulationSpeedInput(clamp(val, 0.01, 100).toString());
                        }
                        else if (/[A-z]/g.test(event.target.value)) {
                            setSimulationSpeedInput("");
                        }
                        else {
                            setSimulationSpeedInput(event.target.value);
                        }
                    }} variant="standard"></TextField>
                    <Typography m={1} display="inline"></Typography>
                    <TextField sx={{ width: "5ch" }} label="tick/upd" value={updateRateInput} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                        let val = parseInt(event.target.value);
                        if (val < 1 || val > 100) {
                            setUpdateRateInput(clamp(val, 1, 100).toString());
                        }
                        else if (/[A-z]/g.test(event.target.value)) {
                            setUpdateRateInput("");
                        }
                        else {
                            setUpdateRateInput(event.target.value);
                        }
                    }} variant="standard"></TextField>
                </Box>

                <Button onClick={updateCol2}>Set</Button>
                <Button onClick={getDashboard}>Dashboard</Button>
            </Grid>
        </Grid>
    </React.Fragment>
}
