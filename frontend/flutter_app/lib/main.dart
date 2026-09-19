import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'screens/main_screen.dart'; 
import 'screens/auth_screen.dart';
import 'providers/user_provider.dart';
import 'services/deep_link.dart'; 

void main() {
  runApp(
    const ProviderScope(
      child: MealFinderApp(),
    ),
  );
}

class MealFinderApp extends ConsumerStatefulWidget {
  const MealFinderApp({super.key});

  @override
  ConsumerState<MealFinderApp> createState() => _MealFinderAppState();
}

class _MealFinderAppState extends ConsumerState<MealFinderApp> {
  @override
  void initState() {
    super.initState();
    // 👈 2. Initialize deep link listener immediately after the first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      DeepLink.initialize(context);
    });
  }

  @override
  void dispose() {
    // 👈 3. Clean up the stream listener when the app widget disposes
    DeepLink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final userState = ref.watch(userProvider);

    return MaterialApp(
      title: 'MealFinder', // 👈 Updated to MealFinder
      debugShowCheckedModeBanner: false,
      routes: {
        '/main': (context) => const MainScreen(), 
        '/auth': (context) => const AuthScreen(),
      },
      
      // Startup Flow Handler
      home: userState.when(
        // App is checking token on launch
        loading: () => const Scaffold(
          backgroundColor: Color(0xFFFEFDF7),
          body: Center(child: CircularProgressIndicator()),
        ),
        
        error: (error, stack) => const AuthScreen(),
        
        // Backend verification result
        data: (user) {
          if (user != null) {
            return const MainScreen(); 
          } else {
            return const AuthScreen(); 
          }
        },
      ),
    );
  }
}