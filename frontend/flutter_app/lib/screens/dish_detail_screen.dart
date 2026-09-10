import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../models/dish.dart';
import '../models/review.dart';
import '../providers/user_provider.dart';
import '../providers/fav_provider.dart';
import '../providers/location_provider.dart';
import '../services/dishes_api.dart';
import '../services/reviews_api.dart';
import '../services/user_location.dart';

class DishDetailScreen extends ConsumerStatefulWidget {
  final int dishId;
  const DishDetailScreen({super.key, required this.dishId});

  @override
  ConsumerState<DishDetailScreen> createState() => _DishDetailScreenState();
}

class _DishDetailScreenState extends ConsumerState<DishDetailScreen> {
  // 🎨 Exact Same Theme Colors
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color secondaryAccent = const Color(0xFFFF8FA3);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 159, 156, 156);
  late Future<DishDetail> _dishDetailFuture;

  @override
  void initState() {
    super.initState();
    _dishDetailFuture = DishService().fetchDishDetail(widget.dishId);
  }

  // 🖍️ Hard-shadow doodle decoration
  BoxDecoration _doodleDecoration({Color? color, double borderRadius = 12.5}) {
    return BoxDecoration(
      color: color ?? cardColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: outlineColor, width: 0.5),
      boxShadow: [
        BoxShadow(
          color: outlineColor,
          offset: const Offset(2, 2),
          blurRadius: 0,
        ),
      ],
    );
  }

  // Write/Edit Review Bottom Sheet Overlay
  void _showWriteReviewSheet(BuildContext context, int dishId, {Review? existingReview}) {
    final bool isEditing = existingReview != null;
    int selectedRating = existingReview?.rating ?? 5;
    bool isSubmitting = false;
    final TextEditingController commentController = TextEditingController(
      text: existingReview?.comment ?? '',
    );

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
          ),
          child: StatefulBuilder(
            builder: (BuildContext context, StateSetter setModalState) {
              return Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                  border: Border.all(color: outlineColor, width: 2),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isEditing ? 'Edit your review' : 'Leave a review',
                      style: TextStyle(color: textMain, fontSize: 22, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(5, (index) {
                        return IconButton(
                          icon: Icon(
                            index < selectedRating ? Icons.star_rounded : Icons.star_border_rounded,
                            color: const Color(0xFFFFB01D),
                            size: 40,
                          ),
                          onPressed: isSubmitting
                              ? null
                              : () {
                                  setModalState(() {
                                    selectedRating = index + 1;
                                  });
                                },
                        );
                      }),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: commentController,
                      maxLines: 3,
                      enabled: !isSubmitting,
                      decoration: InputDecoration(
                        hintText: 'What did you think of this dish?',
                        filled: true,
                        fillColor: cardColor,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12.5),
                          borderSide: BorderSide(color: outlineColor),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12.5),
                          borderSide: BorderSide(color: outlineColor),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12.5),
                          borderSide: BorderSide(color: outlineColor, width: 2),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    GestureDetector(
                      onTap: isSubmitting
                          ? null
                          : () async {
                              final String rawComment = commentController.text.trim();
                              final String? comment = rawComment.isEmpty ? null : rawComment;
                              setModalState(() {
                                isSubmitting = true;
                              });
                              try {
                                if (isEditing) {
                                  await ReviewService().updateReview(
                                    reviewId: existingReview.reviewId,
                                    rating: selectedRating,
                                    comment: comment,
                                  );
                                } else {
                                  await ReviewService().createReview(
                                    dishId: dishId,
                                    rating: selectedRating,
                                    comment: comment,
                                  );
                                }

                                if (context.mounted) {
                                  Navigator.pop(context);
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(isEditing ? 'Review updated!' : 'Review submitted!'),
                                      backgroundColor: outlineColor,
                                      behavior: SnackBarBehavior.floating,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                    ),
                                  );
                                  setState(() {
                                    _dishDetailFuture = DishService().fetchDishDetail(widget.dishId);
                                  });
                                }
                              } catch (e) {
                                if (context.mounted) {
                                  final errorString = e.toString().toLowerCase();
                                  String displayMessage = 'Oops! Failed to submit: $e';
                                  if (errorString.contains('user not found') || errorString.contains('401')) {
                                    Navigator.pop(context);
                                    displayMessage = 'Please log in to review.';
                                  } else if (errorString.contains('already reviewed') || errorString.contains('409')) {
                                    setModalState(() {
                                      isSubmitting = false;
                                    });
                                    displayMessage = 'You have already reviewed this dish! 🍽️';
                                  } else {
                                    setModalState(() {
                                      isSubmitting = false;
                                    });
                                    displayMessage = 'Oops! Something went wrong. Please try again. ⚠️';
                                  }

                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(displayMessage),
                                      backgroundColor: Colors.redAccent,
                                      behavior: SnackBarBehavior.floating,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                    ),
                                  );
                                }
                              }
                            },
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        decoration: _doodleDecoration(
                          color: isSubmitting ? Colors.grey.shade300 : accentColor,
                        ),
                        alignment: Alignment.center,
                        child: isSubmitting
                            ? SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  color: textMain,
                                  strokeWidth: 2,
                                ),
                              )
                            : Text(
                                isEditing ? 'Update Review' : 'Submit Review',
                                style: TextStyle(
                                  color: isSubmitting ? textMuted : textMain,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final userState = ref.watch(userProvider);
    final currentUser = userState.value;
    final favSet = ref.watch(favouritesProvider).value ?? <int>{};
    final isFav = favSet.contains(widget.dishId);
    final Position userPos = ref.watch(locationProvider) ?? UserLocationService.defaultLocation;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: IconThemeData(color: textMain),
      ),
      body: FutureBuilder<DishDetail>(
        future: _dishDetailFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator(color: accentColor));
          } else if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}', style: TextStyle(color: textMain)));
          } else if (!snapshot.hasData) {
            return Center(child: Text('Dish not found.', style: TextStyle(color: textMain)));
          }

          final dish = snapshot.data!;
          // Calculate distance 
          String? distanceBadge;
          if (dish.lat != null && dish.lon != null) {
            final meters = UserLocationService.calculateDistance(
              userLat: userPos.latitude,
              userLng: userPos.longitude,
              targetLat: dish.lat!,
              targetLng: dish.lon!,
            );
            distanceBadge = UserLocationService.formatDistance(meters);
          }

          // Combine Address with Distance: "Address • 450m"
          final addressWithDistance = [
            if (dish.restaurantAddress != null && dish.restaurantAddress!.isNotEmpty)
              dish.restaurantAddress,
            if (distanceBadge != null && distanceBadge.isNotEmpty)
              distanceBadge,
          ].join(' • ');

          // Check existing review
          Review? existingReview;
          if (currentUser != null) {
            for (final r in dish.reviews) {
              if (r.reviewer.username == currentUser.username) {
                existingReview = r;
                break;
              }
            }
          }
          final bool hasReviewed = existingReview != null;

          return SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Top Image with Doodle Border
                Stack(
                  children: [
                    Container(
                      width: double.infinity,
                      height: 250,
                      decoration: _doodleDecoration(borderRadius: 16),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(15),
                        child: dish.imageUrl != null && dish.imageUrl!.isNotEmpty
                            ? Image.network(dish.imageUrl!, fit: BoxFit.cover)
                            : Container(
                                color: const Color(0xFFF0F0F0),
                                child: Icon(Icons.fastfood_outlined, color: textMain, size: 80),
                              ),
                      ),
                    ),
                    Positioned(
                      top: 12,
                      right: 12,
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () {
                          ref.read(favouritesProvider.notifier).toggle(widget.dishId);
                        },
                        child: Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Icon(
                            isFav ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                            color: isFav ? Colors.redAccent : textMain,
                            size: 28,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // 2. Dish Info (Price, Rating, Category - isSpicy & description removed)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Text(
                              dish.name,
                              style: TextStyle(color: textMain, fontSize: 24, fontWeight: FontWeight.w700),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: secondaryAccent,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: outlineColor, width: 1.5),
                            ),
                            child: Text(
                              '\$${dish.price.toStringAsFixed(2)}',
                              style: TextStyle(color: textMain, fontSize: 18, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Icon(Icons.star_rounded, color: const Color(0xFFFFB01D), size: 22),
                          const SizedBox(width: 4),
                          Text(
                            dish.rating.toString(),
                            style: TextStyle(color: textMain, fontSize: 16, fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(width: 16),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: accentColor,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: outlineColor, width: 1),
                            ),
                            child: Text(
                              dish.menuCategory,
                              style: TextStyle(color: textMain, fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // 3. Restaurant Details + Distance Text
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        dish.restaurantName ?? 'Unknown Restaurant',
                        style: TextStyle(color: textMain, fontSize: 16, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.location_on_outlined, color: textMuted, size: 16),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              addressWithDistance.isNotEmpty
                                  ? addressWithDistance
                                  : 'No address provided',
                              style: TextStyle(color: textMuted, fontSize: 14),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                // 4. Light Gray Line Separator
                const SizedBox(height: 24),
                Divider(color: Colors.grey.shade300, thickness: 1.0, height: 1.0),
                const SizedBox(height: 24),

                // 5. Reviews Section Header & Write/Edit Button
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Reviews',
                      style: TextStyle(color: textMain, fontSize: 20, fontWeight: FontWeight.w700),
                    ),
                    GestureDetector(
                      onTap: () {
                        if (currentUser == null) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Please log in to leave a review!')),
                          );
                          return;
                        }
                        _showWriteReviewSheet(context, widget.dishId, existingReview: existingReview);
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: _doodleDecoration(color: accentColor, borderRadius: 20),
                        child: Text(
                          hasReviewed ? 'Edit Review' : '+ Write Review',
                          style: TextStyle(color: textMain, fontSize: 14, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 6. Reviews List
                if (dish.reviews.isEmpty)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
                    decoration: _doodleDecoration(color: Colors.white),
                    child: Column(
                      children: [
                        Icon(Icons.edit_note_rounded, color: textMuted, size: 48),
                        const SizedBox(height: 12),
                        Text(
                          'No reviews yet!',
                          style: TextStyle(color: textMain, fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Be the first to try and review this dish.',
                          style: TextStyle(color: textMuted, fontSize: 14),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  )
                else
                  ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: dish.reviews.length,
                    separatorBuilder: (context, index) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final review = dish.reviews[index];
                      return Container(
                        padding: const EdgeInsets.all(16),
                        decoration: _doodleDecoration(color: Colors.white),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '@${review.reviewer.username}',
                                  style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 15),
                                ),
                                Row(
                                  children: List.generate(5, (starIndex) {
                                    return Icon(
                                      starIndex < review.rating ? Icons.star_rounded : Icons.star_border_rounded,
                                      color: const Color(0xFFFFB01D),
                                      size: 16,
                                    );
                                  }),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            if (review.comment != null && review.comment!.isNotEmpty)
                              Text(
                                review.comment!,
                                style: TextStyle(color: textMain, fontSize: 14, height: 1.4),
                              ),
                            const SizedBox(height: 8),
                            Text(
                              '${review.createdAt.day}/${review.createdAt.month}/${review.createdAt.year}',
                              style: TextStyle(color: textMuted, fontSize: 12),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                const SizedBox(height: 32),
              ],
            ),
          );
        },
      ),
    );
  }
}