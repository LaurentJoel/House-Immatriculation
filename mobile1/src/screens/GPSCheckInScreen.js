import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import * as Location from 'expo-location';
import { locationAPI, propertiesAPI } from '../services/api';

const GPSCheckInScreen = ({ route, navigation }) => {
  const [location, setLocation] = useState(null);
  const [permission, setPermission] = useState(null);
  const [loading, setLoading] = useState(false);
  const [matchedPolygon, setMatchedPolygon] = useState(null);
  const [nearbyPolygons, setNearbyPolygons] = useState([]);
  const [gpsAccuracy, setGpsAccuracy] = useState(null);
  const mapRef = useRef(null);

  const { polygonId, immatriculationNumber } = route.params || {};

  useEffect(() => {
    requestPermission();
  }, []);

  useEffect(() => {
    if (permission === 'granted') {
      getCurrentLocation();
    }
  }, [permission]);

  const requestPermission = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    setPermission(status);
  };

  const getCurrentLocation = async () => {
    try {
      setLoading(true);
      const currentLocation = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      
      setLocation({
        latitude: currentLocation.coords.latitude,
        longitude: currentLocation.coords.longitude,
        altitude: currentLocation.coords.altitude || 0,
        accuracy: currentLocation.coords.accuracy || 0,
      });
      
      setGpsAccuracy(currentLocation.coords.accuracy || 0);
      
      // Auto-check if polygon was passed from nearby selection
      if (polygonId) {
        handlePolygonMatch({
          id: polygonId,
          immatriculation_number: immatriculationNumber,
        });
      } else {
        // Otherwise, try to find matching polygon
        await checkLocation();
      }
    } catch (error) {
      Alert.alert('Error', 'Unable to get your location');
      console.error('Location error:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkLocation = async () => {
    if (!location) {
      Alert.alert('Error', 'Please wait for GPS signal');
      return;
    }

    try {
      setLoading(true);
      const result = await locationAPI.checkIn(
        location.latitude,
        location.longitude,
        location.altitude,
        location.accuracy
      );

      if (result.matched) {
        setMatchedPolygon({
          id: result.polygon_id,
          immatriculation_number: result.immatriculation_number,
          distance: result.distance_meters,
        });
        Alert.alert('Success', result.message);
      } else {
        // Try to get nearby polygons
        const nearby = await locationAPI.getNearbyPolygons(
          location.latitude,
          location.longitude,
          100,
          5
        );
        setNearbyPolygons(nearby.polygons || []);
        Alert.alert('Info', result.message);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to check location');
      console.error('Check-in error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePolygonMatch = (polygon) => {
    setMatchedPolygon(polygon);
    
    // Check if property already exists
    propertiesAPI.getById(polygon.id)
      .then((property) => {
        // Property exists, show view property option
        navigation.navigate('PropertyForm', {
          polygonId: polygon.id,
          immatriculationNumber: polygon.immatriculation_number,
          existingProperty: property,
        });
      })
      .catch((error) => {
        // No property exists, navigate to form
        if (error.response?.status === 404) {
          navigation.navigate('PropertyForm', {
            polygonId: polygon.id,
            immatriculationNumber: polygon.immatriculation_number,
          });
        }
      });
  };

  const handleSelectNearbyPolygon = (polygon) => {
    handlePolygonMatch(polygon);
  };

  if (permission === 'denied') {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Location permission is required</Text>
        <TouchableOpacity
          style={styles.button}
          onPress={requestPermission}
        >
          <Text style={styles.buttonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {location ? (
        <MapView
          ref={mapRef}
          style={styles.map}
          region={{
            latitude: location.latitude,
            longitude: location.longitude,
            latitudeDelta: 0.005,
            longitudeDelta: 0.005,
          }}
        >
          <Marker
            coordinate={{
              latitude: location.latitude,
              longitude: location.longitude,
            }}
            title="Your Location"
            description={`Accuracy: ${gpsAccuracy?.toFixed(2)}m`}
          />
        </MapView>
      ) : (
        <View style={styles.mapPlaceholder}>
          <Text>Waiting for GPS signal...</Text>
        </View>
      )}

      <View style={styles.infoCard}>
        <Text style={styles.infoText}>
          GPS Accuracy: {gpsAccuracy ? `${gpsAccuracy.toFixed(2)}m` : 'N/A'}
        </Text>
        <Text style={styles.infoText}>
          Latitude: {location ? location.latitude.toFixed(6) : 'N/A'}
        </Text>
        <Text style={styles.infoText}>
          Longitude: {location ? location.longitude.toFixed(6) : 'N/A'}
        </Text>
      </View>

      {matchedPolygon ? (
        <View style={styles.matchedCard}>
          <Text style={styles.matchedTitle}>✓ Polygon Matched</Text>
          <Text style={styles.matchedText}>
            Immatriculation: {matchedPolygon.immatriculation_number}
          </Text>
          {matchedPolygon.distance && (
            <Text style={styles.matchedText}>
              Distance: {matchedPolygon.distance.toFixed(2)}m
            </Text>
          )}
        </View>
      ) : nearbyPolygons.length > 0 ? (
        <ScrollView style={styles.nearbyList}>
          <Text style={styles.nearbyTitle}>Nearby Polygons:</Text>
          {nearbyPolygons.map((polygon, index) => (
            <TouchableOpacity
              key={index}
              style={styles.nearbyItem}
              onPress={() => handleSelectNearbyPolygon(polygon)}
            >
              <Text style={styles.nearbyText}>
                {polygon.immatriculation_number}
              </Text>
              <Text style={styles.nearbyDistance}>
                {polygon.distance_meters.toFixed(2)}m away
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      ) : null}

      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={location ? checkLocation : getCurrentLocation}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>
              {location ? 'Check Location' : 'Get GPS Signal'}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#d32f2f',
    marginBottom: 20,
    textAlign: 'center',
  },
  map: {
    height: 300,
    width: '100%',
  },
  mapPlaceholder: {
    height: 300,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#e0e0e0',
  },
  infoCard: {
    backgroundColor: '#fff',
    padding: 15,
    margin: 10,
    borderRadius: 8,
    elevation: 2,
  },
  infoText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5,
  },
  matchedCard: {
    backgroundColor: '#4caf50',
    padding: 15,
    margin: 10,
    borderRadius: 8,
  },
  matchedTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  matchedText: {
    fontSize: 14,
    color: '#fff',
    marginBottom: 4,
  },
  nearbyList: {
    maxHeight: 150,
    margin: 10,
  },
  nearbyTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  nearbyItem: {
    backgroundColor: '#fff',
    padding: 12,
    marginBottom: 8,
    borderRadius: 6,
    elevation: 1,
  },
  nearbyText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1a237e',
  },
  nearbyDistance: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  buttonContainer: {
    padding: 15,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  button: {
    backgroundColor: '#1a237e',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#9fa8da',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default GPSCheckInScreen;
