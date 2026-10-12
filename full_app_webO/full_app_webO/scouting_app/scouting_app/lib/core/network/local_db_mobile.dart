import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

Database? _db;

Future<Database> _getDb() async {
  if (_db != null) return _db!;
  final dbPath = await getDatabasesPath();
  final path   = join(dbPath, 'scouting_offline.db');
  _db = await openDatabase(path, version: 1, onCreate: _onCreate);
  return _db!;
}

Future<void> _onCreate(Database db, int version) async {
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

Future<void> addToSyncQueue({
  required String action,
  required String endpoint,
  required Map<String, dynamic> payload,
  String? filePath,
}) async {
  final db = await _getDb();
  await db.insert('sync_queue', {
    'action'    : action,
    'endpoint'  : endpoint,
    'payload'   : jsonEncode(payload),
    'file_path' : filePath,
    'created_at': DateTime.now().toIso8601String(),
    'attempts'  : 0,
  });
}

Future<List<Map<String, dynamic>>> getPendingSync() async {
  final db = await _getDb();
  return db.query('sync_queue', orderBy: 'created_at ASC');
}

Future<void> removeSyncItem(int id) async {
  final db = await _getDb();
  await db.delete('sync_queue', where: 'id = ?', whereArgs: [id]);
}

Future<void> cachePlayers(List<Map<String, dynamic>> players) async {
  final db    = await _getDb();
  final batch = db.batch();
  for (final p in players) {
    batch.insert('players', {
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
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }
  await batch.commit(noResult: true);
}

Future<List<Map<String, dynamic>>> getCachedPlayers() async {
  final db = await _getDb();
  return db.query('players', orderBy: 'created_at DESC');
}

Future<void> cacheAssessments(List<Map<String, dynamic>> assessments) async {
  final db    = await _getDb();
  final batch = db.batch();
  for (final a in assessments) {
    batch.insert('assessments', {
      'id'            : a['id'],
      'player_id'     : a['player'],
      'player_name'   : a['player_name'],
      'status'        : a['status'],
      'overall_score' : a['overall_score'],
      'scout_notes'   : a['scout_notes'],
      'recommendation': a['recommendation'] == true ? 1 : 0,
      'created_at'    : a['created_at'],
      'synced'        : 1,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }
  await batch.commit(noResult: true);
}

Future<List<Map<String, dynamic>>> getCachedAssessments() async {
  final db = await _getDb();
  return db.query('assessments', orderBy: 'created_at DESC');
}

Future<void> cacheTestResult(Map<String, dynamic> result) async {
  final db = await _getDb();
  await db.insert('test_results', {
    'id'            : result['id'],
    'assessment_id' : result['assessment'],
    'test_type'     : result['test_type'],
    'status'        : result['status'],
    'score'         : result['score'],
    'metrics'       : jsonEncode(result['metrics'] ?? {}),
    'synced'        : 1,
  }, conflictAlgorithm: ConflictAlgorithm.replace);
}
