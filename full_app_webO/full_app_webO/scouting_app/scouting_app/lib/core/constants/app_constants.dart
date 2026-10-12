class AppConstants {
  // ── API ───────────────────────────────────────────────────────────────────
  static const String baseUrl = 'http://127.0.0.1:8000';
  static const String apiBase = '$baseUrl/api';

  static const String loginUrl   = '$apiBase/auth/login/';
  static const String signupUrl = '$apiBase/auth/signup/';
  static const String logoutUrl  = '$apiBase/auth/logout/';
  static const String profileUrl = '$apiBase/auth/profile/';

  static const String playersUrl = '$apiBase/players/';
  static String playerDetailUrl(int id) => '$apiBase/players/$id/';

  static const String assessmentsUrl = '$apiBase/assessments/';
  static String assessmentDetailUrl(int id)  => '$apiBase/assessments/$id/';
  static String assessmentScoreUrl(int id)   => '$apiBase/assessments/$id/score/';
  static String testUploadUrl(int assessmentId, String testType) =>
      '$apiBase/assessments/$assessmentId/tests/$testType/upload/';

  // ── App ───────────────────────────────────────────────────────────────────
  static const String appName    = 'Scouting AI';
  static const String appVersion = '1.0.0';

  // ── Tests ─────────────────────────────────────────────────────────────────
  static const List<Map<String, String>> testTypes = [
    {'key': 'sprint',   'label': '0–10m Sprint',         'emoji': '🏃'},
    {'key': 'jump',     'label': 'Vertical Jump',         'emoji': '⬆️'},
    {'key': 'shuttle',  'label': 'Shuttle Run',           'emoji': '🔄'},
    {'key': 'cone',     'label': '3-Colour Cone Picking', 'emoji': '🎯'},
    {'key': 'footwork', 'label': 'Shadow Footwork',       'emoji': '👣'},
  ];

  // ── Score bands ───────────────────────────────────────────────────────────
  static String scoreBand(double score) {
    if (score >= 90) return 'Elite';
    if (score >= 70) return 'Strong';
    if (score >= 50) return 'Threshold';
    if (score >= 30) return 'Below Threshold';
    return 'Needs Development';
  }

  // ── Local storage keys ────────────────────────────────────────────────────
  static const String tokenKey    = 'auth_token';
  static const String userIdKey   = 'user_id';
  static const String usernameKey = 'username';
  static const String fullNameKey = 'full_name';
}
