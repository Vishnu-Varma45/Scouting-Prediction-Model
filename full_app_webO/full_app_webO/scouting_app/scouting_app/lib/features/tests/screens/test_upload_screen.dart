// No dart:io import — fully cross-platform (web + mobile)
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import '../../../shared/theme/app_theme.dart';
import '../../assessments/providers/assessment_provider.dart';

class TestUploadScreen extends StatefulWidget {
  final int    assessmentId;
  final String testType;
  final String testLabel;
  final String emoji;

  const TestUploadScreen({
    super.key,
    required this.assessmentId,
    required this.testType,
    required this.testLabel,
    required this.emoji,
  });

  @override
  State<TestUploadScreen> createState() => _TestUploadScreenState();
}

class _TestUploadScreenState extends State<TestUploadScreen> {
  // XFile works on web + mobile — no dart:io File needed
  XFile?  _selectedVideo;
  int?    _fileSizeBytes;
  bool    _isUploading  = false;
  String  _uploadStatus = '';

  // Cone test controllers
  final Map<String, TextEditingController> _coneControllers = {
    'accuracy_percent'      : TextEditingController(),
    'average_reaction_time' : TextEditingController(),
    'fastest_reaction'      : TextEditingController(),
    'average_movement_time' : TextEditingController(),
    'cognitive_score'       : TextEditingController(),
    'fatigue_index'         : TextEditingController(),
    'misses'                : TextEditingController(),
    'decision_errors'       : TextEditingController(),
  };

  @override
  void dispose() {
    for (final c in _coneControllers.values) c.dispose();
    super.dispose();
  }

  // ── Pick video from gallery ──────────────────────────────────────────────
  Future<void> _pickVideo() async {
    final picker = ImagePicker();
    final picked = await picker.pickVideo(
      source:      ImageSource.gallery,
      maxDuration: const Duration(minutes: 5),
    );
    if (picked != null) {
      final size = await _getFileSize(picked);
      setState(() {
        _selectedVideo  = picked;
        _fileSizeBytes  = size;
      });
    }
  }

  // ── Record video with camera (mobile only) ───────────────────────────────
  Future<void> _recordVideo() async {
    if (kIsWeb) {
      // Web browsers don't support camera recording via image_picker
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Camera recording is not supported on web. Please upload a video file.'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }
    final picker = ImagePicker();
    final picked = await picker.pickVideo(
      source:      ImageSource.camera,
      maxDuration: const Duration(minutes: 5),
    );
    if (picked != null) {
      final size = await _getFileSize(picked);
      setState(() {
        _selectedVideo = picked;
        _fileSizeBytes = size;
      });
    }
  }

  // ── Get file size cross-platform ─────────────────────────────────────────
  // On web: XFile.length() reads the blob size
  // On mobile: same API, reads from filesystem
  Future<int> _getFileSize(XFile file) async {
    try {
      return await file.length();
    } catch (_) {
      return 0;
    }
  }

  // ── Get display filename cross-platform ──────────────────────────────────
  String _getFileName(XFile file) {
    if (file.name.isNotEmpty) return file.name;
    // On mobile, name may be empty — extract from path
    return file.path.split('/').last;
  }

  // ── Upload video ─────────────────────────────────────────────────────────
  Future<void> _uploadVideo() async {
    if (_selectedVideo == null) return;

    setState(() {
      _isUploading  = true;
      _uploadStatus = 'Uploading video...';
    });

    final provider = context.read<AssessmentProvider>();

    // uploadTest now accepts XFile — works on web + mobile
    final result = await provider.uploadTest(
      assessmentId: widget.assessmentId,
      testType:     widget.testType,
      xFile:        _selectedVideo!,
    );

    setState(() {
      _isUploading  = false;
      _uploadStatus = '';
    });

    if (!mounted) return;

    if (result != null && result.isCompleted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${widget.testLabel} analysis complete! '
            'Score: ${result.score?.toStringAsFixed(0) ?? "—"}',
          ),
          backgroundColor: AppColors.strong,
        ),
      );
      Navigator.pop(context);
    } else if (provider.error.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:         Text(provider.error),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  // ── Submit cone results ───────────────────────────────────────────────────
  Future<void> _submitConeResults() async {
    final metrics = <String, dynamic>{};
    for (final entry in _coneControllers.entries) {
      final val = double.tryParse(entry.value.text);
      if (val == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:         Text('Please fill in "${entry.key}" correctly'),
            backgroundColor: AppColors.error,
          ),
        );
        return;
      }
      metrics[entry.key] = val;
    }

    final provider = context.read<AssessmentProvider>();
    final result   = await provider.submitConeTest(
      assessmentId: widget.assessmentId,
      metrics:      metrics,
    );

    if (mounted && result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Cone test saved! Score: ${result.score?.toStringAsFixed(0) ?? "—"}',
          ),
          backgroundColor: AppColors.strong,
        ),
      );
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.emoji}  ${widget.testLabel}'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: widget.testType == 'cone'
            ? _buildConeForm()
            : _buildVideoUpload(),
      ),
    );
  }

  // ── Video upload UI ───────────────────────────────────────────────────────
  Widget _buildVideoUpload() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Setup instructions
        _InstructionCard(testType: widget.testType),
        const SizedBox(height: 20),

        // Drop zone / selection area
        GestureDetector(
          onTap: _pickVideo,
          child: Container(
            width:  double.infinity,
            height: 200,
            decoration: BoxDecoration(
              color: AppColors.backgroundInput,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _selectedVideo != null
                    ? AppColors.strong
                    : AppColors.border,
                width: _selectedVideo != null ? 1.5 : 0.5,
              ),
            ),
            child: _selectedVideo != null
                ? _SelectedVideoPreview(
                    fileName:      _getFileName(_selectedVideo!),
                    fileSizeBytes: _fileSizeBytes,
                    onRemove:      () => setState(() {
                      _selectedVideo = null;
                      _fileSizeBytes = null;
                    }),
                  )
                : _EmptyDropZone(isWeb: kIsWeb),
          ),
        ),

        const SizedBox(height: 12),

        // Record button — hidden on web (not supported)
        if (!kIsWeb)
          OutlinedButton.icon(
            icon:  const Icon(Icons.videocam_outlined,
                color: AppColors.textSecondary),
            label: const Text('Record video now',
                style: TextStyle(color: AppColors.textSecondary)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
              side: const BorderSide(color: AppColors.border),
            ),
            onPressed: _recordVideo,
          ),

        if (kIsWeb) ...[
          // Web hint
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.info.withOpacity(0.10),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.info.withOpacity(0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline, color: AppColors.info, size: 16),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Tap the box above to select a video file from your system.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: 20),

        // Upload progress indicator
        if (_isUploading) ...[
          _UploadProgressBar(status: _uploadStatus),
          const SizedBox(height: 16),
        ],

        // Upload & Analyse button
        ElevatedButton.icon(
          icon:  const Icon(Icons.send),
          label: const Text('Upload & Analyse'),
          onPressed: (_selectedVideo == null || _isUploading)
              ? null
              : _uploadVideo,
          style: ElevatedButton.styleFrom(
            backgroundColor: _selectedVideo != null
                ? AppColors.primary
                : AppColors.backgroundInput,
          ),
        ),
      ],
    );
  }

  // ── Cone test form ────────────────────────────────────────────────────────
  Widget _buildConeForm() {
    final fields = [
      {'key': 'accuracy_percent',       'label': 'Accuracy (%)',            'hint': 'e.g. 86.7'},
      {'key': 'average_reaction_time',  'label': 'Avg Reaction Time (s)',   'hint': 'e.g. 0.42'},
      {'key': 'fastest_reaction',       'label': 'Fastest Reaction (s)',    'hint': 'e.g. 0.28'},
      {'key': 'average_movement_time',  'label': 'Avg Movement Time (s)',   'hint': 'e.g. 1.1'},
      {'key': 'cognitive_score',        'label': 'Cognitive Score (0–100)', 'hint': 'e.g. 74'},
      {'key': 'fatigue_index',          'label': 'Fatigue Index (0–1)',     'hint': 'e.g. 0.12'},
      {'key': 'misses',                 'label': 'Misses',                  'hint': 'e.g. 2'},
      {'key': 'decision_errors',        'label': 'Decision Errors',         'hint': 'e.g. 1'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Enter Cone Test Results',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        const Text(
          'Run the cone test script on your computer, then enter the output values here.',
          style: TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
        const SizedBox(height: 20),
        ...fields.map((f) => Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: TextFormField(
            controller:   _coneControllers[f['key']],
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: InputDecoration(
              labelText: f['label'],
              hintText:  f['hint'],
            ),
          ),
        )),
        const SizedBox(height: 10),
        Consumer<AssessmentProvider>(
          builder: (_, prov, __) => ElevatedButton(
            onPressed: prov.isLoading ? null : _submitConeResults,
            child: prov.isLoading
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Submit Cone Results'),
          ),
        ),
      ],
    );
  }
}

// ── Selected video preview widget ─────────────────────────────────────────────
class _SelectedVideoPreview extends StatelessWidget {
  final String   fileName;
  final int?     fileSizeBytes;
  final VoidCallback onRemove;

  const _SelectedVideoPreview({
    required this.fileName,
    required this.fileSizeBytes,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    final mb = fileSizeBytes != null
        ? (fileSizeBytes! / (1024 * 1024)).toStringAsFixed(1)
        : null;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.videocam, color: AppColors.strong, size: 48),
        const SizedBox(height: 10),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            fileName,
            style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
            textAlign: TextAlign.center,
            maxLines:  2,
            overflow:  TextOverflow.ellipsis,
          ),
        ),
        if (mb != null) ...[
          const SizedBox(height: 6),
          Text('$mb MB',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
        ],
        const SizedBox(height: 8),
        TextButton(
          onPressed: onRemove,
          child: const Text('Remove', style: TextStyle(color: AppColors.error)),
        ),
      ],
    );
  }
}

// ── Empty drop zone widget ─────────────────────────────────────────────────────
class _EmptyDropZone extends StatelessWidget {
  final bool isWeb;
  const _EmptyDropZone({required this.isWeb});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.upload_file, color: AppColors.textMuted, size: 48),
        const SizedBox(height: 12),
        Text(
          isWeb
              ? 'Click to select a video file'
              : 'Tap to select video from gallery',
          style: const TextStyle(color: AppColors.textMuted, fontSize: 14),
        ),
        const SizedBox(height: 4),
        const Text('MP4 or MOV  •  max 500 MB',
          style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
      ],
    );
  }
}

// ── Upload progress bar ────────────────────────────────────────────────────────
class _UploadProgressBar extends StatelessWidget {
  final String status;
  const _UploadProgressBar({required this.status});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.primary.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const SizedBox(
            width: 20, height: 20,
            child: CircularProgressIndicator(
                strokeWidth: 2, color: AppColors.accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(status,
              style: const TextStyle(color: AppColors.textSecondary)),
          ),
        ],
      ),
    );
  }
}

// ── Test instruction card ──────────────────────────────────────────────────────
class _InstructionCard extends StatelessWidget {
  final String testType;
  const _InstructionCard({required this.testType});

  static const Map<String, Map<String, String>> _instructions = {
    'sprint': {
      'setup':  'Mark 0m and 10m lines on a flat surface.',
      'camera': 'Place camera side-on at the 5m mark, at hip height.',
      'action': 'Player sprints from 0m to 10m on your signal.',
    },
    'jump': {
      'setup':  'Player stands on a flat, clear surface.',
      'camera': 'Place camera front-on or side-on at 2m distance, full body visible.',
      'action': 'Player performs 3 maximum vertical jumps with rest between.',
    },
    'shuttle': {
      'setup':  'Mark 2 lines 9.14m apart (standard shuttle distance).',
      'camera': 'Place camera side-on at the midpoint, full run visible.',
      'action': 'Player runs shuttles back and forth for the full duration.',
    },
    'footwork': {
      'setup':  'Set up a badminton court. Camera at front-right corner, 1.5–2m high.',
      'camera': '45° angle toward player. Full court must be visible.',
      'action': 'Player performs shadow footwork touching all 6 corners.',
    },
  };

  @override
  Widget build(BuildContext context) {
    final info = _instructions[testType];
    if (info == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.primary.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Setup Instructions',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          _InstructionRow(icon: Icons.straighten,  text: info['setup']!),
          const SizedBox(height: 6),
          _InstructionRow(icon: Icons.videocam,    text: info['camera']!),
          const SizedBox(height: 6),
          _InstructionRow(icon: Icons.play_circle, text: info['action']!),
        ],
      ),
    );
  }
}

class _InstructionRow extends StatelessWidget {
  final IconData icon;
  final String   text;
  const _InstructionRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: AppColors.textMuted, size: 16),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        ),
      ],
    );
  }
}
