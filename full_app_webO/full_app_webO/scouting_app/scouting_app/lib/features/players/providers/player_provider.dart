import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../../core/network/api_service.dart';
import '../../../core/network/local_db.dart';
import '../../../core/constants/app_constants.dart';
import '../models/player_model.dart';

class PlayerProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  final LocalDb    _db  = LocalDb();

  List<Player> _players  = [];
  bool         _isLoading = false;
  String       _error     = '';

  List<Player> get players   => _players;
  bool         get isLoading => _isLoading;
  String       get error     => _error;

  // ── Load players (online first, fallback to cache) ─────────────────────────
  Future<void> loadPlayers() async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data = await _api.get(AppConstants.playersUrl);
      final list = (data['results'] as List)
      .map((p) => Player.fromJson(p as Map<String, dynamic>))
      .toList();
      _players = list;
      // Cache for offline
      _players = list;

      if (!kIsWeb) {
        await _db.cachePlayers(
          list.map((p) => p.toJson()..['id'] = p.id).toList(),
        );
      }

    } catch (e, s) {
      if (!kIsWeb) {
        // Fall back to local cache (Android/iOS/Desktop)
        final cached = await _db.getCachedPlayers();
        _players = cached.map((row) => Player(
          id: row['id'],
          fullName: row['full_name'],
          age: row['age'],
          gender: row['gender'],
          dominantFoot: 'right',
          village: row['village'],
          district: row['district'],
          state: row['state'] ?? 'Andhra Pradesh',
          experienceLevel: row['experience'] ?? 'none',
          createdAt: row['created_at'],
        )).toList();
      }
      else {
        // Flutter Web doesn't support sqflite
        _players = [];
      }
    }
    _isLoading = false;
    notifyListeners();
  }

  // ── Create new player ──────────────────────────────────────────────────────
  Future<Player?> createPlayer(Player player) async {
    print("createPlayer() called");
    print(player.toJson());
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data   = await _api.post(AppConstants.playersUrl, player.toJson());
      final created = Player.fromJson(data);
      _players.insert(0, created);
      _isLoading = false;
      notifyListeners();
      return created;

    } catch (e) {
      _error = e is ApiException ? e.message : 'Failed to create player. Will sync when online.';

      // Queue for offline sync
      if (!kIsWeb) {
        await _db.addToSyncQueue(
        action: 'POST',
        endpoint: AppConstants.playersUrl,
        payload: player.toJson(),
        );
      }

      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  // ── Search ─────────────────────────────────────────────────────────────────
  List<Player> search(String query) {
    print("Search query: '$query'");
    print("Total players: ${_players.length}");

    if (query.isEmpty) {
      print("Returning all players");
      return _players;
    }

    final result = _players.where((p) =>
        p.fullName.toLowerCase().contains(query.toLowerCase()) ||
        p.village.toLowerCase().contains(query.toLowerCase())
    ).toList();

    print("Filtered players: ${result.length}");
    return result;
  }
}
