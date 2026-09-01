// lib/screens/main_screen.dart
import 'package:flutter/material.dart';
import 'home_screen.dart';
import 'compare_screen.dart';
import 'favourite_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _pages = const [
    HomeScreen(),
    CompareScreen(),
    FavouriteScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _currentIndex == 0,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        setState(() => _currentIndex = 0);
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFFEFDF7),
        body: IndexedStack(
          index: _currentIndex,
          children: _pages,
        ),
        bottomNavigationBar: _buildBottomNav(), // 👈 Directly in the same file
      ),
    );
  }

  Widget _buildBottomNav() {
    const Color barBgColor = Color(0xFF1E1E1E);
    const Color selectedColor = Colors.white;
    const Color unselectedColor = Color(0xFF8E8E93);
    const Color topBorderColor = Color(0xFF2C2C2E);

    return Container(
      decoration: const BoxDecoration(
        color: barBgColor,
        border: Border(top: BorderSide(color: topBorderColor, width: 1.0)),
      ),
      child: SafeArea(
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (newIndex) => setState(() => _currentIndex = newIndex),
          backgroundColor: barBgColor,
          selectedItemColor: selectedColor,
          unselectedItemColor: unselectedColor,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w400, fontSize: 12),
          type: BottomNavigationBarType.fixed,
          elevation: 0,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined),
              activeIcon: Icon(Icons.home_rounded),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.alt_route_rounded),
              activeIcon: Icon(Icons.alt_route_rounded),
              label: 'Compare',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.favorite_outline_rounded),
              activeIcon: Icon(Icons.favorite_rounded, color: Colors.redAccent),
              label: 'Favourite',
            ),
          ],
        ),
      ),
    );
  }
}