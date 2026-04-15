import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
  Image,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import * as ImagePicker from 'expo-image-picker';
import { propertiesAPI } from '../services/api';

const PropertyFormScreen = ({ route, navigation }) => {
  const { polygonId, immatriculationNumber, existingProperty } = route.params || {};
  
  const [formData, setFormData] = useState({
    owner_name: '',
    owner_phone: '',
    owner_sex: '',
    address: '',
    city: '',
    region: '',
    building_type: '',
    is_storey_building: false,
    floor_count: 1,
    room_count: 1,
    construction_material: '',
    estimated_area_sqm: '',
    verification_notes: '',
  });

  const [frontPhoto, setFrontPhoto] = useState(null);
  const [sidePhoto, setSidePhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [propertyId, setPropertyId] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (existingProperty) {
      setFormData({
        owner_name: existingProperty.owner_name || '',
        owner_phone: existingProperty.owner_phone || '',
        owner_sex: existingProperty.owner_sex || '',
        address: existingProperty.address || '',
        city: existingProperty.city || '',
        region: existingProperty.region || '',
        building_type: existingProperty.building_type || '',
        is_storey_building: existingProperty.is_storey_building || false,
        floor_count: existingProperty.floor_count || 1,
        room_count: existingProperty.room_count || 1,
        construction_material: existingProperty.construction_material || '',
        estimated_area_sqm: existingProperty.estimated_area_sqm || '',
        verification_notes: existingProperty.verification_notes || '',
      });
      setPropertyId(existingProperty.id);
      setIsEditing(true);
    }
  }, [existingProperty]);

  const pickPhoto = async (type) => {
    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (permissionResult.granted === false) {
      Alert.alert('Permission Required', 'Permission to access camera roll is required!');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled) {
      if (type === 'front') {
        setFrontPhoto(result.assets[0]);
      } else {
        setSidePhoto(result.assets[0]);
      }
    }
  };

  const takePhoto = async (type) => {
    const permissionResult = await ImagePicker.requestCameraPermissionsAsync();
    
    if (permissionResult.granted === false) {
      Alert.alert('Permission Required', 'Permission to access camera is required!');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled) {
      if (type === 'front') {
        setFrontPhoto(result.assets[0]);
      } else {
        setSidePhoto(result.assets[0]);
      }
    }
  };

  const handlePhotoSelection = async (type) => {
    Alert.alert(
      `Select ${type} photo`,
      '',
      [
        {
          text: 'Take Photo',
          onPress: () => takePhoto(type),
        },
        {
          text: 'Choose from Library',
          onPress: () => pickPhoto(type),
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    );
  };

  const validateForm = () => {
    if (!formData.owner_name) {
      Alert.alert('Validation Error', 'Owner name is required');
      return false;
    }
    if (!formData.owner_phone) {
      Alert.alert('Validation Error', 'Owner phone is required');
      return false;
    }
    if (!formData.address) {
      Alert.alert('Validation Error', 'Address is required');
      return false;
    }
    if (!frontPhoto || !sidePhoto) {
      Alert.alert('Photos Required', 'Please upload both front and side photos');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      if (isEditing) {
        // Update existing property
        await propertiesAPI.update(propertyId, formData);
        
        // Upload photos
        await propertiesAPI.uploadPhotos(propertyId, frontPhoto, sidePhoto);
        
        Alert.alert('Success', 'Property updated successfully!', [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      } else {
        // Create new property
        const propertyData = {
          polygon_id: polygonId,
          ...formData,
        };

        const response = await propertiesAPI.create(propertyData);
        setPropertyId(response.id);

        // Upload photos
        await propertiesAPI.uploadPhotos(response.id, frontPhoto, sidePhoto);

        Alert.alert('Success', 'Property saved successfully!', [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      }
    } catch (error) {
      console.error('Save error:', error);
      Alert.alert(
        'Error',
        error.response?.data?.detail || 'Failed to save property'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>
          {isEditing ? 'Edit Property' : 'New Property'}
        </Text>
        <Text style={styles.subtitle}>
          Immatriculation: {immatriculationNumber}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Owner Information</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Owner Name"
          value={formData.owner_name}
          onChangeText={(text) => setFormData({ ...formData, owner_name: text })}
        />

        <TextInput
          style={styles.input}
          placeholder="Owner Phone"
          value={formData.owner_phone}
          onChangeText={(text) => setFormData({ ...formData, owner_phone: text })}
          keyboardType="phone-pad"
        />

        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.owner_sex}
            onValueChange={(itemValue) => setFormData({ ...formData, owner_sex: itemValue })}
            style={styles.picker}
          >
            <Picker.Item label="Select Sex" value="" />
            <Picker.Item label="Male" value="Male" />
            <Picker.Item label="Female" value="Female" />
          </Picker>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Address</Text>
        
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Full Address"
          value={formData.address}
          onChangeText={(text) => setFormData({ ...formData, address: text })}
          multiline
          numberOfLines={3}
        />

        <TextInput
          style={styles.input}
          placeholder="City"
          value={formData.city}
          onChangeText={(text) => setFormData({ ...formData, city: text })}
        />

        <TextInput
          style={styles.input}
          placeholder="Region"
          value={formData.region}
          onChangeText={(text) => setFormData({ ...formData, region: text })}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Building Details</Text>
        
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={formData.building_type}
            onValueChange={(itemValue) => setFormData({ ...formData, building_type: itemValue })}
            style={styles.picker}
          >
            <Picker.Item label="Select Building Type" value="" />
            <Picker.Item label="Residential" value="Residential" />
            <Picker.Item label="Commercial" value="Commercial" />
            <Picker.Item label="Mixed" value="Mixed" />
          </Picker>
        </View>

        <View style={styles.row}>
          <TouchableOpacity
            style={styles.checkboxContainer}
            onPress={() => setFormData({ ...formData, is_storey_building: !formData.is_storey_building })}
          >
            <View style={[styles.checkbox, formData.is_storey_building && styles.checkboxChecked]} />
            <Text style={styles.checkboxLabel}>Storey Building</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.row}>
          <TextInput
            style={styles.halfInput}
            placeholder="Floors"
            value={formData.floor_count.toString()}
            onChangeText={(text) => setFormData({ ...formData, floor_count: parseInt(text) || 1 })}
            keyboardType="numeric"
          />

          <TextInput
            style={styles.halfInput}
            placeholder="Rooms"
            value={formData.room_count.toString()}
            onChangeText={(text) => setFormData({ ...formData, room_count: parseInt(text) || 1 })}
            keyboardType="numeric"
          />
        </View>

        <TextInput
          style={styles.input}
          placeholder="Construction Material"
          value={formData.construction_material}
          onChangeText={(text) => setFormData({ ...formData, construction_material: text })}
        />

        <TextInput
          style={styles.input}
          placeholder="Estimated Area (sqm)"
          value={formData.estimated_area_sqm.toString()}
          onChangeText={(text) => setFormData({ ...formData, estimated_area_sqm: parseFloat(text) || 0 })}
          keyboardType="decimal-pad"
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Photos</Text>
        
        <View style={styles.photoSection}>
          <View style={styles.photoContainer}>
            {frontPhoto ? (
              <>
                <Image source={{ uri: frontPhoto.uri }} style={styles.photo} />
                <Text style={styles.photoLabel}>Front Photo</Text>
              </>
            ) : (
              <View style={styles.photoPlaceholder}>
                <Text style={styles.photoPlaceholderText}>Front Photo</Text>
              </View>
            )}
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => handlePhotoSelection('front')}
            >
              <Text style={styles.photoButtonText}>{frontPhoto ? 'Change' : 'Add'} Front</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.photoContainer}>
            {sidePhoto ? (
              <>
                <Image source={{ uri: sidePhoto.uri }} style={styles.photo} />
                <Text style={styles.photoLabel}>Side Photo</Text>
              </>
            ) : (
              <View style={styles.photoPlaceholder}>
                <Text style={styles.photoPlaceholderText}>Side Photo</Text>
              </View>
            )}
            <TouchableOpacity
              style={styles.photoButton}
              onPress={() => handlePhotoSelection('side')}
            >
              <Text style={styles.photoButtonText}>{sidePhoto ? 'Change' : 'Add'} Side</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Verification Notes</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Add verification notes..."
          value={formData.verification_notes}
          onChangeText={(text) => setFormData({ ...formData, verification_notes: text })}
          multiline
          numberOfLines={4}
        />
      </View>

      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={[styles.saveButton, loading && styles.saveButtonDisabled]}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.saveButtonText}>
              {isEditing ? 'Update Property' : 'Save Property'}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#1a237e',
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#bbdefb',
  },
  section: {
    backgroundColor: '#fff',
    padding: 15,
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a237e',
    marginBottom: 15,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    marginBottom: 15,
    fontSize: 16,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  halfInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginHorizontal: 5,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    marginBottom: 15,
  },
  picker: {
    height: 50,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#1a237e',
    marginRight: 10,
    borderRadius: 4,
  },
  checkboxChecked: {
    backgroundColor: '#1a237e',
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#333',
  },
  photoSection: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  photoContainer: {
    flex: 1,
    marginHorizontal: 5,
  },
  photo: {
    width: '100%',
    height: 150,
    borderRadius: 8,
    marginBottom: 8,
  },
  photoPlaceholder: {
    width: '100%',
    height: 150,
    backgroundColor: '#e0e0e0',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  photoPlaceholderText: {
    color: '#999',
    fontSize: 14,
  },
  photoLabel: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginBottom: 8,
  },
  photoButton: {
    backgroundColor: '#1a237e',
    padding: 8,
    borderRadius: 4,
    alignItems: 'center',
  },
  photoButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  buttonContainer: {
    padding: 20,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  saveButton: {
    backgroundColor: '#4caf50',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    backgroundColor: '#81c784',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});

export default PropertyFormScreen;
