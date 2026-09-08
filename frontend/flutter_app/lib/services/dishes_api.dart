import 'dart:developer' as developer;
import 'package:http/http.dart' as http;
import '../core/network/api_client.dart';
import '../core/network/network_exceptions.dart';
import '../models/dish.dart';
import '../models/compare.dart';


class DishService {
  final ApiClient _apiClient;

  DishService({ApiClient? apiClient, http.Client? client}): _apiClient = apiClient ?? ApiClient(client: client);

  /// 1. Search Dishes with Optional Filters
  Future<List<Dish>> searchDishes({
    String? q,
    double? maxPrice,
    double? minRating,
    String? menuCategory,
  }) async {
    final Map<String, String> queryParams = {};

    if (q != null && q.trim().isNotEmpty) queryParams['q'] = q.trim();
    if (maxPrice != null) queryParams['max_price'] = maxPrice.toString();
    if (minRating != null) queryParams['min_rating'] = minRating.toString();
    if (menuCategory != null && menuCategory.trim().isNotEmpty) {
      queryParams['menu_category'] = menuCategory.trim();
    }

    return _apiClient.getJson<List<Dish>>(
      path: '/dishes/search',
      queryParameters: queryParams,
      endpointName: 'searchDishes',
      onSuccess: (data) {
        if (data is! List) {
          developer.log(
            'JSON format error: Expected List but got ${data.runtimeType}',
            name: 'DishService.searchDishes',
          );
          throw NetworkException(
            'Expected a List from server, but got ${data.runtimeType}',
          );
        }

        return data.map((item) {
          try {
            return Dish.fromJson(item as Map<String, dynamic>);
          } catch (e, stack) {
            developer.log(
              'Failed to parse Dish item: $item',
              error: e,
              stackTrace: stack,
              name: 'DishService.searchDishes',
            );
            throw NetworkException('Failed to parse Dish: $e\nItem payload: $item');
          }
        }).toList();
      },
    );
  }

  /// 2. Fetch Dish Details by ID
  Future<DishDetail> fetchDishDetail(int dishId) async {
    return _apiClient.getJson<DishDetail>(
      path: '/dishes/$dishId',
      endpointName: 'fetchDishDetail',
      onSuccess: (data) => DishDetail.fromJson(data as Map<String, dynamic>),
    );
  }

  ///3. Toggle favourite for a specific dish
  Future<bool> toggleFavourite(int dishId) async {
    return await _apiClient.postJson<bool>(
      path: '/dishes/$dishId/favourite',
      body: {}, // Empty body as dish_id is in the path
      endpointName: 'toggleFavourite',
      onSuccess: (data) {
        if (data is Map<String, dynamic> && data.containsKey('is_favourite')) {
          return data['is_favourite'] as bool;
        }
        return false;
      },
    );
  }

  /// 4. Fetch all favorited dishes for the logged-in user: GET /users/me/favourites
  Future<List<Dish>> fetchFavourites() async {
    return await _apiClient.getJson<List<Dish>>(
      path: '/users/me/favourites',
      endpointName: 'Fetch Favourites',
      onSuccess: (data) {
        if (data is List) {
          return data
              .map((item) => Dish.fromJson(item as Map<String, dynamic>))
              .toList();
        }
        return <Dish>[];
      },
    );
  }

  ///5. Request AI comparison summary
  Future<CompareResponse> fetchCompareSummary({
    required List<int> dishIds,
    double? lat,
    double? lon,
  }) async {
    final payload = CompareRequest(
      dishIds: dishIds,
      userLat: lat,
      userLon: lon,
    );

    return await _apiClient.postJson<CompareResponse>(
      path: '/dishes/compare-summary',
      body: payload.toJson(),
      endpointName: 'fetchCompareSummary',
      onSuccess: (data) {
        if (data is Map<String, dynamic>) {
          return CompareResponse.fromJson(data);
        }
        throw Exception('Invalid server response for compare summary');
      },
    );
  }

}