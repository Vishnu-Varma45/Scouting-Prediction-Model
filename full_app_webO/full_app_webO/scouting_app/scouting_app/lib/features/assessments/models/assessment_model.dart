import '../../players/models/player_model.dart';

class TestResult {
  final int?   id;
  final int    assessmentId;
  final String testType;
  final String status;
  final double? score;
  final Map<String, dynamic>? metrics;
  final String? error;
  final String? createdAt;

  TestResult({
    this.id,
    required this.assessmentId,
    required this.testType,
    required this.status,
    this.score,
    this.metrics,
    this.error,
    this.createdAt,
  });

  factory TestResult.fromJson(Map<String, dynamic> json) => TestResult(
    id:           json['id'],
    assessmentId: json['assessment'] ?? 0,
    testType:     json['test_type'] ?? '',
    status:       json['status'] ?? 'pending',
    score:        json['score']?.toDouble(),
    metrics:      json['metrics'] as Map<String, dynamic>?,
    error:        json['error'],
    createdAt:    json['created_at'],
  );

  bool get isCompleted  => status == 'completed';
  bool get isProcessing => status == 'processing';
  bool get isFailed     => status == 'failed';
  bool get isPending    => status == 'pending';

  String get testLabel {
    const labels = {
      'sprint'  : '0–10m Sprint',
      'jump'    : 'Vertical Jump',
      'shuttle' : 'Shuttle Run',
      'cone'    : '3-Colour Cone Picking',
      'footwork': 'Shadow Footwork',
    };
    return labels[testType] ?? testType;
  }

  String get testEmoji {
    const emojis = {
      'sprint'  : '🏃',
      'jump'    : '⬆️',
      'shuttle' : '🔄',
      'cone'    : '🎯',
      'footwork': '👣',
    };
    return emojis[testType] ?? '📋';
  }
}

class Assessment {
  final int?   id;
  final int    playerId;
  final Player? player;
  final String status;
  final String scoutNotes;
  final double? overallScore;
  final bool?  recommendation;
  final List<TestResult> testResults;
  final String? createdAt;

  Assessment({
    this.id,
    required this.playerId,
    this.player,
    required this.status,
    this.scoutNotes = '',
    this.overallScore,
    this.recommendation,
    this.testResults = const [],
    this.createdAt,
  });

  factory Assessment.fromJson(Map<String, dynamic> json) {
    final results = (json['test_results'] as List<dynamic>? ?? [])
        .map((r) => TestResult.fromJson(r as Map<String, dynamic>))
        .toList();

    Player? player;
    if (json['player_detail'] != null) {
      player = Player.fromJson(json['player_detail'] as Map<String, dynamic>);
    }

    return Assessment(
      id:             json['id'],
      playerId:       json['player'] ?? 0,
      player:         player,
      status:         json['status'] ?? 'draft',
      scoutNotes:     json['scout_notes'] ?? '',
      overallScore:   json['overall_score']?.toDouble(),
      recommendation: json['recommendation'],
      testResults:    results,
      createdAt:      json['created_at'],
    );
  }

  Map<String, dynamic> toJson() => {
    'player'      : playerId,
    'scout_notes' : scoutNotes,
  };

  int get completedTests => testResults.where((t) => t.isCompleted).length;
  int get totalTests     => 5;
  bool get allDone       => completedTests == totalTests;

  TestResult? getTest(String testType) {
    try {
      return testResults.firstWhere((t) => t.testType == testType);
    } catch (_) {
      return null;
    }
  }

  String get playerName => player?.fullName ?? 'Player #$playerId';
}
