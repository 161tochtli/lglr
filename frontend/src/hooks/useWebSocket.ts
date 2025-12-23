import { useState, useEffect, useRef } from 'react';
import type { WSMessage } from '../types';

interface UseWebSocketOptions {
  onMessage?: (message: WSMessage) => void;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WSMessage | null;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const { onMessage, reconnectInterval = 3000 } = options;
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  const pingIntervalRef = useRef<number>();
  const onMessageRef = useRef(onMessage);

  // Keep onMessage ref updated without causing reconnections
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;

      try {
        // Build WebSocket URL
        const wsUrl = url.startsWith('ws')
          ? url
          : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${url}`;
        
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setIsConnected(true);
          console.log('[WS] Connected');
          
          // Start ping interval to keep connection alive
          pingIntervalRef.current = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          if (event.data === 'pong') return;
          
          try {
            const message: WSMessage = JSON.parse(event.data);
            
            // Ignore keepalive messages
            if (message.type === 'keepalive') return;
            
            setLastMessage(message);
            onMessageRef.current?.(message);
          } catch (e) {
            console.warn('[WS] Failed to parse message:', event.data);
          }
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setIsConnected(false);
          console.log('[WS] Disconnected, reconnecting...');
          
          // Clear ping interval
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
          }
          
          // Schedule reconnect
          reconnectTimeoutRef.current = window.setTimeout(connect, reconnectInterval);
        };

        ws.onerror = (error) => {
          console.error('[WS] Error:', error);
        };
      } catch (e) {
        console.error('[WS] Connection failed:', e);
        if (isMounted) {
          reconnectTimeoutRef.current = window.setTimeout(connect, reconnectInterval);
        }
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, [url, reconnectInterval]);

  return { isConnected, lastMessage };
}

