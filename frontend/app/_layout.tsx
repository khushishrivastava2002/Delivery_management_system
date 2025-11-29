import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import 'react-native-reanimated';


import { AuthProvider } from '../contexts/AuthContext';
import { LocationProvider, useLocation } from '../contexts/LocationContext';
import { View, Text, Modal, StyleSheet, TouchableOpacity, Linking, Platform, useColorScheme } from 'react-native';

// Prevent the splash screen from auto-hiding before asset loading is complete.
// Trigger rebuild
SplashScreen.preventAutoHideAsync();

const LocationBlocker = () => {
  const { isLocationEnabled, checkLocationStatus } = useLocation();

  const openSettings = () => {
    if (Platform.OS === 'web') {
      alert('Please enable location services in your browser settings.');
    } else if (Platform.OS === 'ios') {
      Linking.openURL('app-settings:');
    } else {
      Linking.openSettings();
    }
  };

  return (
    <Modal
      visible={!isLocationEnabled}
      transparent={true}
      animationType="fade"
    >
      <View style={styles.centeredView}>
        <View style={styles.modalView}>
          <Text style={styles.modalTitle}>Location Required</Text>
          <Text style={styles.modalText}>
            You must enable location services to use this application. We need your location to assign orders and track deliveries.
          </Text>
          <TouchableOpacity
            style={[styles.button, styles.buttonOpen]}
            onPress={openSettings}
          >
            <Text style={styles.textStyle}>Open Settings</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.button, styles.buttonCheck]}
            onPress={checkLocationStatus}
          >
            <Text style={[styles.textStyle, { color: '#3B82F6' }]}>I've Enabled It</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const [loaded] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
  });

  useEffect(() => {
    if (loaded) {
      SplashScreen.hideAsync();
    }
  }, [loaded]);

  if (!loaded) {
    return null;
  }

  return (
    <AuthProvider>
      <LocationProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <Stack>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen name="+not-found" />
          </Stack>
          <LocationBlocker />
        </ThemeProvider>
      </LocationProvider>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  centeredView: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.8)',
  },
  modalView: {
    margin: 20,
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 35,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
    width: '85%',
  },
  button: {
    borderRadius: 10,
    padding: 15,
    elevation: 2,
    width: '100%',
    marginBottom: 10,
    alignItems: 'center',
  },
  buttonOpen: {
    backgroundColor: '#3B82F6',
  },
  buttonCheck: {
    backgroundColor: '#F3F4F6',
    marginTop: 10,
  },
  textStyle: {
    color: 'white',
    fontWeight: 'bold',
    textAlign: 'center',
    fontSize: 16,
  },
  modalTitle: {
    marginBottom: 15,
    textAlign: 'center',
    fontSize: 22,
    fontWeight: 'bold',
    color: '#111827',
  },
  modalText: {
    marginBottom: 25,
    textAlign: 'center',
    fontSize: 16,
    color: '#4B5563',
    lineHeight: 24,
  },
});
