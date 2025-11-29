import React, { createContext, useContext, useState, useEffect } from 'react';
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { Alert, Platform } from 'react-native';
import api from '../utils/api';
import { useAuth } from './AuthContext';
import { DeliveryPersonStatus } from '../types';

interface LocationContextType {
  isLocationEnabled: boolean;
  checkLocationStatus: () => Promise<void>;
}

const LocationContext = createContext<LocationContextType | undefined>(undefined);

export const LocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLocationEnabled, setIsLocationEnabled] = useState(true); // Default to true to avoid initial flash
  const { user } = useAuth();

  const updateBackendStatus = async (isEnabled: boolean) => {
    if (!user) return;
    try {
      await api.patch('/delivery-person/location-status', { is_location_on: isEnabled });
    } catch (error) {
      console.error('Failed to update location status on backend:', error);
    }
  };

  const checkLocationStatus = async () => {
    try {
      const { status } = await Location.getForegroundPermissionsAsync();
      const isEnabled = await Location.hasServicesEnabledAsync();

      const locationOn = status === 'granted' && isEnabled;
      setIsLocationEnabled(locationOn);
      updateBackendStatus(locationOn);

      if (!locationOn) {
        // If location is off, we might want to prompt the user
        // But the UI will handle the blocking modal
      }

    } catch (error) {
      console.error('Error checking location status:', error);
      setIsLocationEnabled(false);
    }
  };

  useEffect(() => {
    checkLocationStatus();

    // Poll for location status changes every 5 seconds
    const interval = setInterval(checkLocationStatus, 5000);
    return () => clearInterval(interval);
  }, [user]);

  // Define task name
  const LOCATION_TASK_NAME = 'background-location-task';

  // Define the task in the global scope (outside component)
  // TaskManager is only available on native platforms
  if (Platform.OS !== 'web') {
    TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }) => {
      if (error) {
        console.error('Background location task error:', error);
        return;
      }
      if (data) {
        const { locations } = data as { locations: Location.LocationObject[] };
        const location = locations[0];
        if (location) {
          console.log('Background location update:', location.coords);
          try {
            await api.post('/location/track', {
              latitude: location.coords.latitude,
              longitude: location.coords.longitude,
            });
          } catch (err) {
            console.error('Background track error:', err);
          }
        }
      }
    });
  }

  // Location Tracking Logic
  useEffect(() => {
    let subscription: Location.LocationSubscription | null = null;

    const startTracking = async () => {
      // Only track if user is logged in, active, and location services are enabled
      if (user?.status === DeliveryPersonStatus.ACTIVE && isLocationEnabled) {
        try {
          console.log('Starting location tracking...');

          if (Platform.OS === 'web') {
            // Web Implementation: Use watchPositionAsync
            // Note: This will NOT work if the tab is completely closed.
            // It might work if the tab is inactive/minimized depending on browser throttling.
            subscription = await Location.watchPositionAsync(
              {
                accuracy: Location.Accuracy.High,
                timeInterval: 30000, // Update every 30 seconds
                distanceInterval: 0, // Update regardless of distance
              },
              (location) => {
                console.log('Web Location update:', location.coords);
                api.post('/location/track', {
                  latitude: location.coords.latitude,
                  longitude: location.coords.longitude,
                }).catch(err => console.error('Location track error:', err));
              }
            );
          } else {
            // Native Implementation: Use Background Location
            const { status } = await Location.requestBackgroundPermissionsAsync();
            if (status !== 'granted') {
              console.warn('Background location permission denied');
            }

            await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
              accuracy: Location.Accuracy.High,
              timeInterval: 30000, // Update every 30 seconds
              distanceInterval: 0, // Update regardless of distance
              foregroundService: {
                notificationTitle: "Delivery App",
                notificationBody: "Tracking your location for delivery...",
              },
              showsBackgroundLocationIndicator: true,
            });
          }

        } catch (error) {
          console.error('Error starting location tracking:', error);
        }
      } else {
        console.log('Stopping location tracking...');
        if (Platform.OS === 'web') {
          if (subscription) {
            subscription.remove();
            subscription = null;
          }
        } else {
          try {
            const hasStarted = await Location.hasStartedLocationUpdatesAsync(LOCATION_TASK_NAME);
            if (hasStarted) {
              await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);
            }
          } catch (e) {
            console.warn("Error stopping location updates:", e);
          }
        }
      }
    };

    startTracking();

    return () => {
      if (Platform.OS === 'web' && subscription) {
        // Check if remove exists (it should, but safety first for web/different versions)
        if (typeof subscription.remove === 'function') {
          subscription.remove();
        }
      }
      // Native cleanup is handled by unmounting or status change logic above
    };
  }, [user?.status, isLocationEnabled]);

  return (
    <LocationContext.Provider value={{ isLocationEnabled, checkLocationStatus }}>
      {children}
    </LocationContext.Provider>
  );
};

export const useLocation = () => {
  const context = useContext(LocationContext);
  if (context === undefined) {
    throw new Error('useLocation must be used within a LocationProvider');
  }
  return context;
};
