import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user.dart';
import '../services/users_api.dart';
import '../services/auth_api.dart';
import '../core/storage/token_storage.dart';

// 1. The Notifier (The Brain/Manager)
class UserNotifier extends AsyncNotifier<User?> {
  
  // Runs automatically when the app opens or UI asks for it
  @override
  Future<User?> build() async {
    try {
      // Try to fetch the user profile. If it works, save it in RAM.
      return await UsersApi().getUserProfile();
    } catch (e) {
      // If it fails (e.g., no token, not logged in), return null
      return null; 
    }
  }

  // Completely wipes the user from Backend + Phone + RAM
  Future<void> deleteAccount() async {
    state = const AsyncValue.loading(); // Show spinner globally
    
    try {
      await UsersApi().deleteUserAccount(); // Tell Backend
      await TokenStorage.clearToken();      // Clear Phone Storage
      state = const AsyncValue.data(null);  // Clear RAM (User is gone)
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow; // Pass error to UI so the SnackBar shows up!
    }
  }

  //  Standard Log Out (Keeps account, just clears session)
  Future<void> clearSession() async {
    await TokenStorage.clearToken();     // Clear Phone Storage
    state = const AsyncValue.data(null); // Clear RAM
  }

  /// Uploads a new profile picture and updates global Riverpod state
  Future<void> uploadProfilePicture(File imageFile) async {
    final previousState = state; // Save current state in case of error
    state = const AsyncValue.loading(); // Show loading state
    
    try {
      final updatedUser = await UsersApi().uploadProfilePicture(imageFile);
      state = AsyncValue.data(updatedUser); 
    } catch (e, stackTrace) {
      state = previousState; // Revert to old state if upload fails
      return Future.error(e, stackTrace); // Rethrow so UI shows SnackBar
    }
  }

  /// Removes the profile picture and updates global Riverpod state
  Future<void> deleteProfilePicture() async {
    final previousState = state;
    state = const AsyncValue.loading();
    
    try {
      final updatedUser = await UsersApi().deleteProfilePicture();
      state = AsyncValue.data(updatedUser); 
    } catch (e, stackTrace) {
      state = previousState;
      return Future.error(e, stackTrace);
    }
  }

  /// Changes the user's password and updates global Riverpod state
  Future<void> changePassword({required String currentPassword,required String newPassword,}) async {
    await AuthApi().changePassword(
      currentPassword: currentPassword,
      newPassword: newPassword,
    );
  }
}

// 2. The Provider (The label the UI uses to connect to the Brain)
final userProvider = AsyncNotifierProvider<UserNotifier, User?>(() {
  return UserNotifier();
});