import 'package:flutter/foundation.dart';
import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class LocalDb {
  static final LocalDb _instance = LocalDb._internal();
  factory LocalDb() => _instance;
  LocalDb._internal();

  Database? _db;

  Future<Database> get db async {
    _db ??= await _initDb();
    return _db!;
  }

  Future<Database> _initDb() async {
    if (kIsWeb) {
      throw UnsupportedError("SQLite is not supported on Flutter Web");
    }

    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'scouting_offline.db');

    return openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    // Pending sync queue — stores any action that failed due to no internet
    await db.execute('''
      CREATE TABLE sync_queue (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        action      TEXT NOT NULL,
        endpoint    TEXT NOT NULL,
        payload     TEXT NOT NULL,
        file_path   TEXT,
        created_at  TEXT NOT NULL,
        attempts    INTEGER DEFAULT 0
      )
    ''');

    // Local player cache
    await db.execute('''
      CREATE TABLE players (
        id           INTEGER PRIMARY KEY,
        full_name    TEXT NOT NULL,
        age          INTEGER,
        gender       TEXT,
        village      TEXT,
        district     TEXT,
        state        TEXT,
        height_cm    REAL,
        weight_kg    REAL,
        experience   TEXT,
        created_at   TEXT,
        synced       INTEGER DEFAULT 1
      )
    ''');

    // Local assessment cache
    await db.execute('''
      CREATE TABLE assessments (
        id            INTEGER PRIMARY KEY,
        player_id     INTEGER,
        player_name   TEXT,
        status        TEXT,
        overall_score REAL,
        scout_notes   TEXT,
        recommendation INTEGER,
        created_at    TEXT,
        synced        INTEGER DEFAULT 1
      )
    ''');

    // Local test results cache
    await db.execute('''
      CREATE TABLE test_results (
        id            INTEGER PRIMARY KEY,
        assessment_id INTEGER,
        test_type     TEXT,
        status        TEXT,
        score         REAL,
        metrics       TEXT,
        video_path    TEXT,
        synced        INTEGER DEFAULT 1
      )
    ''');
  }

  // ── Sync queue ─────────────────────────────────────────────────────────────
  Future<int> addToSyncQueue({
    required String action,
    required String endpoint,
    required Map<String, dynamic> payload,
    String? filePath,
  }) async {
    final database = await db;
    return database.insert('sync_queue', {
      'action'    : action,
      'endpoint'  : endpoint,
      'payload'   : jsonEncode(payload),
      'file_path' : filePath,
      'created_at': DateTime.now().toIso8601String(),
      'attempts'  : 0,
    });
  }

  Future<List<Map<String, dynamic>>> getPendingSync() async {
    final database = await db;
    return database.query('sync_queue', orderBy: 'created_at ASC');
  }

  Future<void> removeSyncItem(int id) async {
    final database = await db;
    await database.delete('sync_queue', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> incrementSyncAttempt(int id) async {
    final database = await db;
    await database.rawUpdate(
      'UPDATE sync_queue SET attempts = attempts + 1 WHERE id = ?', [id]
    );
  }

  // ── Players ────────────────────────────────────────────────────────────────
  Future<void> cachePlayers(List<Map<String, dynamic>> players) async {
    final database = await db;
    final batch    = database.batch();
    for (final p in players) {
      batch.insert(
        'players', {
          'id'        : p['id'],
          'full_name' : p['full_name'],
          'age'       : p['age'],
          'gender'    : p['gender'],
          'village'   : p['village'],
          'district'  : p['district'],
          'state'     : p['state'],
          'height_cm' : p['height_cm'],
          'weight_kg' : p['weight_kg'],
          'experience': p['experience_level'],
          'created_at': p['created_at'],
          'synced'    : 1,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<List<Map<String, dynamic>>> getCachedPlayers() async {
    final database = await db;
    return database.query('players', orderBy: 'created_at DESC');
  }

  // ── Assessments ────────────────────────────────────────────────────────────
  Future<void> cacheAssessments(List<Map<String, dynamic>> assessments) async {
    final database = await db;
    final batch    = database.batch();
    for (final a in assessments) {
      batch.insert(
        'assessments', {
          'id'            : a['id'],
          'player_id'     : a['player'],
          'player_name'   : a['player_name'],
          'status'        : a['status'],
          'overall_score' : a['overall_score'],
          'scout_notes'   : a['scout_notes'],
          'recommendation': a['recommendation'] == true ? 1 : 0,
          'created_at'    : a['created_at'],
          'synced'        : 1,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<List<Map<String, dynamic>>> getCachedAssessments() async {
    final database = await db;
    return database.query('assessments', orderBy: 'created_at DESC');
  }

  // ── Test results ───────────────────────────────────────────────────────────
  Future<void> cacheTestResult(Map<String, dynamic> result) async {
    final database = await db;
    await database.insert(
      'test_results', {
        'id'            : result['id'],
        'assessment_id' : result['assessment'],
        'test_type'     : result['test_type'],
        'status'        : result['status'],
        'score'         : result['score'],
        'metrics'       : jsonEncode(result['metrics'] ?? {}),
        'synced'        : 1,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
}
