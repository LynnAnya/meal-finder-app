import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../services/user_location.dart';

class LocationNotifier extends StateNotifier<Position?> {
  LocationNotifier() : super(null);

  /// Requests or returns device GPS coordinates, reading from memory if cached.
  Future<Position?> fetchLocationIfNeeded() async {
    if (state != null) return state;

    final pos = await UserLocationService.determinePosition();
    state = pos;
    return pos;
  }

  /// Forces a fresh GPS read from hardware, updating cached state.
  Future<Position?> refreshLocation() async {
    final pos = await UserLocationService.determinePosition();
    state = pos;
    return pos;
  }
}

final locationProvider = StateNotifierProvider<LocationNotifier, Position?>((ref) {
  return LocationNotifier();
});