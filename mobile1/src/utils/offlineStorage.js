import AsyncStorage from '@react-native-async-storage/async-storage';

const OFFLINE_PROPERTIES_KEY = '@offline_properties';
const OFFLINE_PHOTOS_KEY = '@offline_photos';
const OFFLINE_GPS_LOGS_KEY = '@offline_gps_logs';

export const OfflineStorage = {
  // Save property for offline sync
  saveProperty: async (propertyData) => {
    try {
      const existing = await AsyncStorage.getItem(OFFLINE_PROPERTIES_KEY);
      const properties = existing ? JSON.parse(existing) : [];
      
      properties.push({
        ...propertyData,
        timestamp: Date.now(),
        status: 'pending',
      });
      
      await AsyncStorage.setItem(OFFLINE_PROPERTIES_KEY, JSON.stringify(properties));
      return true;
    } catch (error) {
      console.error('Error saving offline property:', error);
      return false;
    }
  },

  // Get all pending offline properties
  getPendingProperties: async () => {
    try {
      const data = await AsyncStorage.getItem(OFFLINE_PROPERTIES_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Error getting offline properties:', error);
      return [];
    }
  },

  // Remove property from offline storage after sync
  removeProperty: async (index) => {
    try {
      const properties = await AsyncStorage.getItem(OFFLINE_PROPERTIES_KEY);
      if (properties) {
        const list = JSON.parse(properties);
        list.splice(index, 1);
        await AsyncStorage.setItem(OFFLINE_PROPERTIES_KEY, JSON.stringify(list));
      }
    } catch (error) {
      console.error('Error removing offline property:', error);
    }
  },

  // Save photo for offline sync
  savePhoto: async (photoData) => {
    try {
      const existing = await AsyncStorage.getItem(OFFLINE_PHOTOS_KEY);
      const photos = existing ? JSON.parse(existing) : [];
      
      photos.push({
        ...photoData,
        timestamp: Date.now(),
        status: 'pending',
      });
      
      await AsyncStorage.setItem(OFFLINE_PHOTOS_KEY, JSON.stringify(photos));
      return true;
    } catch (error) {
      console.error('Error saving offline photo:', error);
      return false;
    }
  },

  // Get all pending offline photos
  getPendingPhotos: async () => {
    try {
      const data = await AsyncStorage.getItem(OFFLINE_PHOTOS_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Error getting offline photos:', error);
      return [];
    }
  },

  // Remove photo from offline storage after sync
  removePhoto: async (index) => {
    try {
      const photos = await AsyncStorage.getItem(OFFLINE_PHOTOS_KEY);
      if (photos) {
        const list = JSON.parse(photos);
        list.splice(index, 1);
        await AsyncStorage.setItem(OFFLINE_PHOTOS_KEY, JSON.stringify(list));
      }
    } catch (error) {
      console.error('Error removing offline photo:', error);
    }
  },

  // Save GPS log for offline sync
  saveGPSLog: async (gpsData) => {
    try {
      const existing = await AsyncStorage.getItem(OFFLINE_GPS_LOGS_KEY);
      const logs = existing ? JSON.parse(existing) : [];
      
      logs.push({
        ...gpsData,
        timestamp: Date.now(),
        status: 'pending',
      });
      
      await AsyncStorage.setItem(OFFLINE_GPS_LOGS_KEY, JSON.stringify(logs));
      return true;
    } catch (error) {
      console.error('Error saving offline GPS log:', error);
      return false;
    }
  },

  // Get all pending offline GPS logs
  getPendingGPSLogs: async () => {
    try {
      const data = await AsyncStorage.getItem(OFFLINE_GPS_LOGS_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Error getting offline GPS logs:', error);
      return [];
    }
  },

  // Clear all offline data
  clearAll: async () => {
    try {
      await AsyncStorage.multiRemove([
        OFFLINE_PROPERTIES_KEY,
        OFFLINE_PHOTOS_KEY,
        OFFLINE_GPS_LOGS_KEY,
      ]);
    } catch (error) {
      console.error('Error clearing offline data:', error);
    }
  },

  // Get offline data count
  getOfflineCount: async () => {
    try {
      const properties = await OfflineStorage.getPendingProperties();
      const photos = await OfflineStorage.getPendingPhotos();
      const gpsLogs = await OfflineStorage.getPendingGPSLogs();
      
      return {
        properties: properties.length,
        photos: photos.length,
        gpsLogs: gpsLogs.length,
        total: properties.length + photos.length + gpsLogs.length,
      };
    } catch (error) {
      console.error('Error getting offline count:', error);
      return { properties: 0, photos: 0, gpsLogs: 0, total: 0 };
    }
  },
};
