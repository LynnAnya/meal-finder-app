import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/dish.dart';
import '../services/dishes_api.dart';
import '../providers/fav_provider.dart';
import 'dish_detail_screen.dart';

class FavouriteScreen extends ConsumerStatefulWidget {
  const FavouriteScreen({super.key});

  @override
  ConsumerState<FavouriteScreen> createState() => _FavouritesScreenState();
}

class _FavouritesScreenState extends ConsumerState<FavouriteScreen> {
  // 🎨 Exact Same Playful Theme Colors
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color secondaryAccent = const Color(0xFFFF8FA3);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 159, 156, 156);

  late Future<List<Dish>> _favouritesFuture;

  @override
  void initState() {
    super.initState();
    _loadFavourites();
  }

  void _loadFavourites() {
    if (!mounted) return;
    setState(() {
      _favouritesFuture = DishService().fetchFavourites();
    });
  }

  String _extractCity(String? fullAddress) {
    if (fullAddress == null || fullAddress.trim().isEmpty) return '';
    final parts = fullAddress.split(',');
    return parts.last.trim();
  }

  // 🖍️ Reusable hard-shadow doodle decoration
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
    // ⚡ Auto sync with Riverpod: re-fetch dish cards when an ID is added or changed
    ref.listen<AsyncValue<Set<int>>>(favouritesProvider, (previous, next) {
      if (previous?.value != next.value) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _loadFavourites();
        });
      }
    });

    // 🎯 Live sync with Riverpod favourites state
    final favAsync = ref.watch(favouritesProvider);
    final favSet = favAsync.value ?? <int>{};

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        automaticallyImplyLeading: false, // 👈 Removes '<' icon completely on this 2-column tab screen
        title: Text(
          'Favourite Meals',
          style: TextStyle(
            color: textMain,
            fontWeight: FontWeight.w600,
            fontSize: 22,
          ),
        ),
      ),
      body: RefreshIndicator(
        color: accentColor,
        backgroundColor: cardColor,
        onRefresh: () async {
          _loadFavourites();
          await _favouritesFuture;
        },
        child: FutureBuilder<List<Dish>>(
          future: _favouritesFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Center(
                child: CircularProgressIndicator(color: accentColor),
              );
            } else if (snapshot.hasError) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.lock_clock_outlined, color: outlineColor, size: 50),
                      const SizedBox(height: 12),
                      Text(
                        'Session Expired or Failed to Load',
                        style: TextStyle(
                          color: textMain,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${snapshot.error}'.replaceAll('Exception:', '').trim(),
                        style: TextStyle(color: textMuted, fontSize: 13),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadFavourites,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: accentColor,
                          foregroundColor: textMain,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                            side: BorderSide(color: outlineColor),
                          ),
                        ),
                        child: const Text('Try Again'),
                      ),
                    ],
                  ),
                ),
              );
            } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
              return _buildEmptyView();
            }
            // Filter dishes that are still in Riverpod active favourites set
           final orderedFavIds = favSet.toList().reversed.toList();
            // 2. Map ID -> Dish directly using where/first
            final visibleDishes = <Dish>[];
            for (final id in orderedFavIds) {
              final matchingDishes = snapshot.data!.where((dish) => dish.id == id);
              if (matchingDishes.isNotEmpty) {
                visibleDishes.add(matchingDishes.first);
              }
            }
            // 2-Column Grid Layout
            return GridView.builder(
              physics: const AlwaysScrollableScrollPhysics(
                parent: BouncingScrollPhysics(),
              ),
              padding: const EdgeInsets.all(16.0),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 14.0,
                mainAxisSpacing: 14.0,
                childAspectRatio: 0.72,
              ),
              itemCount: visibleDishes.length,
              itemBuilder: (context, index) {
                return _buildGridCard(visibleDishes[index]);
              },
            );
          },
        ),
      ),
    );
  }

  Widget _buildEmptyView() {
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.favorite_border_rounded, color: textMuted, size: 64),
                const SizedBox(height: 12),
                Text(
                  'No favorites yet!',
                  style: TextStyle(
                    color: textMain,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Heart dishes to save them here.',
                  style: TextStyle(
                    color: textMuted,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildGridCard(Dish dish) {
    final city = _extractCity(dish.restaurantAddress);
    final restaurantInfo = [
      if (dish.restaurantName != null && dish.restaurantName!.isNotEmpty)
        dish.restaurantName,
      if (city.isNotEmpty) city,
    ].join(' • ');

    return GestureDetector(
      onTap: () async {
        // When clicking to view details, DishDetailScreen still has its own back button '<'
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => DishDetailScreen(dishId: dish.id),
          ),
        );
      },
      child: Container(
        decoration: _doodleDecoration(),
        padding: const EdgeInsets.all(10.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Food Image with Heart Overlay
            Stack(
              children: [
                Container(
                  width: double.infinity,
                  height: 110,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: outlineColor, width: 1.0),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(9),
                    child: dish.dishImagePath != null && dish.dishImagePath!.isNotEmpty
                        ? Image.network(
                            dish.dishImagePath!,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) =>
                                Container(
                              color: const Color(0xFFF0F0F0),
                              child: Icon(
                                Icons.fastfood_outlined,
                                color: textMain,
                                size: 36,
                              ),
                            ),
                          )
                        : Container(
                            color: const Color(0xFFF0F0F0),
                            child: Icon(
                              Icons.fastfood_outlined,
                              color: textMain,
                              size: 36,
                            ),
                          ),
                  ),
                ),
               Positioned(
                top: 6,
                right: 6,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () {ref.read(favouritesProvider.notifier).toggle(dish.id);
                  },
                  child: const Padding(
                    padding: EdgeInsets.all(4.0),
                    child: Icon(
                      Icons.favorite_rounded,
                      color: Colors.redAccent,
                      size: 22,
                    ),
                  ),
                ),
              ),
              ],
            ),
            const SizedBox(height: 8),
            // 2. Dish Name
            Text(
              dish.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: textMain,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),

            // 3. Restaurant / City
            if (restaurantInfo.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                restaurantInfo,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: textMuted,
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],

            const Spacer(),

            // 4. Badges (Price & Rating)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: secondaryAccent,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: outlineColor, width: 1.0),
                  ),
                  child: Text(
                    '\$${dish.price.toStringAsFixed(2)}',
                    style: TextStyle(
                      color: textMain,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: outlineColor, width: 1.0),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.star_rounded,
                        color: Color(0xFFFFB01D),
                        size: 14,
                      ),
                      const SizedBox(width: 2),
                      Text(
                        dish.rating.toString(),
                        style: TextStyle(
                          color: textMain,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}