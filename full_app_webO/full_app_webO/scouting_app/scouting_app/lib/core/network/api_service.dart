import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:mime/mime.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/app_constants.dart';

class ApiService {
  // ── Singleton ──────────────────────────────────────────────────────────────
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  // ── Auth token ─────────────────────────────────────────────────────────────
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(AppConstants.tokenKey);
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _getToken();
    return {
      'Content-Type':  'application/json',
      'Authorization': 'Token $token',
    };
  }

  // ── Generic GET ────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> get(String url) async {
    final headers  = await _authHeaders();
    final response = await http.get(Uri.parse(url), headers: headers);
    return _handleResponse(response);
  }

  // ── Generic POST (JSON) ────────────────────────────────────────────────────
  Future<Map<String, dynamic>> post(String url, Map<String, dynamic> body) async {
    final headers = await _authHeaders();
    try {
      final response = await http.post(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(body),
      );
      return _handleResponse(response);
    } catch (e) {
      print('HTTP POST ERROR: $e');
      rethrow;
    }
  }

  // ── Generic PATCH ──────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> patch(String url, Map<String, dynamic> body) async {
    final headers  = await _authHeaders();
    final response = await http.patch(
      Uri.parse(url),
      headers: headers,
      body: jsonEncode(body),
    );
    return _handleResponse(response);
  }

  // ── Multipart video upload — works on Web + Android + iOS ─────────────────
  // Accepts XFile (from image_picker) instead of dart:io File.
  // On web  → reads bytes via xFile.readAsBytes()
  // On mobile → reads bytes the same way (XFile works on all platforms)
  Future<Map<String, dynamic>> uploadVideo({
    required String url,
    required XFile  xFile,
    Map<String, String>? extraFields,
  }) async {
    final token   = await _getToken();
    final request = http.MultipartRequest('POST', Uri.parse(url));

    request.headers['Authorization'] = 'Token $token';

    // Read file bytes — works on both web and mobile
    final Uint8List bytes    = await xFile.readAsBytes();
    final String   filename  = xFile.name.isNotEmpty
        ? xFile.name
        : xFile.path.split('/').last;

    // Detect MIME type
    final String mimeType = xFile.mimeType ??
        lookupMimeType(filename) ??
        'video/mp4';

    request.files.add(
      http.MultipartFile.fromBytes(
        'video',
        bytes,
        filename: filename,
        contentType: _parseMediaType(mimeType),
      ),
    );

    // Extra fields (e.g. calibration_points for footwork)
    if (extraFields != null) {
      request.fields.addAll(extraFields);
    }

    final streamed  = await request.send();
    final response  = await http.Response.fromStream(streamed);
    return _handleResponse(response);
  }

  // ── Login ──────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse(AppConstants.loginUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    return _handleResponse(response);
  }

  // ── Response handler ───────────────────────────────────────────────────────
  Map<String, dynamic> _handleResponse(http.Response response) {
    final body = jsonDecode(response.body);

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (body is List) {
        return {'results': body, 'count': body.length};
      }
      return body as Map<String, dynamic>;
    }

    final errorMsg = body is Map
        ? (body['error'] ?? body['detail'] ?? 'Unknown error')
        : 'Request failed (${response.statusCode})';

    throw ApiException(
      message:    errorMsg.toString(),
      statusCode: response.statusCode,
    );
  }

  // ── Helper: parse "video/mp4" → MediaType ─────────────────────────────────
  dynamic _parseMediaType(String mimeType) {
    try {
      final parts = mimeType.split('/');
      if (parts.length == 2) {
        // http package accepts MediaType — build it from type/subtype
        return http.MediaType(parts[0], parts[1]);
      }
    } catch (_) {}
    return http.MediaType('video', 'mp4');
  }
}

// ── Custom exception ───────────────────────────────────────────────────────────
class ApiException implements Exception {
  final String message;
  final int    statusCode;
  ApiException({required this.message, required this.statusCode});

  @override
  String toString() => 'ApiException($statusCode): $message';
}
