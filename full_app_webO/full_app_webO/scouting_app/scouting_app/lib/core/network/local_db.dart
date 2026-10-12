import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:shared_preferences/shared_preferences.dart';

// sqflite only imported on non-web
import 'local_db_mobile.dart' if (dart.library.html) 'local_db_web.dart'
    as platform_db;

/// LocalDb is the single interface for offline caching.
/// On web  → uses SharedPreferences (JSON-encoded).
/// On mobile/desktop → uses sqflite.
class LocalDb {
  static final LocalDb _instance = LocalDb._internal();
  factory LocalDb() => _instance;
  LocalDb._internal();

  // ── Sync queue ──────────────────────────────────────────────────────────────
  Future<void> addToSyncQueue({
    required String action,
    required String endpoint,
    required Map<String, dynamic> payload,
    String? filePath,
  }) async {
    if (kIsWeb) {
      await _webAddToSyncQueue(
          action: action, endpoint: endpoint, payload: payload);
    } else {
      await platform_db.addToSyncQueue(
          action: action,
          endpoint: endpoint,
          payload: payload,
          filePath: filePath);
    }
  }

  Future<List<Map<String, dynamic>>> getPendingSync() async {
    if (kIsWeb) return _webGetPendingSync();
    return platform_db.getPendingSync();
  }

  Future<void> removeSyncItem(int id) async {
    if (kIsWeb) return _webRemoveSyncItem(id);
    return platform_db.removeSyncItem(id);
  }

  // ── Players ─────────────────────────────────────────────────────────────────
  Future<void> cachePlayers(List<Map<String, dynamic>> players) async {
    if (kIsWeb) return _webSave('cached_players', players);
    return platform_db.cachePlayers(players);
  }

  Future<List<Map<String, dynamic>>> getCachedPlayers() async {
    if (kIsWeb) return _webLoad('cached_players');
    return platform_db.getCachedPlayers();
  }

  // ── Assessments ─────────────────────────────────────────────────────────────
  Future<void> cacheAssessments(List<Map<String, dynamic>> assessments) async {
    if (kIsWeb) return _webSave('cached_assessments', assessments);
    return platform_db.cacheAssessments(assessments);
  }

  Future<List<Map<String, dynamic>>> getCachedAssessments() async {
    if (kIsWeb) return _webLoad('cached_assessments');
    return platform_db.getCachedAssessments();
  }

  // ── Test results ────────────────────────────────────────────────────────────
  Future<void> cacheTestResult(Map<String, dynamic> result) async {
    if (kIsWeb) {
      final existing = await _webLoad('cached_test_results');
      existing.removeWhere((r) => r['id'] == result['id']);
      existing.add(result);
      await _webSave('cached_test_results', existing);
    } else {
      return platform_db.cacheTestResult(result);
    }
  }

  // ── Web helpers (SharedPreferences) ─────────────────────────────────────────
  Future<void> _webSave(String key, List<Map<String, dynamic>> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, jsonEncode(data));
  }

  Future<List<Map<String, dynamic>>> _webLoad(String key) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(key);
    if (raw == null) return [];
    final decoded = jsonDecode(raw) as List;
    return decoded.cast<Map<String, dynamic>>();
  }

  Future<void> _webAddToSyncQueue({
    required String action,
    required String endpoint,
    required Map<String, dynamic> payload,
  }) async {
    final queue = await _webLoad('sync_queue');
    queue.add({
      'id'        : DateTime.now().millisecondsSinceEpoch,
      'action'    : action,
      'endpoint'  : endpoint,
      'payload'   : payload,
      'created_at': DateTime.now().toIso8601String(),
      'attempts'  : 0,
    });
    await _webSave('sync_queue', queue);
  }

  Future<List<Map<String, dynamic>>> _webGetPendingSync() async {
    return _webLoad('sync_queue');
  }

  Future<void> _webRemoveSyncItem(int id) async {
    final queue = await _webLoad('sync_queue');
    queue.removeWhere((item) => item['id'] == id);
    await _webSave('sync_queue', queue);
  }
}
