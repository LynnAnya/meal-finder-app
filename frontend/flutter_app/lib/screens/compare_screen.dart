import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../models/dish.dart';
import '../models/compare.dart';
import '../providers/compare_provider.dart';
import '../providers/location_provider.dart';
import '../services/dishes_api.dart';
import '../services/user_location.dart';
import 'dish_detail_screen.dart';

class CompareScreen extends ConsumerStatefulWidget {
  const CompareScreen({super.key});

  @override
  ConsumerState<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends ConsumerState<CompareScreen> {
  // 🎨 Playful Theme Palette (Matches HomeScreen)
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color secondaryAccent = const Color(0xFFFF8FA3);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 159, 156, 156);

  // AI Generation State
  bool _isLoadingAi = false;
  CompareResponse? _aiComparison;
  String? _aiError;

  BoxDecoration _doodleDecoration({Color? color, double borderRadius = 12.5}) {
    return BoxDecoration(
      color: color ?? cardColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: outlineColor, width: 1.0),
      boxShadow: [
        BoxShadow(
          color: outlineColor,
          offset: const Offset(2, 2),
          blurRadius: 0,
        ),
      ],
    );
  }

  void _clearAllComparison() {
    ref.read(compareProvider.notifier).clear();
    setState(() {
      _aiComparison = null;
      _aiError = null;
      _isLoadingAi = false;
    });
  }

  Future<void> _askAiToAnalyze(List<Dish> dishes) async {
    if (dishes.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select at least 2 dishes to compare!')),
      );
      return;
    }

    setState(() {
      _isLoadingAi = true;
      _aiError = null;
    });

    try {
      final dishIds = dishes.map((d) => d.id).toList();

      // Read location state from Riverpod
      // If user denied GPS or coordinates are null, send null to let backend apply default city
      final rawPosition = ref.read(locationProvider);
      final double? userLat = rawPosition?.latitude;
      final double? userLon = rawPosition?.longitude;

      final response = await DishService().fetchCompareSummary(
        dishIds: dishIds,
        lat: userLat,
        lon: userLon,
      );

      if (mounted) {
        setState(() {
          _aiComparison = response;
          _isLoadingAi = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _aiError = e.toString().replaceAll('NetworkException: ', '');
          _isLoadingAi = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // 🎯 Live sync with HomeScreen compare selection
    final selectedDishes = ref.watch(compareProvider);

    // 🎯 Watch user location (falling back safely to Brisbane CBD if GPS denied)
    final Position userPos = ref.watch(locationProvider) ?? UserLocationService.defaultLocation;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded, color: textMain),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Compare Meals ⚖️',
          style: TextStyle(
            color: textMain,
            fontWeight: FontWeight.w700,
            fontSize: 20,
          ),
        ),
        actions: [
          if (selectedDishes.isNotEmpty)
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _clearAllComparison,
              child: Padding(
                padding: const EdgeInsets.only(right: 16.0, left: 8.0),
                child: Center(
                  child: Text(
                    'Clear',
                    style: TextStyle(
                      color: textMuted,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
      body: selectedDishes.isEmpty
          ? _buildEmptyState()
          : SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Selected (${selectedDishes.length}/5)',
                    style: TextStyle(
                      color: textMain,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 1. Horizontal Scroll Comparison Table/Columns
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: selectedDishes.map((dish) {
                        return _buildDishColumn(dish, userPos);
                      }).toList(),
                    ),
                  ),

                  const SizedBox(height: 24),
                  Divider(color: Colors.grey.shade300, thickness: 1.0),
                  const SizedBox(height: 20),

                  // 2. AI Decision Helper Area
                  _buildAiHelperSection(selectedDishes),
                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.compare_arrows_rounded, color: textMuted, size: 72),
            const SizedBox(height: 16),
            Text(
              'No meals selected to compare',
              style: TextStyle(
                color: textMain,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap the circular checkbox on dishes in the Home screen to compare them side-by-side.',
              textAlign: TextAlign.center,
              style: TextStyle(color: textMuted, fontSize: 14, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }

  // Individual Comparison Column Card with Distance Row
  Widget _buildDishColumn(Dish dish, Position userPos) {
    // Calculate distance for this column item
    String distanceText = '-';
    if (dish.lat != null && dish.lon != null) {
      final meters = UserLocationService.calculateDistance(
        userLat: userPos.latitude,
        userLng: userPos.longitude,
        targetLat: dish.lat!,
        targetLng: dish.lon!,
      );
      final formatted = UserLocationService.formatDistance(meters);
      if (formatted.isNotEmpty) {
        distanceText = formatted;
      }
    }

    return Container(
      width: 175,
      margin: const EdgeInsets.only(right: 14.0, bottom: 6.0),
      padding: const EdgeInsets.all(12.0),
      decoration: _doodleDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Row 1: Circular Deselect Checkbox Indicator
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Selected',
                style: TextStyle(
                  color: textMuted,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  ref.read(compareProvider.notifier).toggleDish(dish);
                },
                child: Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accentColor,
                    border: Border.all(color: outlineColor, width: 1.2),
                  ),
                  child: Icon(Icons.check_rounded, size: 15, color: textMain),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Row 2: Tappable Dish Image
          GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => DishDetailScreen(dishId: dish.id),
                ),
              );
            },
            child: Container(
              width: double.infinity,
              height: 110,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: outlineColor, width: 1.0),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(9),
                child: dish.imageUrl != null && dish.imageUrl!.isNotEmpty
                    ? Image.network(
                        dish.imageUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => _buildPlaceholderImage(),
                      )
                    : _buildPlaceholderImage(),
              ),
            ),
          ),
          const SizedBox(height: 10),

          // Row 3: Dish Name
          Text(
            dish.name,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: textMain,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 10),

          // Row 4: Price Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: secondaryAccent,
              borderRadius: BorderRadius.circular(7),
              border: Border.all(color: outlineColor, width: 1.0),
            ),
            child: Text(
              '\$${dish.price.toStringAsFixed(2)}',
              style: TextStyle(
                color: textMain,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 10),

          // Row 5: Rating Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(7),
              border: Border.all(color: outlineColor, width: 1.0),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.star_rounded, color: Color(0xFFFFB01D), size: 15),
                const SizedBox(width: 3),
                Text(
                  dish.rating.toString(),
                  style: TextStyle(
                    color: textMain,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),

          // Row 6: Restaurant Address
          Text(
            'Address',
            style: TextStyle(color: textMuted, fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 2),
          Text(
            (dish.restaurantAddress != null && dish.restaurantAddress!.isNotEmpty)
                ? dish.restaurantAddress!
                : (dish.restaurantName ?? 'No address'),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(color: textMain, fontSize: 12, height: 1.2),
          ),
          const SizedBox(height: 10),

          // Row 7: Calculated Live Distance
          Text(
            'Distance',
            style: TextStyle(color: textMuted, fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 2),
          Text(
            distanceText,
            style: TextStyle(color: textMain, fontSize: 13, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholderImage() {
    return Container(
      color: const Color(0xFFF0F0F0),
      child: Icon(Icons.fastfood_outlined, color: textMain, size: 36),
    );
  }

  // AI Decision Helper (Button or Verdict Card)
  Widget _buildAiHelperSection(List<Dish> dishes) {
    if (_isLoadingAi) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(24),
        decoration: _doodleDecoration(),
        child: Column(
          children: [
            CircularProgressIndicator(color: accentColor),
            const SizedBox(height: 16),
            Text(
              'AI is comparing reviews, prices & distance...',
              style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
    }

    // Post-Analysis Card
    if (_aiComparison != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: _doodleDecoration(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Text('🤖', style: TextStyle(fontSize: 22)),
                    const SizedBox(width: 8),
                    Text(
                      'AI Decision Verdict',
                      style: TextStyle(color: textMain, fontSize: 18, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => setState(() => _aiComparison = null),
                  child: Icon(Icons.refresh_rounded, color: textMuted, size: 20),
                )
              ],
            ),
            const SizedBox(height: 12),

            // Conversational Verdict Bubble
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF2F0FF),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: outlineColor, width: 1.0),
              ),
              child: Text(
                _aiComparison!.verdict,
                style: TextStyle(color: textMain, fontSize: 14, height: 1.4, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 14),

            // Best Value & Taste Picks
            if (_aiComparison!.bestValuePick.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 6.0),
                child: Row(
                  children: [
                    const Text('💰 ', style: TextStyle(fontSize: 16)),
                    Text('Best Value: ', style: TextStyle(fontWeight: FontWeight.w700, color: textMain, fontSize: 13)),
                    Expanded(
                      child: Text(
                        _aiComparison!.bestValuePick,
                        style: TextStyle(color: textMuted, fontSize: 13),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),

            if (_aiComparison!.bestTastePick.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: Row(
                  children: [
                    const Text('⭐ ', style: TextStyle(fontSize: 16)),
                    Text('Best Taste: ', style: TextStyle(fontWeight: FontWeight.w700, color: textMain, fontSize: 13)),
                    Expanded(
                      child: Text(
                        _aiComparison!.bestTastePick,
                        style: TextStyle(color: textMuted, fontSize: 13),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),

            if (_aiComparison!.tradeOffBreakdown.isNotEmpty) ...[
              const Divider(height: 16),
              ..._aiComparison!.tradeOffBreakdown.map(
                (point) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('• ', style: TextStyle(fontWeight: FontWeight.bold, color: textMain)),
                      Expanded(
                        child: Text(
                          point,
                          style: TextStyle(color: textMain, fontSize: 13, height: 1.3),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      );
    }

    // Pre-Analysis State: Action Button
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_aiError != null) ...[
          Padding(
            padding: const EdgeInsets.only(bottom: 10.0),
            child: Text(
              '⚠️ $_aiError',
              style: const TextStyle(color: Colors.redAccent, fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ],
        GestureDetector(
          onTap: () => _askAiToAnalyze(dishes),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 14),
            decoration: _doodleDecoration(color: accentColor, borderRadius: 16),
            alignment: Alignment.center,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text('🤖', style: TextStyle(fontSize: 18)),
                const SizedBox(width: 8),
                Text(
                  'Ask AI to Help Decide',
                  style: TextStyle(color: textMain, fontSize: 15, fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}