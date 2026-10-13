import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { checkHealth } from '../api/health';

export const HealthContext = createContext(null);

const POLL_INTERVAL_MS = 30000; // 30 seconds

/**
 * Manages backend health status telemetry by polling /health periodically.
 */
export function HealthProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [modelName, setModelName] = useState(null);
  const [telegramPolling, setTelegramPolling] = useState(false);
  const [capabilities, setCapabilities] = useState({});
  const [lastChecked, setLastChecked] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await checkHealth();
      if (data && (data.status === 'ok' || data.status === 'healthy' || data.model)) {
        setIsConnected(true);
        setModelName(data.model || 'Unknown Model');
        setTelegramPolling(Boolean(data.telegram_polling));
        setCapabilities(data.capabilities || {});
        setError(null);
      } else {
        setIsConnected(false);
        setTelegramPolling(false);
        setCapabilities({});
        setError('Invalid response from backend');
      }
    } catch (err) {
      setIsConnected(false);
      setTelegramPolling(false);
      setCapabilities({});
      setError(err.message || 'Backend unreachable');
    } finally {
      setIsLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    checkHealth()
      .then((data) => {
        if (!ignore && data && (data.status === 'ok' || data.status === 'healthy' || data.model)) {
          setIsConnected(true);
          setModelName(data.model || 'Unknown Model');
          setTelegramPolling(Boolean(data.telegram_polling));
          setCapabilities(data.capabilities || {});
          setError(null);
        } else if (!ignore) {
          setIsConnected(false);
          setTelegramPolling(false);
          setCapabilities({});
          setError('Invalid response from backend');
        }
      })
      .catch((err) => {
        if (!ignore) {
          setIsConnected(false);
          setTelegramPolling(false);
          setCapabilities({});
          setError(err.message || 'Backend unreachable');
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
          setLastChecked(new Date());
        }
      });

    const timer = setInterval(fetchHealth, POLL_INTERVAL_MS);
    return () => {
      ignore = true;
      clearInterval(timer);
    };
  }, [fetchHealth]);

  const value = {
    isConnected,
    modelName,
    telegramPolling,
    capabilities,
    lastChecked,
    error,
    isLoading,
    refreshHealth: fetchHealth,
  };

  return (
    <HealthContext.Provider value={value}>
      {children}
    </HealthContext.Provider>
  );
}

/**
 * Custom hook to consume the backend health status.
 */
export function useHealth() {
  const context = useContext(HealthContext);
  if (!context) {
    throw new Error('useHealth must be used within a HealthProvider');
  }
  return context;
}

export default HealthContext;
