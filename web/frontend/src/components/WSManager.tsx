import { useState, useCallback, useMemo } from "react";
export const isBrowser = typeof window !== "undefined";

function useWSManager() {
    const wsInstance = useMemo(() => isBrowser ? new WebSocket("http://localhost:5555") : null, []);
    // const [wsInstance] = useState(() => isBrowser ? new WebSocket(...) : null);
    const [wsConnection, setWSConnection] = useState<WebSocket | null>(null);
    
    // Call when updating the ws connection
    const updateWs = useCallback((url) => {
        if(!browser) return setWsInstance(null);

        // Close the old connection
        if(wsInstance?.readyState !== 3)
        wsInstance?.close(...);
    
        // Create a new connection
        const newWs = new WebSocket(url);
        setWsInstance(newWs);
    }, [wsInstance])
    
 
}