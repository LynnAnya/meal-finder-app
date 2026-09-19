import 'dart:async';
import 'package:app_links/app_links.dart';
import 'package:flutter/material.dart';
import '../screens/reset_password_screen.dart';

class DeepLink {
  static final AppLinks _appLinks = AppLinks();
  static StreamSubscription<Uri>? _linkSubscription;

  /// Call once when app launches in main.dart
  static void initialize(BuildContext context) {
    // 🛡️ Guiding listener to ensure context is mounted before handling link
    _linkSubscription = _appLinks.uriLinkStream.listen((uri) {
      if (!context.mounted) return; // Guard against async gap
      _handleDeepLink(context, uri);
    });
  }

  static void _handleDeepLink(BuildContext context, Uri uri) {
    // Target host: mealfinder://reset-password?token=XYZ
    if (uri.host == 'reset-password' || uri.path.contains('reset-password')) {
      final token = uri.queryParameters['token'];

      if (token != null && token.isNotEmpty) {
        // Double check mounted status before navigation
        if (!context.mounted) return;

        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (context) => ResetPasswordScreen(token: token),
          ),
        );
      }
    }
  }

  static void dispose() {
    _linkSubscription?.cancel();
  }
}