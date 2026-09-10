import 'restaurant.dart';
import 'review.dart';

class Dish {
  final int id;
  final String name;
  final double price;
  final double rating;
  final String menuCategory;
  final String? imageUrl;
  final int? restaurantId;
  final String? restaurantName;
  final String? restaurantAddress;
  final double? lat;
  final double? lon;

  const Dish({
    required this.id,
    required this.name,
    required this.price,
    required this.rating,
    required this.menuCategory,
    this.imageUrl,
    this.restaurantId,
    this.restaurantName,
    this.restaurantAddress,
    this.lat,
    this.lon,
  });

  factory Dish.fromJson(Map<String, dynamic> json) {
    return Dish(
      id: json['dish_id'] ?? json['id'] ?? 0,
      name: json['dish_name'] ?? json['name'] ?? 'Unknown Dish',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      rating: (json['average_rating'] ?? json['rating'] as num?)?.toDouble() ?? 0.0,
      menuCategory: json['menu_category'] as String? ?? 'Mains',
      imageUrl: json['image_url'] as String?,
      restaurantId: json['restaurant_id'] ?? json['restaurant']?['id'],
      restaurantName: json['restaurant_name'] ?? json['restaurant']?['name'],
      restaurantAddress: json['restaurant_address'] ?? json['restaurant']?['address'],
      lat: ((json['lat'] ?? json['restaurant']?['lat']) as num?)?.toDouble(),
      lon: ((json['lon'] ?? json['restaurant']?['lon']) as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'dish_id': id,
      'dish_name': name,
      'price': price,
      'average_rating': rating,
      'menu_category': menuCategory,
      'image_url': imageUrl,
      'restaurant_id': restaurantId,
      'restaurant_name': restaurantName,
      'restaurant_address': restaurantAddress,
      'lat': lat,
      'lon': lon,
    };
  }
}

class DishDetail extends Dish {
  final List<Review> reviews;
  final Restaurant? restaurant;

  const DishDetail({
    required super.id,
    required super.name,
    required super.price,
    required super.rating,
    required super.menuCategory,
    super.imageUrl,
    super.restaurantId,
    super.restaurantName,
    super.restaurantAddress,
    super.lat,
    super.lon,
    required this.reviews,
    this.restaurant,
  });

  factory DishDetail.fromJson(Map<String, dynamic> json) {

    final rawReviews = json['reviews'] as List? ?? [];
    final parsedReviews = rawReviews
        .map((r) => Review.fromJson(r as Map<String, dynamic>))
        .toList();

    final parsedRestaurant = json['restaurant'] != null
        ? Restaurant.fromJson(json['restaurant'] as Map<String, dynamic>)
        : null;

    return DishDetail(
      id: json['dish_id'] ?? json['id'] ?? 0,
      name: json['dish_name'] ?? json['name'] ?? '',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      rating: (json['average_rating'] ?? json['rating'] as num?)?.toDouble() ?? 0.0,
      menuCategory: json['menu_category'] as String? ?? 'Mains',
      imageUrl: json['image_url'] as String?,
      restaurantId: json['restaurant_id'] ?? parsedRestaurant?.id,
      restaurantName: json['restaurant_name'] ?? parsedRestaurant?.name,
      restaurantAddress: json['restaurant_address'] ?? parsedRestaurant?.address,
      lat: ((json['lat'] ?? parsedRestaurant?.lat) as num?)?.toDouble(),
      lon: ((json['lon'] ?? parsedRestaurant?.lon) as num?)?.toDouble(),
      reviews: parsedReviews,
      restaurant: parsedRestaurant,
    );
  }
}