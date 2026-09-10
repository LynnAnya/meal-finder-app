// lib/services/location_service.dart
import 'dart:async';
import 'package:geolocator/geolocator.dart';

class UserLocationService {
  static final Position defaultLocation = Position(
    latitude: -27.4698,
    longitude: 153.0251,
    timestamp: DateTime.now(),
    accuracy: 0.0,
    altitude: 0.0,
    heading: 0.0,
    speed: 0.0,
    speedAccuracy: 0.0,
    altitudeAccuracy: 0.0,
    headingAccuracy: 0.0,
  );

  static Future<Position?> determinePosition() async {
    try {
      // 1. Check if device hardware GPS switch is turned on
      final bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return null;
      }

      // 2. Check existing OS permission status
      LocationPermission permission = await Geolocator.checkPermission();
      
      // If undecided, trigger the native OS permission prompt
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return null;
        }
      }
      // If user permanently blocked location access
      if (permission == LocationPermission.deniedForever) {
        return null;
      }

      // 3. Hardware GPS read wrapped with a safety timeout (8 seconds)
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium, 
          timeLimit: Duration(seconds: 8),
        ),
      );
    } catch (_) {
      return null;
    }
  }

  static int calculateDistance({
    required double userLat,
    required double userLng,
    required double targetLat,
    required double targetLng,
  }) {
    return Geolocator.distanceBetween(
      userLat,
      userLng,
      targetLat,
      targetLng,
    ).round();
  }

  /// Formats raw meters (e.g., "350m" or "1.2km")
  static String formatDistance(int? meters) {
    if (meters == null) return '';
    if (meters < 1000) return '${meters}m';
    return '${(meters / 1000).toStringAsFixed(1)}km';
  }

  /// Deep-links directly to this app's permissions screen in phone Settings.
  /// 
  /// Use this when permission is 'deniedForever' so the user can re-enable GPS.
  static Future<bool> openAppSettings() async {
    return await Geolocator.openAppSettings();
  }

  /// Deep-links directly to the device's master GPS toggle switch.
  /// 
  /// Use this when the phone's hardware GPS is switched completely off.
  static Future<bool> openLocationSettings() async {
    return await Geolocator.openLocationSettings();
  }
}