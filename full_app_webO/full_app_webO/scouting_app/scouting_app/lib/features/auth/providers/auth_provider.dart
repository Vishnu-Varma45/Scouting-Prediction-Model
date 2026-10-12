import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_service.dart';
import '../../../core/constants/app_constants.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  bool   _isLoading = false;
  bool   _isLoggedIn = false;
  String _token    = '';
  int    _userId   = 0;
  String _username = '';
  String _fullName = '';
  String _error    = '';

  bool   get isLoading  => _isLoading;
  bool   get isLoggedIn => _isLoggedIn;
  String get token      => _token;
  int    get userId     => _userId;
  String get username   => _username;
  String get fullName   => _fullName;
  String get error      => _error;

  // Check if token exists in storage (app launch)
  Future<void> checkAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(AppConstants.tokenKey);
    if (token != null && token.isNotEmpty) {
      _token      = token;
      _userId     = prefs.getInt(AppConstants.userIdKey) ?? 0;
      _username   = prefs.getString(AppConstants.usernameKey) ?? '';
      _fullName   = prefs.getString(AppConstants.fullNameKey) ?? '';
      _isLoggedIn = true;
      notifyListeners();
    }
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data = await _api.login(username, password);

      _token    = data['token'];
      _userId   = data['user_id'];
      _username = data['username'];
      _fullName = data['full_name'] ?? '';

      // Persist to local storage
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(AppConstants.tokenKey,    _token);
      await prefs.setInt(AppConstants.userIdKey,      _userId);
      await prefs.setString(AppConstants.usernameKey, _username);
      await prefs.setString(AppConstants.fullNameKey, _fullName);

      _isLoggedIn = true;
      _isLoading  = false;
      notifyListeners();
      return true;

    } catch (e) {
      _error     = e is ApiException ? e.message : 'Login failed. Check your connection.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<bool> signup({
    required String username,
    required String password,
    String fullName = '',
    String email    = '',
  }) async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data = await _api.post(AppConstants.signupUrl, {
        'username' : username,
        'password' : password,
        'full_name': fullName,
        'email'    : email,
      });

      _token    = data['token'];
      _userId   = data['user_id'];
      _username = data['username'];
      _fullName = data['full_name'] ?? '';

      // Persist to local storage
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(AppConstants.tokenKey,    _token);
      await prefs.setInt(AppConstants.userIdKey,      _userId);
      await prefs.setString(AppConstants.usernameKey, _username);
      await prefs.setString(AppConstants.fullNameKey, _fullName);

      _isLoggedIn = true;
      _isLoading  = false;
      notifyListeners();
      return true;

    } catch (e) {
      _error     = e is ApiException ? e.message : 'Signup failed. Check your connection.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _api.post(AppConstants.logoutUrl, {});
    } catch (_) {}

    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    _token      = '';
    _userId     = 0;
    _username   = '';
    _fullName   = '';
    _isLoggedIn = false;
    notifyListeners();
  }
}
