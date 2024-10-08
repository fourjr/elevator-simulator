import { ElevatorAlgorithm } from "@/models/enums";
import { ClientCommand, ClientMessage, ServerMessage } from "@/models/Packet";
import { clamp } from "@/utils";
import { Box, Button, MenuItem, Select, SelectChangeEvent, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

export default function ControlPanel(
    { wsInstance, elevatorIds, floors,
        maxLoad, algorithm, simulationSpeed, updateSpeed
    }: { wsInstance: WebSocket | null, elevatorIds: number[],
        floors: number, algorithm: ElevatorAlgorithm, maxLoad: number,
        simulationSpeed: number, updateSpeed: number 
    }) {

    const [playState, setPlayState] = useState(false);
    const [newElevatorFloor, setNewElevatorFloor] = useState(1);
    const [removeElevatorId, setRemoveElevatorId] = useState(1);

    function togglePlay() {
        // const new ServerMessage
    }

    useEffect(() => {
        if (elevatorIds.length > 0) {
            setRemoveElevatorId(elevatorIds[0]);
        }
    }, [elevatorIds.length])

    function addElevator() {
        if (wsInstance !== null) {
            const message = new ClientMessage(ClientCommand.ADD_ELEVATOR, [newElevatorFloor]);
            message.send(wsInstance);
        }
    }

    function removeElevator() {
        if (wsInstance !== null) {
            const message = new ClientMessage(ClientCommand.REMOVE_ELEVATOR, [removeElevatorId]);
            message.send(wsInstance);
        }
    }

    return <Box>
        <Typography>Control Panel</Typography>
        Elevator
        <TextField sx={{width: "10ch"}} id="new-elevator-floor" value={newElevatorFloor} onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
            const val = clamp(parseInt(event.target.value), 1, floors);
            setNewElevatorFloor(val);
        }} label="floor" variant="outlined" />
        <Button onClick={addElevator}>Add</Button>
        <Select id="remove-elevator-id" value={removeElevatorId.toString()} onChange={(event: SelectChangeEvent) => {
            setRemoveElevatorId(parseInt(event.target.value));
        }}>
            {elevatorIds.map(id => <MenuItem key={id} value={id.toString()}>{id}</MenuItem>)}
        </Select>
        <Button onClick={removeElevator}>Remove</Button>
        <Button onClick={togglePlay}>{playState ? "Pause" : "Play"}</Button>
    </Box>
}
