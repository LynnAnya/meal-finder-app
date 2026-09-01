import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/dish.dart';

class CompareNotifier extends StateNotifier<List<Dish>> {
  CompareNotifier() : super([]);

  void toggleDish(Dish dish) {
    if (state.any((d) => d.id == dish.id)) {
      state = state.where((d) => d.id != dish.id).toList();
    } else {
      if (state.length >= 5) return; // Strict maximum limit of 5 items
      state = [...state, dish];
    }
  }

  bool isSelected(int dishId) => state.any((d) => d.id == dishId);
  void clear() => state = [];
}

final compareProvider = StateNotifierProvider<CompareNotifier, List<Dish>>((ref) {
  return CompareNotifier();
});