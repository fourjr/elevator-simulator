import { Md5 } from "ts-md5";


enum ClientCommand {
    ADD_ELEVATOR = 0,  // (int: current_floor)
    REMOVE_ELEVATOR = 1,  // (int: elevator_id)
    SET_FLOORS = 2,  // (int: floor_count)
    SET_SIMULATION_SPEED = 3,  // (int: speed)
    ADD_PASSENGER = 4,  // (int: initial, int: destination)
    ADD_PASSENGERS = 5,  // (int: count, (int: initial, int: destination) * count)
    SET_ALGORITHM = 6,  // TODO (int: algorithm_names)
    SET_MAX_LOAD = 7,  // (int: new_max_load)
    RESET = 8,
    PAUSE = 9,
    RESUME = 10,
    REGISTER = 11,
    ADD_LOAD = 12,  // (int: initial, int: destination, weight: int)
    REMOVE_LOAD = 13,  // (int: load_id)
    SET_SEED = 14,  // (int: seed)
    SET_UPDATE_SPEED = 15,  // (int: update_speed)
}

enum ServerCommand {
    REGISTER = 0,
    ACK = 1,
    CLOSE = 2,
    GAME_UPDATE_STATE = 3
}

const START_BYTES = new Uint8Array([0xE0, 0xEA, 0X0A, 0x08]);
const END_BYTES = new Uint8Array([0xFF, 0xFF, 0xFF, 0xFF]);

class ClientMessage {
    command: ClientCommand;
    clientId: number | null;
    data: Uint8Array;

    constructor(command: ClientCommand, client_id: number | null = null, values: number[] | null = null) {
        this.command = command;
        this.clientId = client_id;
        if (values === null) {
            this.data = new Uint8Array(0);
        } else {
            this.data = concatByteArray(...values.map(i2b));
        }
    }

    getLength(): number {
        return this.data.length + (this.clientId !== null ? 4 : 0);
    }

    getChecksum(): number {
        let hash = new Md5();
        hash.appendByteArray(concatByteArray(
            i2b(this.getLength()),
            this.clientId !== null ? i2b(this.clientId) : new Uint8Array(0),
            this.data
        ));
        const hexResult = hash.end();
        if (hexResult === undefined || typeof hexResult !== "string") {
            throw new Error("Checksum calculation failed");
        }
        const result = parseInt(hexResult.slice(-3), 16);
        return result % 10;
    }

    toArrayBuffer(): ArrayBuffer {
        return concatByteArray(
            START_BYTES,
            i2b(this.command),
            i2b(this.getLength()),
            this.clientId !== null ? i2b(this.clientId) : new Uint8Array(0),
            this.data,
            i2b(this.getChecksum()),
            END_BYTES
        ).buffer;
    }

    send(ws: WebSocket): void {
        ws.send(this.toArrayBuffer());
        console.log(`Message sent to server: ${ClientCommand[this.command]}`)
    }
}

class ServerMessage {
    command: ServerCommand
    length: number
    client_id: number
    raw_data: Uint8Array

    _cursor: number = 0

    constructor(buffer_data: ArrayBuffer) {
        this.raw_data = new Uint8Array(buffer_data)

        let start_bytes = this._readBytes(4)
        if (start_bytes.some((val, idx) => val !== START_BYTES[idx])) {
            throw new Error("Invalid start bytes")
        }

        let end_bytes = this.raw_data.slice(-4)
        if (end_bytes.some((val, idx) => val !== END_BYTES[idx])) {
            throw new Error("Invalid end bytes")
        }

        this.command = this._readInt() as ServerCommand
        this.length = this._readInt()

        if (this.length + 4 * 5 !== this.raw_data.length) {
            throw new Error("Invalid length" + this.length + " " + this.raw_data.length)
        }

        if (!this._verifyChecksum()) {
            throw new Error("Invalid checksum")
        }

        this.client_id = this._readInt()
    }

    _verifyChecksum(): boolean {
        let hash = new Md5();
        hash.appendByteArray(
            this.raw_data.slice(8, -8)
        )
        const hexResult = hash.end();
        if (hexResult === undefined || typeof hexResult !== "string") {
            throw new Error("Checksum calculation failed");
        }
        const result = parseInt(hexResult.slice(-3), 16);

        const checksumValue = b2i(this.raw_data.slice(-8, -4))
        return result % 10 === checksumValue
    }

    _readBytes(length: number): Uint8Array {
        const result = this.raw_data.slice(this._cursor, this._cursor + length)
        this._cursor += length
        return result
    }

    _readInt(): number {
        return b2i(this._readBytes(4))
    }
}

function i2b(num: number): Uint8Array {
    return new Uint8Array([
        (num >> 24) & 0xFF,
        (num >> 16) & 0xFF,
        (num >> 8) & 0xFF,
        num & 0xFF
    ])
}

function b2i(bytes: Uint8Array): number {
    return (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3]
}

function concatByteArray(...arrays: Uint8Array[]): Uint8Array {
    const result = new Uint8Array(arrays.reduce((acc, val) => acc + val.length, 0))
    let cursor = 0
    for (const array of arrays) {
        result.set(array, cursor)
        cursor += array.length
    }
    return result
}


export {
    ClientCommand,
    ServerCommand,
    ClientMessage,
    ServerMessage
}