import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/compare_provider.dart';

class CompareScreen extends ConsumerWidget {
  const CompareScreen({super.key});

  final Color bgColor = const Color(0xFFFEFDF7);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedDishes = ref.watch(compareProvider);

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          'Compare Dishes ⚖️',
          style: TextStyle(color: textMain, fontWeight: FontWeight.bold, fontSize: 20),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: selectedDishes.isEmpty
              ? Text(
                  'No dishes selected for comparison yet.',
                  style: TextStyle(color: textMuted, fontSize: 16),
                )
              : Text(
                  'Comparing ${selectedDishes.length} dishes (Coming Soon)',
                  style: TextStyle(color: textMain, fontSize: 16, fontWeight: FontWeight.bold),
                ),
        ),
      ),
    );
  }
}