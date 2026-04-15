# House Tracking Mobile App - IRS Cameroon

## Overview
Mobile application for field agents to track house locations, pair GPS positions with OSM polygons, and collect property information for the Internal Revenue Services of Cameroon.

## Features
- **GPS Location Tracking**: Activate GPS and get precise location
- **Polygon Matching**: Automatically match GPS position with OSM house polygons
- **Property Data Entry**: Collect comprehensive property information
- **Photo Upload**: Capture front and side photos of buildings
- **Offline Support**: Save data locally and sync when online
- **User Authentication**: Secure login with JWT tokens

## Tech Stack
- **Framework**: React Native with Expo
- **Navigation**: React Navigation
- **State Management**: React Context API
- **Storage**: AsyncStorage
- **Maps**: React Native Maps
- **Location**: Expo Location
- **Camera**: Expo Image Picker
- **Forms**: Formik with Yup validation

## Setup

### Prerequisites
- Node.js 18+
- npm or yarn
- Expo CLI
- Android Studio / Xcode for native development

### Installation

1. Install dependencies:
```bash
npm install
```

2. Install Expo CLI:
```bash
npm install -g expo-cli
```

3. Configure API endpoint:
Update `API_BASE_URL` in `src/services/api.js` with your backend server address

4. Start the development server:
```bash
npm start
```

5. Run on device:
- Press `a` for Android
- Press `i` for iOS
- Or scan QR code with Expo Go app

## Configuration

### API Endpoint
Update the `API_BASE_URL` in `src/services/api.js`:
```javascript
const API_BASE_URL = 'http://YOUR_SERVER_IP:8000/api';
```

**Important**: Use your local network IP (e.g., 192.168.1.100) instead of localhost when testing on physical devices.

### Environment Variables
Create a `.env` file:
```
API_BASE_URL=http://your-server-ip:8000/api
```

## Usage Flow

1. **Login**: Field agent logs in with credentials
2. **GPS Check-In**: 
   - App activates GPS
   - Shows current location on map
   - Automatically searches for matching polygon
   - Displays nearby polygons if no exact match
3. **Property Entry**:
   - Enter owner information
   - Fill property details
   - Upload front and side photos
   - Save to database
4. **Data Sync**: All data syncs to PostgreSQL database

## Data Collection Fields

### Owner Information
- Owner Name (required)
- Owner Phone (required)
- Owner Sex (Male/Female/Other)

### Address
- Full Address (required)
- City
- Region

### Building Details
- Building Type (Residential/Commercial/Mixed)
- Is Storey Building (checkbox)
- Floor Count
- Room Count
- Construction Material
- Estimated Area (sqm)

### Photos
- Front Photo (required)
- Side Photo (required)

### Verification
- Verification Notes

## Offline Support

The app supports offline data collection:
- GPS positions are logged locally
- Property data can be saved offline
- Photos are cached and uploaded when connection is available
- Automatic sync when back online

## Security

- JWT-based authentication
- Automatic token refresh
- Secure password storage
- HTTPS API communication

## Optimization for IRS Cameroon

### Performance
- Efficient GPS polling (reduces battery drain)
- Image compression before upload
- Lazy loading of components
- Optimized database queries

### User Experience
- Simple, intuitive interface
- Minimal steps for data entry
- GPS accuracy indicators
- Visual feedback for all actions
- Works in low-connectivity areas

### Data Quality
- Required field validation
- Photo requirements (front and side views)
- GPS accuracy thresholds
- Polygon matching with distance verification

## Troubleshooting

### GPS Issues
- Ensure GPS is enabled on device
- Check location permissions
- Move to open area for better signal
- Wait for GPS accuracy to improve (< 20m recommended)

### Connection Issues
- Verify API_BASE_URL is correct
- Check device is on same network as server
- Ensure backend server is running
- Check firewall settings

### Photo Upload Issues
- Check camera permissions
- Ensure photos are not too large (< 10MB)
- Verify network connection
- Check server storage space

## Build for Production

### Android APK
```bash
expobuild:android
```

### iOS IPA
```bash
expobuild:ios
```

## Testing

### Unit Tests
```bash
npm test
```

### E2E Tests
```bash
npm run test:e2e
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

Internal use only - IRS Cameroon

## Support

For technical support, contact the development team.
