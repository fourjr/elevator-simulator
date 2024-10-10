import Elevator from "./Elevator";

class Load {
    id: number;
    initialFloor: number;
    destinationFloor: number;
    weight: number = 60;
    elevator: Elevator | null = null;
    tickCreated: number;
    enterLiftTick: number | null = null;

    constructor(id: number, initialFloor: number, destinationFloor: number, tickCreated: number) {
        this.id = id;
        this.initialFloor = initialFloor;
        this.destinationFloor = destinationFloor;
        this.tickCreated = tickCreated;
    }
}

export default Load;