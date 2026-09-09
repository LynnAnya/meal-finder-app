import 'dart:async';
import 'package:geolocator/geolocator.dart';

class UserLocationService {
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
      // Prevents app from freezing indefinitely underground or in dead zones
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium, // Battery-efficient for food discovery
          timeLimit: Duration(seconds: 8),
        ),
      );
    } catch (_) {
      return null;
    }
  }

  /// Calculates straight-line distance in meters between two coordinates
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

  /// Formats raw meters into clean UI badges (e.g., "350m" or "1.2km").
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