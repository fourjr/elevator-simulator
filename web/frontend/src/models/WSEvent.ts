import { ServerMessage } from "./Packet";

interface WSEvent extends Event {
    message: ServerMessage;
}

export default WSEvent;