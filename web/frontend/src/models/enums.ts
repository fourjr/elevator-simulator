enum ElevatorAlgorithm {
    Destination_Dispatch = 0,
    FCFS = 1,
    LOOK = 2,
    NStepLOOK = 3,
    Rolling = 4,
    Scatter = 5,
}



enum OpCode {
    CLOSE = 0,
    ERROR = 1,

    NEW_SIMULATION = 2,
    START_SIMULATION = 3,
    STOP_SIMULATION = 4,

    ADD_ELEVATOR = 5,
    REMOVE_ELEVATOR = 6,
    ADD_PASSENGERS = 7,
    SET_FLOORS = 8,
    SET_ALGORITHM = 9,
    SET_SIMULATION_SPEED = 10,
    SET_UPDATE_SPEED = 11,
    SET_MAX_LOAD = 12,

    GAME_UPDATE_STATE = 13,

    DASHBOARD = 20,
}

enum GameUpdateType {
    ELEVATOR_MOVE = 0,
    ELEVATOR_DESTINATION = 1,
    LOAD_UNLOAD = 2,
    LOAD_LOAD = 3
}

enum GameState {
    RUNNING = 0,
    PAUSED = 1,
}

// PACKET STRUCTURE


enum RegisterPacket {
    floors = 0,
    maxLoad = 1,
    algorithm = 2,
    simulationSpeed = 3,
    updateSpeed = 4
}

enum ElevatorPacket {
    id = 0,
    currentFloor = 1,
}

export { ElevatorAlgorithm, RegisterPacket, ElevatorPacket, GameState, GameUpdateType, OpCode };