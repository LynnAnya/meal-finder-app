import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../models/dish.dart';
import '../services/dishes_api.dart';
import '../providers/fav_provider.dart';
import '../providers/compare_provider.dart';
import '../services/user_location.dart';
import '../providers/location_provider.dart';
import 'dish_detail_screen.dart';
import 'profile_screen.dart';
import 'compare_screen.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  // 🎨 Playful Theme Colors
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color secondaryAccent = const Color(0xFFFF8FA3);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 159, 156, 156);

  // Controllers
  final TextEditingController _searchController = TextEditingController();
  final ExpansibleController _expansionTileController = ExpansibleController();
  Timer? _debounceTimer;

  // Filter States
  String _searchQuery = '';
  String? _selectedCategory;
  double _maxPrice = 100.0;
  double _minRating = 0.0;
  String _sortBy = 'default';

  // Data State
  late Future<List<Dish>> _dishesFuture;

  final List<String> _categories = ['Mains', 'Appetizers', 'Dessert', 'Sides', 'Kids', 'Beverages'];
  final List<double> _ratingOptions = [0.0, 3.5, 4.0, 4.5];
  final Map<String, String> _sortOptions = {
    'default': 'Default',
    'distance_asc': 'Distance: Nearest First',
    'price_asc': 'Price: Low to High',
    'price_desc': 'Price: High to Low',
    'rating_desc': 'Rating: Highest First',
  };

  @override
  void initState() {
    super.initState();
    _fetchDishes();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(locationProvider.notifier).fetchLocationIfNeeded();
    });

  }
  @override
  void dispose() {
    _searchController.dispose();
    _debounceTimer?.cancel();
    super.dispose();
  }

  void _fetchDishes() {
    setState(() {
      _dishesFuture = DishService().searchDishes(
        q: _searchQuery.isNotEmpty ? _searchQuery : null,
        menuCategory: _selectedCategory,
        maxPrice: _maxPrice,
        minRating: _minRating > 0 ? _minRating : null,
      );
    });
  }

  void _onSearchChanged(String value) {
    if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 350), () {
      if (mounted) {
        setState(() {
          _searchQuery = value.trim();
          _fetchDishes();
        });
      }
    });
  }

  void _resetAllFilters() {
    setState(() {
      _searchController.clear();
      _searchQuery = '';
      _selectedCategory = null;
      _maxPrice = 100.0;
      _minRating = 0.0;
      _sortBy = 'default';
      _fetchDishes();
    });
  }

  List<Dish> _applySorting(List<Dish> dishes, Position? userPos) {
    final sortedList = List<Dish>.from(dishes);
    switch (_sortBy) {
      case 'distance_asc':
        if (userPos != null) {
          sortedList.sort((a, b) {
          final num distA = (a.lat != null && a.lon != null)
              ? UserLocationService.calculateDistance(
                  userLat: userPos.latitude,userLng: userPos.longitude,
                  targetLat: a.lat!,targetLng: a.lon!,
                ) : double.infinity;

          final num distB = (b.lat != null && b.lon != null)
              ? UserLocationService.calculateDistance(
                  userLat: userPos.latitude, userLng: userPos.longitude,
                  targetLat: b.lat!,targetLng: b.lon!,
                ) : double.infinity;
          return distA.compareTo(distB);
          });
        }
        break;
      case 'price_asc':
        sortedList.sort((a, b) => a.price.compareTo(b.price));
        break;
      case 'price_desc':
        sortedList.sort((a, b) => b.price.compareTo(a.price));
        break;
      case 'rating_desc':
        sortedList.sort((a, b) => b.rating.compareTo(a.rating));
        break;
      
      default:
        break;
    }
    return sortedList;
  }

  String _extractCity(String? fullAddress) {
    if (fullAddress == null || fullAddress.trim().isEmpty) return '';
    final parts = fullAddress.split(',');
    return parts.last.trim();
  }

  bool get _hasActiveFilters =>
      _searchQuery.isNotEmpty ||
      _selectedCategory != null ||
      _maxPrice < 100.0 ||
      _minRating > 0.0 ||
      _sortBy != 'default';

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
  
  @override
  Widget build(BuildContext context) {
    final selectedForCompare = ref.watch(compareProvider);
    final userPos = ref.watch(locationProvider) ?? UserLocationService.defaultLocation;
    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        toolbarHeight: 70,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Find your next meal 🍔',
              style: TextStyle(color: textMain, fontWeight: FontWeight.w700, fontSize: 21),
            ),
            const SizedBox(height: 3),
            Text(
              'Select your meal to compare up to 5',
              style: TextStyle(color: textMuted, fontWeight: FontWeight.w400, fontSize: 13),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.person_outline_rounded, color: textMain, size: 28),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ProfileScreen()),
              );
            },
          )
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              // 1. Search Bar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
                child: Container(
                  decoration: _doodleDecoration(),
                  child: TextField(
                    controller: _searchController,
                    onChanged: _onSearchChanged,
                    style: TextStyle(color: textMain, fontWeight: FontWeight.w500),
                    decoration: InputDecoration(
                      hintText: 'Search food or dishes...',
                      hintStyle: TextStyle(color: textMuted, fontWeight: FontWeight.w400),
                      prefixIcon: Icon(Icons.search, color: textMain),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: Icon(Icons.clear, color: textMain),
                              onPressed: () {
                                _searchController.clear();
                                _onSearchChanged('');
                              },
                            )
                          : null,
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(vertical: 14.0),
                    ),
                  ),
                ),
              ),
              // 2. Expandable Filters & Sort Area
              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  controller: _expansionTileController,
                  iconColor: textMain,
                  collapsedIconColor: textMain,
                  title: Row(
                    children: [
                      Icon(Icons.tune, color: textMain, size: 20),
                      const SizedBox(width: 8),
                      Text('Filters & Sort', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 16)),
                      if (_hasActiveFilters) ...[
                        const SizedBox(width: 8),
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: secondaryAccent,
                            shape: BoxShape.circle,
                            border: Border.all(color: outlineColor, width: 1.5),
                          ),
                        ),
                      ]
                    ],
                  ),
                  children: [
                    _buildSortFilter(),
                    _buildPriceFilter(),
                    _buildRatingFilter(),
                    _buildCategoryFilter(),
                    const SizedBox(height: 14),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16.0),
                      child: Row(
                        children: [
                          if (_hasActiveFilters)
                            Expanded(
                              child: GestureDetector(
                                onTap: _resetAllFilters,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(vertical: 12),
                                  decoration: _doodleDecoration(color: Colors.white, borderRadius: 12),
                                  alignment: Alignment.center,
                                  child: Text('Reset All', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 15)),
                                ),
                              ),
                            ),
                          if (_hasActiveFilters) const SizedBox(width: 12),
                          Expanded(
                            child: GestureDetector(
                              onTap: () {
                                _fetchDishes();
                                _expansionTileController.collapse();
                              },
                              child: Container(
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                decoration: _doodleDecoration(color: accentColor, borderRadius: 12),
                                alignment: Alignment.center,
                                child: Text('Apply Filters', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 15)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
              // 3. Results Single Column List (Tighter Spacing)
              Expanded(
                child: FutureBuilder<List<Dish>>(
                  future: _dishesFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return Center(child: CircularProgressIndicator(color: accentColor));
                    } else if (snapshot.hasError) {
                      return Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Text(
                            'Oops! ${snapshot.error}',
                            style: TextStyle(color: textMain, fontWeight: FontWeight.w600),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      );
                    } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.search_off_rounded, color: textMuted, size: 64),
                            const SizedBox(height: 12),
                            Text('No dishes found.', style: TextStyle(color: textMain, fontSize: 18, fontWeight: FontWeight.w600)),
                            if (_hasActiveFilters)
                              TextButton(
                                onPressed: _resetAllFilters,
                                child: Text('Clear all filters', style: TextStyle(color: secondaryAccent, fontWeight: FontWeight.bold, fontSize: 16)),
                              ),
                          ],
                        ),
                      );
                    }
                    final dishes = _applySorting(snapshot.data!, userPos);

                    return ListView.builder(
                      physics: const BouncingScrollPhysics(),
                      padding: EdgeInsets.only(
                        left: 16.0,
                        right: 16.0,
                        top: 4.0,
                        bottom: selectedForCompare.isNotEmpty ? 84.0 : 12.0,
                      ),
                      itemCount: dishes.length,
                      itemBuilder: (context, index) {
                        return _buildDishCard(dishes[index], selectedForCompare, userPos);
                      },
                    );
                  },
                ),
              ),
            ],
          ),
          // Floating Compare Action Banner
          if (selectedForCompare.isNotEmpty)
            Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const CompareScreen()),
                  );
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
                  decoration: _doodleDecoration(color: accentColor, borderRadius: 30),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Compare ${selectedForCompare.length}/5 Meals',
                        style: TextStyle(color: textMain, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      Row(
                        children: [
                          Text('Open', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 14)),
                          const SizedBox(width: 4),
                          Icon(Icons.arrow_forward_rounded, color: textMain, size: 18),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
  Widget _buildDoodleChip({required String label, required bool isSelected, required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(right: 10.0, bottom: 4.0),
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
        decoration: BoxDecoration(
          color: isSelected ? accentColor : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: outlineColor, width: 1.5),
          boxShadow: isSelected ? [BoxShadow(color: outlineColor, offset: const Offset(2, 2), blurRadius: 0)] : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: textMain,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
  Widget _buildSortFilter() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Sort By', style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children: _sortOptions.entries.map((entry) {
                return _buildDoodleChip(
                  label: entry.value,
                  isSelected: _sortBy == entry.key,
                  onTap: () => setState(() => _sortBy = entry.key),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
  Widget _buildPriceFilter() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Max Price', style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: secondaryAccent,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: outlineColor, width: 1.2),
                ),
                child: Text('\$${_maxPrice.toInt()}', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 13)),
              ),
            ],
          ),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: outlineColor,
              inactiveTrackColor: Colors.grey.shade300,
              thumbColor: accentColor,
              trackHeight: 3.5,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 9.0),
            ),
            child: Slider(
              value: _maxPrice,
              min: 5.0,
              max: 100.0,
              onChanged: (value) => setState(() => _maxPrice = value),
            ),
          ),
        ],
      ),
    );
  }
  Widget _buildRatingFilter() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Minimum Rating', style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children: _ratingOptions.map((rating) {
                return _buildDoodleChip(
                  label: rating == 0.0 ? 'Any ⭐' : '$rating+ ⭐',
                  isSelected: _minRating == rating,
                  onTap: () => setState(() => _minRating = rating),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
  Widget _buildCategoryFilter() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Category', style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children: [
                _buildDoodleChip(
                  label: 'All',
                  isSelected: _selectedCategory == null,
                  onTap: () => setState(() => _selectedCategory = null),
                ),
                ..._categories.map((category) {
                  return _buildDoodleChip(
                    label: category,
                    isSelected: _selectedCategory == category,
                    onTap: () => setState(() => _selectedCategory = category),
                  );
                }),
              ],
            ),
          ),
        ],
      ),
    );
  }
  // --- 1-Column Horizontal Card Layout ---
  Widget _buildDishCard(Dish dish, List<Dish> selectedDishes, Position? userPos) {
    final city = _extractCity(dish.restaurantAddress);

    String? distanceText;
    if (userPos != null && dish.lat != null && dish.lon != null) {
      final meters = UserLocationService.calculateDistance(
        userLat: userPos.latitude,
        userLng: userPos.longitude,
        targetLat: dish.lat!,
        targetLng: dish.lon!,
      );
      distanceText = UserLocationService.formatDistance(meters);
    }

    final restaurantInfo = [
      if (dish.restaurantName != null && dish.restaurantName!.isNotEmpty) dish.restaurantName,
      if (city.isNotEmpty) city,
      if (distanceText != null && distanceText.isNotEmpty) distanceText,
    ].join(' • ');

    final favSet = ref.watch(favouritesProvider).value ?? <int>{};
    final isFav = favSet.contains(dish.id);

    final isSelectedForCompare = selectedDishes.any((d) => d.id == dish.id);
    final bool isMaxReached = selectedDishes.length >= 5;
    final bool isCompareDisabled = !isSelectedForCompare && isMaxReached;

    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => DishDetailScreen(dishId: dish.id),
          ),
        );
      },
      child: Stack(
        children: [
          // Main Card Body
          Container(
            margin: const EdgeInsets.only(bottom: 10.0),
            padding: const EdgeInsets.fromLTRB(6.0, 6.0, 12.0, 6.0),
            decoration: _doodleDecoration(
              color: isSelectedForCompare ? const Color(0xFFF6F4FE) : cardColor,
            ),
            child: Row(
              children: [
                // 1. Food Image with Circular Checkbox
                Stack(
                  children: [
                    Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: outlineColor, width: 1.0),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(9),
                        child: dish.imageUrl != null && dish.imageUrl!.isNotEmpty
                            ? Image.network(dish.imageUrl!, fit: BoxFit.cover)
                            : Container(
                                color: const Color(0xFFF0F0F0),
                                child: Icon(Icons.fastfood_outlined, color: textMain, size: 38),
                              ),
                      ),
                    ),
                    // 🔘 Top-Left Circular Selection Indicator (Muted Gray when maxed out, no snackbar)
                    Positioned(
                      top: 5,
                      left: 5,
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: isCompareDisabled
                            ? null // Completely muted/disabled when 5 items selected
                            : () {
                                ref.read(compareProvider.notifier).toggleDish(dish);
                              },
                        child: Container(
                          width: 21,
                          height: 21,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            // Muted gray fill when disabled; Accent when selected; Transparent when unselected
                            color: isCompareDisabled
                                ? Colors.grey.shade300
                                : (isSelectedForCompare ? accentColor : Colors.transparent),
                            border: Border.all(
                              color: isCompareDisabled
                                  ? Colors.grey.shade400
                                  : (isSelectedForCompare ? outlineColor : const Color(0xFFB0B0B0)),
                              width: 1.2,
                            ),
                          ),
                          child: isSelectedForCompare
                              ? Icon(Icons.check_rounded, size: 14, color: textMain)
                              : null,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 12),

                // 2. Dish & Restaurant Details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(right: 28.0),
                        child: Text(
                          dish.name,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: textMain,
                            fontSize: 16.5,
                            fontWeight: FontWeight.w600,
                            height: 1.2,
                          ),
                        ),
                      ),

                      if (restaurantInfo.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(Icons.storefront_outlined, color: textMuted, size: 14),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                restaurantInfo,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(color: textMuted, fontSize: 12.5, fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ),
                      ],
                      const SizedBox(height: 8),
                      // Side-by-Side Badges: [Price Badge] + [Rating Badge]
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(
                              color: secondaryAccent,
                              borderRadius: BorderRadius.circular(7),
                              border: Border.all(color: outlineColor, width: 1.1),
                            ),
                            child: Text(
                              '\$${dish.price.toStringAsFixed(2)}',
                              style: TextStyle(color: textMain, fontSize: 13, fontWeight: FontWeight.w600),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(7),
                              border: Border.all(color: outlineColor, width: 1.1),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.star_rounded, color: Color(0xFFFFB01D), size: 14),
                                const SizedBox(width: 2),
                                Text(
                                  dish.rating.toString(),
                                  style: TextStyle(color: textMain, fontSize: 12, fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Top-Right Floating Heart Button
          Positioned(
            top: 6,
            right: 8,
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () {
                ref.read(favouritesProvider.notifier).toggle(dish.id);
              },
              child: Padding(
                padding: const EdgeInsets.all(6.0),
                child: Icon(
                  isFav ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                  color: isFav ? Colors.redAccent : textMain,
                  size: 23,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}