import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/network/api_service.dart';
import '../../../core/network/local_db.dart';
import '../../../core/constants/app_constants.dart';
import '../models/assessment_model.dart';

class AssessmentProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  final LocalDb    _db  = LocalDb();

  List<Assessment> _assessments  = [];
  Assessment?      _current;
  bool             _isLoading    = false;
  bool             _isUploading  = false;
  String           _error        = '';
  String           _uploadStatus = '';

  List<Assessment> get assessments   => _assessments;
  Assessment?      get current       => _current;
  bool             get isLoading     => _isLoading;
  bool             get isUploading   => _isUploading;
  String           get error         => _error;
  String           get uploadStatus  => _uploadStatus;

  // ── Load all assessments ────────────────────────────────────────────────────
  Future<void> loadAssessments() async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data   = await _api.get(AppConstants.assessmentsUrl);
      _assessments = (data['results'] as List)
          .map((a) => Assessment.fromJson(a as Map<String, dynamic>))
          .toList();

      // Cache for offline
      await _db.cacheAssessments(
        _assessments.map((a) => {
          'id'          : a.id,
          'player'      : a.playerId,
          'player_name' : a.playerName,
          'status'      : a.status,
          'overall_score': a.overallScore,
          'scout_notes' : a.scoutNotes,
          'recommendation': a.recommendation,
          'created_at'  : a.createdAt,
        }).toList(),
      );
    } catch (_) {
      // Offline fallback
      final cached = await _db.getCachedAssessments();
      _assessments = cached.map((row) => Assessment(
        id:          row['id'],
        playerId:    row['player_id'],
        status:      row['status'] ?? 'draft',
        scoutNotes:  row['scout_notes'] ?? '',
        overallScore: row['overall_score']?.toDouble(),
        createdAt:   row['created_at'],
      )).toList();
    }

    _isLoading = false;
    notifyListeners();
  }

  // ── Load single assessment ──────────────────────────────────────────────────
  Future<void> loadAssessment(int id) async {
    _isLoading = true;
    notifyListeners();
    try {
      final data = await _api.get(AppConstants.assessmentDetailUrl(id));
      _current   = Assessment.fromJson(data);
    } catch (e) {
      _error = 'Failed to load assessment';
    }
    _isLoading = false;
    notifyListeners();
  }

  // ── Create assessment ───────────────────────────────────────────────────────
  Future<Assessment?> createAssessment(int playerId, {String notes = ''}) async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data    = await _api.post(AppConstants.assessmentsUrl, {
        'player'     : playerId,
        'scout_notes': notes,
      });
      final created = Assessment.fromJson(data);
      _assessments.insert(0, created);
      _current   = created;
      _isLoading = false;
      notifyListeners();
      return created;
    } catch (e) {
      _error     = e is ApiException ? e.message : 'Failed to create assessment';
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  // ── Upload video — accepts XFile (works on web + mobile) ───────────────────
  Future<TestResult?> uploadTest({
    required int    assessmentId,
    required String testType,
    required XFile  xFile,          // ← XFile instead of dart:io File
  }) async {
    _isUploading  = true;
    _uploadStatus = 'Uploading video...';
    _error        = '';
    notifyListeners();

    try {
      _uploadStatus = 'Running AI analysis...';
      notifyListeners();

      final data = await _api.uploadVideo(
        url:   AppConstants.testUploadUrl(assessmentId, testType),
        xFile: xFile,
      );

      final result = TestResult.fromJson(data);

      if (_current?.id == assessmentId) {
        await loadAssessment(assessmentId);
      }

      await _db.cacheTestResult(data);

      _isUploading  = false;
      _uploadStatus = '';
      notifyListeners();
      return result;

    } catch (e) {
      // Queue for offline sync (file path only meaningful on mobile)
      await _db.addToSyncQueue(
        action:   'POST',
        endpoint: AppConstants.testUploadUrl(assessmentId, testType),
        payload:  {'test_type': testType},
        filePath: xFile.path,
      );

      _error        = e is ApiException ? e.message : 'Upload failed. Will retry when online.';
      _isUploading  = false;
      _uploadStatus = '';
      notifyListeners();
      return null;
    }
  }

  // ── Submit cone test (JSON only) ────────────────────────────────────────────
  Future<TestResult?> submitConeTest({
    required int assessmentId,
    required Map<String, dynamic> metrics,
  }) async {
    _isLoading = true;
    _error     = '';
    notifyListeners();

    try {
      final data   = await _api.post(
        AppConstants.testUploadUrl(assessmentId, 'cone'),
        {'metrics': metrics},
      );
      final result = TestResult.fromJson(data);
      if (_current?.id == assessmentId) await loadAssessment(assessmentId);
      _isLoading = false;
      notifyListeners();
      return result;
    } catch (e) {
      _error     = e is ApiException ? e.message : 'Failed to submit cone results';
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  // ── Get overall score ───────────────────────────────────────────────────────
  Future<Map<String, dynamic>?> getScore(int assessmentId) async {
    try {
      return await _api.get(AppConstants.assessmentScoreUrl(assessmentId));
    } catch (_) {
      return null;
    }
  }

  // ── Set recommendation ──────────────────────────────────────────────────────
  Future<void> setRecommendation(int assessmentId, bool recommend) async {
    try {
      await _api.patch(
        AppConstants.assessmentDetailUrl(assessmentId),
        {'recommendation': recommend},
      );
      if (_current?.id == assessmentId) await loadAssessment(assessmentId);
    } catch (e) {
      _error = 'Failed to update recommendation';
      notifyListeners();
    }
  }

  void clearCurrent() {
    _current = null;
    notifyListeners();
  }
}
