class Restaurant {
  final int id;
  final String name;
  final String? address;
  final double? lat;
  final double? lon;
  final String? venueType;
  final String? cuisine;
  final String? openingHours;

  const Restaurant({
    required this.id,
    required this.name,
    this.address,
    this.lat,
    this.lon,
    this.venueType,
    this.cuisine,
    this.openingHours,
  });

  factory Restaurant.fromJson(Map<String, dynamic> json) {
    return Restaurant(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      address: json['address'] as String?,
      lat: (json['lat'] as num?)?.toDouble(),
      lon: (json['lon'] as num?)?.toDouble(),
      venueType: json['venue_type'] as String?,
      cuisine: json['cuisine'] as String?,
      openingHours: json['opening_hours'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'address': address,
      'lat': lat,
      'lon': lon,
      'venue_type': venueType,
      'cuisine': cuisine,
      'opening_hours': openingHours,
    };
  }
}