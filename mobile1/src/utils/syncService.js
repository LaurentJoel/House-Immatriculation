import NetInfo from '@react-native-community/netinfo';
import { propertiesAPI, locationAPI } from '../services/api';
import { OfflineStorage } from './offlineStorage';

let isSyncing = false;

export const SyncService = {
  // Check network connectivity
  checkConnection: async () => {
    const connection = await NetInfo.fetch();
    return connection.isConnected && connection.isInternetReachable;
  },

  // Sync offline properties
  syncProperties: async () => {
    try {
      const properties = await OfflineStorage.getPendingProperties();
      
      if (properties.length === 0) {
        console.log('No properties to sync');
        return true;
      }

      for (let i = 0; i < properties.length; i++) {
        const property = properties[i];
        
        try {
          await propertiesAPI.create(property.data);
          await OfflineStorage.removeProperty(i);
          i--; // Adjust index after removal
          console.log('Property synced successfully');
        } catch (error) {
          console.error('Error syncing property:', error);
          // Skip failed property and continue
        }
      }

      return true;
    } catch (error) {
      console.error('Error in syncProperties:', error);
      return false;
    }
  },

  // Sync offline photos
  syncPhotos: async () => {
    try {
      const photos = await OfflineStorage.getPendingPhotos();
      
      if (photos.length === 0) {
        console.log('No photos to sync');
        return true;
      }

      for (let i = 0; i < photos.length; i++) {
        const photo = photos[i];
        
        try {
          await propertiesAPI.uploadPhotos(
            photo.propertyId,
            photo.frontPhoto,
            photo.sidePhoto
          );
          await OfflineStorage.removePhoto(i);
          i--; // Adjust index after removal
          console.log('Photos synced successfully');
        } catch (error) {
          console.error('Error syncing photos:', error);
          // Skip failed photos and continue
        }
      }

      return true;
    } catch (error) {
      console.error('Error in syncPhotos:', error);
      return false;
    }
  },

  // Sync offline GPS logs
  syncGPSLogs: async () => {
    try {
      const logs = await OfflineStorage.getPendingGPSLogs();
      
      if (logs.length === 0) {
        console.log('No GPS logs to sync');
        return true;
      }

      for (let i = 0; i < logs.length; i++) {
        const log = logs[i];
        
        try {
          await locationAPI.logGPS(
            log.latitude,
            log.longitude,
            log.altitude,
            log.accuracy,
            log.propertyId
          );
          await OfflineStorage.removeGPSLog(i);
          i--; // Adjust index after removal
          console.log('GPS log synced successfully');
        } catch (error) {
          console.error('Error syncing GPS log:', error);
          // Skip failed log and continue
        }
      }

      return true;
    } catch (error) {
      console.error('Error in syncGPSLogs:', error);
      return false;
    }
  },

  // Sync all offline data
  syncAll: async () => {
    if (isSyncing) {
      console.log('Sync already in progress');
      return false;
    }

    const isConnected = await SyncService.checkConnection();
    
    if (!isConnected) {
      console.log('No internet connection, skipping sync');
      return false;
    }

    isSyncing = true;
    console.log('Starting sync...');

    try {
      await SyncService.syncProperties();
      await SyncService.syncPhotos();
      await SyncService.syncGPSLogs();

      console.log('Sync completed');
      return true;
    } catch (error) {
      console.error('Sync failed:', error);
      return false;
    } finally {
      isSyncing = false;
    }
  },

  // Start automatic sync listener
  startSyncListener: () => {
    return NetInfo.addEventListener(state => {
      if (state.isConnected && state.isInternetReachable) {
        console.log('Internet connected, syncing...');
        SyncService.syncAll();
      } else {
        console.log('Internet disconnected');
      }
    });
  },

  // Stop sync listener
  stopSyncListener: (listener) => {
    if (listener) {
      listener();
    }
  },
};
