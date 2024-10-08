import Elevator from "./Elevator";

class Load {
    initialFloor: number;
    destinationFloor: number;
    weight: number;
    elevator: Elevator;
    tickCreated: number;
    enterLiftTick: number | null = null;

    constructor(initialFloor: number, destinationFloor: number, weight: number, elevator: Elevator, tickCreated: number) {
        this.initialFloor = initialFloor;
        this.destinationFloor = destinationFloor;
        this.weight = weight;
        this.elevator = elevator;
        this.tickCreated = tickCreated;
    }
}

export default Load;