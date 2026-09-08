class CompareRequest {
  final List<int> dishIds;
  final double? userLat;
  final double? userLon;

  const CompareRequest({
    required this.dishIds,
    this.userLat,
    this.userLon,
  });

  Map<String, dynamic> toJson() {
    return {
      'dish_ids': dishIds,
      if (userLat != null) 'user_lat': userLat,
      if (userLon != null) 'user_lon': userLon,
    };
  }
}

class CompareResponse {
  final String verdict;
  final List<String> tradeOffBreakdown;
  final String bestValuePick;
  final String bestTastePick;

  const CompareResponse({
    required this.verdict,
    required this.tradeOffBreakdown,
    required this.bestValuePick,
    required this.bestTastePick,
  });

  factory CompareResponse.fromJson(Map<String, dynamic> json) {
    final rawBreakdown = json['trade_off_breakdown'] as List? ?? [];
    return CompareResponse(
      verdict: json['verdict'] as String? ?? 'No verdict generated.',
      tradeOffBreakdown: rawBreakdown.map((e) => e.toString()).toList(),
      bestValuePick: json['best_value_pick'] as String? ?? '',
      bestTastePick: json['best_taste_pick'] as String? ?? '',
    );
  }
}