import Elevator from "./Elevator";

class Load {
    initialFloor: number;
    destinationFloor: number;
    weight: number = 60;
    elevator: Elevator | null = null;
    tickCreated: number;
    enterLiftTick: number | null = null;

    constructor(initialFloor: number, destinationFloor: number, tickCreated: number) {
        this.initialFloor = initialFloor;
        this.destinationFloor = destinationFloor;
        this.tickCreated = tickCreated;
    }
}

export default Load;