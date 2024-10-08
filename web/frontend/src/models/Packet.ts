import { Md5 } from "ts-md5";
import { ClientCommand, ServerCommand } from "./enums";


const START_BYTES = new Uint8Array([0xE0, 0xEA, 0X0A, 0x08]);
const END_BYTES = new Uint8Array([0xFF, 0xFF, 0xFF, 0xFF]);

class ClientPacket {
    command: ClientCommand;
    data: Uint8Array;

    constructor(command: ClientCommand, values: number[] | null = null) {
        this.command = command;
        if (values === null) {
            this.data = new Uint8Array(0);
        } else {
            this.data = concatByteArray(...values.map(i2b));
        }
    }

    getLength(): number {
        return this.data.length;
    }

    getChecksum(): number {
        let hash = new Md5();
        hash.appendByteArray(concatByteArray(
            i2b(this.getLength()),
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

class ServerPacket {
    command: ServerCommand
    length: number
    raw_data: Uint8Array
    data: number[]

    private cursor: number = 0

    constructor(buffer_data: ArrayBuffer) {
        this.raw_data = new Uint8Array(buffer_data)

        let start_bytes = this.readBytes(4)
        if (start_bytes.some((val, idx) => val !== START_BYTES[idx])) {
            throw new Error("Invalid start bytes")
        }

        let end_bytes = this.raw_data.slice(-4)
        if (end_bytes.some((val, idx) => val !== END_BYTES[idx])) {
            throw new Error("Invalid end bytes")
        }

        this.command = this.readInt() as ServerCommand
        this.length = this.readInt()

        if (this.length + 4 * 5 !== this.raw_data.length) {
            throw new Error("Invalid length" + this.length + " " + this.raw_data.length)
        }

        if (!this.verifyChecksum()) {
            throw new Error("Invalid checksum")
        }

        this.data = []
        while (this.cursor < this.raw_data.length - 8) {
            this.data.push(this.readInt())
        }
    }

    private verifyChecksum(): boolean {
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

    readBytes(length: number): Uint8Array {
        const result = this.raw_data.slice(this.cursor, this.cursor + length)
        this.cursor += length
        return result
    }

    readInt(): number {
        return b2i(this.readBytes(4))
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
    ClientPacket as ClientMessage,
    ServerPacket as ServerMessage
}