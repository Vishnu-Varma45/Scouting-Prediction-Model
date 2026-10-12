import 'package:flutter/material.dart';
import '../../../shared/theme/app_theme.dart';
import '../../../core/constants/app_constants.dart';
import '../../assessments/models/assessment_model.dart';

class ResultsScreen extends StatelessWidget {
  final Assessment assessment;
  const ResultsScreen({super.key, required this.assessment});

  @override
  Widget build(BuildContext context) {
    final score = assessment.overallScore ?? 0;
    final color = AppTheme.scoreColor(score);
    final band  = AppConstants.scoreBand(score);

    return Scaffold(
      appBar: AppBar(
        title: Text('Results — ${assessment.playerName}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () {/* share PDF future scope */},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Overall score hero ──────────────────────────────────────────
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppColors.primary, AppColors.primaryLight],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  const Text('OVERALL TALENT SCORE',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(score.toStringAsFixed(1),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 64,
                      fontWeight: FontWeight.bold,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: color.withOpacity(0.6)),
                    ),
                    child: Text(band,
                      style: TextStyle(
                        color: color,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Score bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: score / 100,
                      minHeight: 10,
                      backgroundColor: Colors.white12,
                      valueColor: AlwaysStoppedAnimation<Color>(color),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // ── Recommendation banner ───────────────────────────────────────
            if (assessment.recommendation != null)
              _RecommendationBanner(recommended: assessment.recommendation!),

            const SizedBox(height: 20),

            // ── Per-test breakdown heading ──────────────────────────────────
            const Text('Test Breakdown',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),

            // ── Per-test result cards ───────────────────────────────────────
            ...AppConstants.testTypes.map((testDef) {
              final result = assessment.getTest(testDef['key']!);
              if (result == null || !result.isCompleted) return const SizedBox.shrink();
              return _TestResultCard(
                result:    result,
                testLabel: testDef['label']!,
                emoji:     testDef['emoji']!,
              );
            }),

            const SizedBox(height: 20),

            // ── Scout notes ─────────────────────────────────────────────────
            if (assessment.scoutNotes.isNotEmpty) ...[
              const Text('Scout Notes',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.backgroundCard,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.border),
                ),
                child: Text(assessment.scoutNotes,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ),
            ],

            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }
}

// ── Recommendation banner ─────────────────────────────────────────────────────
class _RecommendationBanner extends StatelessWidget {
  final bool recommended;
  const _RecommendationBanner({required this.recommended});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: (recommended ? AppColors.strong : AppColors.error).withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (recommended ? AppColors.strong : AppColors.error).withOpacity(0.4),
        ),
      ),
      child: Row(
        children: [
          Icon(
            recommended ? Icons.check_circle : Icons.cancel,
            color: recommended ? AppColors.strong : AppColors.error,
            size: 28,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  recommended
                      ? 'Recommended for Academy Trial'
                      : 'Not Recommended at This Time',
                  style: TextStyle(
                    color: recommended ? AppColors.strong : AppColors.error,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  recommended
                      ? 'Player meets the threshold for a real-life trial.'
                      : 'Player did not meet the minimum threshold.',
                  style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Per-test result card ──────────────────────────────────────────────────────
class _TestResultCard extends StatefulWidget {
  final TestResult result;
  final String     testLabel;
  final String     emoji;
  const _TestResultCard({
    required this.result,
    required this.testLabel,
    required this.emoji,
  });

  @override
  State<_TestResultCard> createState() => _TestResultCardState();
}

class _TestResultCardState extends State<_TestResultCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final score = widget.result.score ?? 0;
    final color = AppTheme.scoreColor(score);
    final band  = AppConstants.scoreBand(score);

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        children: [
          // Header row
          InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  // Emoji
                  Container(
                    width: 44, height: 44,
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Center(
                      child: Text(widget.emoji,
                        style: const TextStyle(fontSize: 22)),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Label + band
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(widget.testLabel,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(band,
                          style: TextStyle(color: color, fontSize: 12)),
                      ],
                    ),
                  ),

                  // Score pill
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(score.toStringAsFixed(0),
                      style: TextStyle(
                        color: color,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: AppColors.textMuted,
                  ),
                ],
              ),
            ),
          ),

          // Score bar
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: score / 100,
                minHeight: 4,
                backgroundColor: AppColors.border,
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ),
          ),

          // Expanded metrics
          if (_expanded && widget.result.metrics != null) ...[
            const Divider(height: 1, color: AppColors.border),
            Padding(
              padding: const EdgeInsets.all(14),
              child: _MetricsGrid(
                testType: widget.result.testType,
                metrics:  widget.result.metrics!,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Metrics grid — renders the right metrics per test type ────────────────────
class _MetricsGrid extends StatelessWidget {
  final String                 testType;
  final Map<String, dynamic>   metrics;
  const _MetricsGrid({required this.testType, required this.metrics});

  List<Map<String, String>> _getDisplayMetrics() {
    switch (testType) {
      case 'sprint':
        return [
          {'label': 'Avg Speed',       'value': '${_f(metrics["average_speed_ms"])} m/s'},
          {'label': 'Step Count',      'value': '${metrics["step_count"] ?? "—"}'},
          {'label': 'Step Frequency',  'value': '${_f(metrics["step_frequency"])} /s'},
          {'label': 'Trunk Angle',     'value': '${_f(metrics["mean_trunk_angle"])}°'},
          {'label': 'Knee Asymmetry',  'value': '${_f(metrics["knee_asymmetry_deg"])}°'},
          {'label': 'Stride Grade',    'value': '${metrics["stride_grade"] ?? "—"}'},
        ];

      case 'jump':
        return [
          {'label': 'Best Height',     'value': '${_f(metrics["best_jump_height_cm"])} cm'},
          {'label': 'Avg Height',      'value': '${_f(metrics["avg_jump_height_cm"])} cm'},
          {'label': 'Flight Time',     'value': '${_f(metrics["best_flight_time_s"])} s'},
          {'label': 'Knee Flexion',    'value': '${_f(metrics["knee_flexion_deg"])}°'},
          {'label': 'Stability',       'value': '${_f(metrics["landing_stability"])}/100'},
          {'label': 'Recovery',        'value': '${_f(metrics["avg_recovery_time_s"])} s'},
          {'label': 'Symmetry',        'value': '${_f(metrics["avg_symmetry_pct"])}%'},
          {'label': 'Jumps',           'value': '${metrics["jumps_detected"] ?? "—"}'},
        ];

      case 'shuttle':
        return [
          {'label': 'Total Time',      'value': '${_f(metrics["total_time_s"])} s'},
          {'label': 'Shuttle Legs',    'value': '${metrics["total_shuttle_legs"] ?? "—"}'},
          {'label': 'Peak Speed',      'value': '${_f(metrics["peak_speed_ms"])} m/s'},
          {'label': 'Avg Speed',       'value': '${_f(metrics["avg_speed_ms"])} m/s'},
          {'label': 'Peak Accel',      'value': '${_f(metrics["peak_accel_ms2"])} m/s²'},
          {'label': 'Avg Decel',       'value': '${_f(metrics["avg_decel_ms2"])} m/s²'},
        ];

      case 'cone':
        return [
          {'label': 'Accuracy',        'value': '${_f(metrics["accuracy_percent"])}%'},
          {'label': 'Avg Reaction',    'value': '${_f(metrics["average_reaction_time"])} s'},
          {'label': 'Fastest',         'value': '${_f(metrics["fastest_reaction"])} s'},
          {'label': 'Cognitive Score', 'value': '${_f(metrics["cognitive_score"])}/100'},
          {'label': 'Fatigue Index',   'value': '${_f(metrics["fatigue_index"])}'},
          {'label': 'Errors',          'value': '${metrics["decision_errors"] ?? "—"}'},
        ];

      case 'footwork':
        return [
          {'label': 'Completion',      'value': '${_f(metrics["completion_time_s"])} s'},
          {'label': 'Split Steps',     'value': '${metrics["split_steps"] ?? "—"}'},
          {'label': 'Min Lunge',       'value': '${_f(metrics["min_lunge_angle_deg"])}°'},
          {'label': 'Avg Lunge',       'value': '${_f(metrics["avg_lunge_angle_deg"])}°'},
          {'label': 'L/R Symmetry',    'value': '${_f(metrics["left_right_symmetry"])}%'},
        ];

      default:
        return metrics.entries.take(6).map((e) => {
          'label': e.key,
          'value': '${e.value}',
        }).toList();
    }
  }

  String _f(dynamic v) {
    if (v == null) return '—';
    if (v is double) return v.toStringAsFixed(1);
    return v.toString();
  }

  @override
  Widget build(BuildContext context) {
    final items = _getDisplayMetrics();
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount:    3,
        childAspectRatio:  1.5,
        crossAxisSpacing:  8,
        mainAxisSpacing:   8,
      ),
      itemCount: items.length,
      itemBuilder: (_, i) {
        final item = items[i];
        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.backgroundInput,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(item['value']!,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(item['label']!,
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 10,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
              ),
            ],
          ),
        );
      },
    );
  }
}
