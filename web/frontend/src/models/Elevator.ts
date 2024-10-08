import Load from "./Load";

class Elevator {
    id: number;
    currentFloor: number;
    loads: Load[] = [];
    enabled: boolean = true;
    destinationFloor: number | null = null;

    constructor(id: number, currentFloor: number) {
        this.id = id;
        this.currentFloor = currentFloor;
    }
}


export default Elevator;