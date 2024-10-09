import { ServerPacket } from "./Packet";

interface WSEvent extends Event {
    packet: ServerPacket;
}

export default WSEvent;