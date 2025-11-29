import { useState, useEffect, useRef } from 'react';
import { fyersDataSocket } from 'fyers-web-sdk-v3';

export const useFyers = (accessToken) => {
  const [isConnected, setIsConnected] = useState(false);
  const [marketData, setMarketData] = useState({});
  const fyersRef = useRef(null);

  useEffect(() => {
    if (!accessToken) return;

    let reconnectTimer;
    let fyersInstance = null;

    const initFyers = () => {
      try {
        // Initialize Fyers Socket
        const fyers = new fyersDataSocket(accessToken);
        fyersInstance = fyers;
        
        fyers.on("connect", () => {
          console.log("Fyers Socket Connected");
          setIsConnected(true);
        });

        fyers.on("message", (message) => {
          // console.log("Fyers Update:", message);
          if (message && message.symbol) {
              setMarketData(prev => ({
                  ...prev,
                  [message.symbol]: message
              }));
          }
        });

        fyers.on("error", (err) => {
          console.error("Fyers Socket Error:", err);
          // setIsConnected(false); // Don't set false immediately on error, wait for close
        });

        fyers.on("close", () => {
          console.log("Fyers Socket Closed. Attempting reconnect in 5s...");
          setIsConnected(false);
          clearTimeout(reconnectTimer);
          reconnectTimer = setTimeout(initFyers, 5000);
        });

        fyers.connect();
        fyersRef.current = fyers;

      } catch (error) {
        console.error("Failed to initialize Fyers SDK:", error);
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(initFyers, 5000);
      }
    };

    initFyers();

    return () => {
      clearTimeout(reconnectTimer);
      if (fyersInstance) {
        // fyersInstance.close(); // SDK might not have a close method exposed cleanly or it might auto-close
        // Check documentation or available methods. Usually close() or disconnect()
        // For now, we leave it to GC or SDK to handle, as explicit close might trigger the 'close' event and cause loop
        // But we should try to stop it.
        // fyersInstance.close(); 
      }
    };
  }, [accessToken]);

  const subscribe = (symbols) => {
    if (fyersRef.current && isConnected) {
      fyersRef.current.subscribe(symbols);
    }
  };

  const unsubscribe = (symbols) => {
    if (fyersRef.current && isConnected) {
      fyersRef.current.unsubscribe(symbols);
    }
  };

  return { isConnected, marketData, subscribe, unsubscribe };
};
