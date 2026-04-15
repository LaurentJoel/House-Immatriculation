import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// API Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://192.168.1.100:8000/api'; // Change to your backend IP

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
          headers: { Authorization: `Bearer ${refreshToken}` },
        });

        const { access_token, refresh_token } = response.data;
        
        await AsyncStorage.setItem('access_token', access_token);
        await AsyncStorage.setItem('refresh_token', refresh_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username, password) => {
    const response = await api.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },
};

// Location API
export const locationAPI = {
  checkIn: async (latitude, longitude, altitude = null, accuracy = null) => {
    const response = await api.post('/location/check-in', {
      latitude,
      longitude,
      altitude,
      accuracy,
    });
    return response.data;
  },

  getNearbyPolygons: async (latitude, longitude, radius = 100, limit = 10) => {
    const response = await api.get('/location/nearby-polygons', {
      params: { latitude, longitude, radius, limit },
    });
    return response.data;
  },

  logGPS: async (latitude, longitude, altitude = null, accuracy = null, propertyId = null) => {
    const response = await api.post('/location/log', {
      latitude,
      longitude,
      altitude,
      accuracy,
      property_id: propertyId,
    });
    return response.data;
  },
};

// Properties API
export const propertiesAPI = {
  getAll: async (skip = 0, limit = 100, statusFilter = null, regionFilter = null) => {
    const params = { skip, limit };
    if (statusFilter) params.status_filter = statusFilter;
    if (regionFilter) params.region_filter = regionFilter;
    
    const response = await api.get('/properties', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/properties/${id}`);
    return response.data;
  },

  create: async (propertyData) => {
    const response = await api.post('/properties', propertyData);
    return response.data;
  },

  update: async (id, propertyData) => {
    const response = await api.put(`/properties/${id}`, propertyData);
    return response.data;
  },

  delete: async (id) => {
    const response = await api.delete(`/properties/${id}`);
    return response.data;
  },

  uploadPhotos: async (propertyId, frontPhoto, sidePhoto) => {
    const formData = new FormData();
    formData.append('front_photo', {
      uri: frontPhoto.uri,
      type: frontPhoto.type || 'image/jpeg',
      name: `front_${Date.now()}.jpg`,
    });
    formData.append('side_photo', {
      uri: sidePhoto.uri,
      type: sidePhoto.type || 'image/jpeg',
      name: `side_${Date.now()}.jpg`,
    });

    const response = await api.post(`/properties/${propertyId}/photos`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default api;
