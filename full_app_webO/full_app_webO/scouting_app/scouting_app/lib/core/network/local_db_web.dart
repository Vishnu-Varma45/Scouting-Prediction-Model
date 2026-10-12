// Web stub — all actual web storage is handled inside local_db.dart
// using SharedPreferences. These functions are never called on web
// because local_db.dart checks kIsWeb before calling platform_db.

Future<void> addToSyncQueue({
  required String action,
  required String endpoint,
  required Map<String, dynamic> payload,
  String? filePath,
}) async {}

Future<List<Map<String, dynamic>>> getPendingSync() async => [];

Future<void> removeSyncItem(int id) async {}

Future<void> cachePlayers(List<Map<String, dynamic>> players) async {}

Future<List<Map<String, dynamic>>> getCachedPlayers() async => [];

Future<void> cacheAssessments(List<Map<String, dynamic>> assessments) async {}

Future<List<Map<String, dynamic>>> getCachedAssessments() async => [];

Future<void> cacheTestResult(Map<String, dynamic> result) async {}
