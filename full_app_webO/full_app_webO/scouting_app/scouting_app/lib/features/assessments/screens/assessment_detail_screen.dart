import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../shared/theme/app_theme.dart';
import '../../../core/constants/app_constants.dart';
import '../providers/assessment_provider.dart';
import '../models/assessment_model.dart';
import '../../tests/screens/test_upload_screen.dart';
import '../../results/screens/results_screen.dart';

class AssessmentDetailScreen extends StatefulWidget {
  final int assessmentId;
  const AssessmentDetailScreen({super.key, required this.assessmentId});

  @override
  State<AssessmentDetailScreen> createState() => _AssessmentDetailScreenState();
}

class _AssessmentDetailScreenState extends State<AssessmentDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AssessmentProvider>().loadAssessment(widget.assessmentId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AssessmentProvider>(
      builder: (_, provider, __) {
        final assessment = provider.current;

        if (provider.isLoading && assessment == null) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator(color: AppColors.accent)),
          );
        }

        if (assessment == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Assessment')),
            body: const Center(child: Text('Assessment not found',
              style: TextStyle(color: AppColors.textMuted))),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: Text(assessment.playerName),
            actions: [
              if (assessment.allDone)
                TextButton(
                  onPressed: () => Navigator.push(context,
                    MaterialPageRoute(
                      builder: (_) => ResultsScreen(assessment: assessment),
                    ),
                  ),
                  child: const Text('View Results',
                    style: TextStyle(color: AppColors.accent)),
                ),
            ],
          ),
          body: RefreshIndicator(
            color: AppColors.accent,
            onRefresh: () => provider.loadAssessment(widget.assessmentId),
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Player info card ──────────────────────────────────────
                  _PlayerInfoCard(assessment: assessment),
                  const SizedBox(height: 20),

                  // ── Progress ──────────────────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Tests',
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text('${assessment.completedTests} / ${assessment.totalTests} complete',
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Progress bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: assessment.completedTests / assessment.totalTests,
                      minHeight: 6,
                      backgroundColor: AppColors.border,
                      valueColor: const AlwaysStoppedAnimation<Color>(AppColors.strong),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Test cards ────────────────────────────────────────────
                  ...AppConstants.testTypes.map((testDef) {
                    final testType = testDef['key']!;
                    final result   = assessment.getTest(testType);
                    return _TestCard(
                      testType:  testType,
                      label:     testDef['label']!,
                      emoji:     testDef['emoji']!,
                      result:    result,
                      onTap: () => Navigator.push(context,
                        MaterialPageRoute(
                          builder: (_) => TestUploadScreen(
                            assessmentId: assessment.id!,
                            testType:     testType,
                            testLabel:    testDef['label']!,
                            emoji:        testDef['emoji']!,
                          ),
                        ),
                      ).then((_) => provider.loadAssessment(widget.assessmentId)),
                    );
                  }),

                  const SizedBox(height: 20),

                  // ── Overall score (when all done) ─────────────────────────
                  if (assessment.allDone) ...[
                    _OverallScoreCard(assessment: assessment),
                    const SizedBox(height: 12),

                    // Recommendation buttons
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.close, color: AppColors.error),
                            label: const Text('Not Recommend',
                              style: TextStyle(color: AppColors.error)),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: AppColors.error),
                            ),
                            onPressed: () => provider.setRecommendation(assessment.id!, false),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.check),
                            label: const Text('Recommend'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.strong,
                            ),
                            onPressed: () => provider.setRecommendation(assessment.id!, true),
                          ),
                        ),
                      ],
                    ),
                  ],

                  const SizedBox(height: 80),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

// ── Player info card ──────────────────────────────────────────────────────────
class _PlayerInfoCard extends StatelessWidget {
  final Assessment assessment;
  const _PlayerInfoCard({required this.assessment});

  @override
  Widget build(BuildContext context) {
    final p = assessment.player;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: AppColors.primary,
              child: Text(
                assessment.playerName.substring(0, 1).toUpperCase(),
                style: const TextStyle(
                  color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(assessment.playerName,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (p != null) ...[
                    Text('${p.age}y  •  ${p.genderLabel}  •  ${p.dominantFoot} foot',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                    Text(p.locationStr,
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                  ],
                ],
              ),
            ),
            // Recommendation badge
            if (assessment.recommendation != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: (assessment.recommendation!
                      ? AppColors.strong : AppColors.error).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  assessment.recommendation! ? '✓ Recommended' : '✗ Not Recommended',
                  style: TextStyle(
                    color: assessment.recommendation! ? AppColors.strong : AppColors.error,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ── Test card ─────────────────────────────────────────────────────────────────
class _TestCard extends StatelessWidget {
  final String     testType;
  final String     label;
  final String     emoji;
  final TestResult? result;
  final VoidCallback onTap;

  const _TestCard({
    required this.testType,
    required this.label,
    required this.emoji,
    required this.result,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isCompleted  = result?.isCompleted  ?? false;
    final isProcessing = result?.isProcessing ?? false;
    final isFailed     = result?.isFailed     ?? false;
    final score        = result?.score;

    Color  statusColor;
    String statusLabel;
    IconData statusIcon;

    if (isCompleted) {
      statusColor = AppColors.strong;
      statusLabel = score != null ? score.toStringAsFixed(0) : 'Done';
      statusIcon  = Icons.check_circle;
    } else if (isProcessing) {
      statusColor = AppColors.threshold;
      statusLabel = 'Processing...';
      statusIcon  = Icons.hourglass_top;
    } else if (isFailed) {
      statusColor = AppColors.error;
      statusLabel = 'Failed';
      statusIcon  = Icons.error_outline;
    } else {
      statusColor = AppColors.textMuted;
      statusLabel = 'Pending';
      statusIcon  = Icons.radio_button_unchecked;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // Emoji icon
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: isCompleted
                      ? AppColors.strong.withOpacity(0.12)
                      : AppColors.backgroundInput,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Text(emoji, style: const TextStyle(fontSize: 20)),
                ),
              ),

              const SizedBox(width: 12),

              // Label
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (isCompleted && score != null) ...[
                      const SizedBox(height: 3),
                      Text(AppConstants.scoreBand(score),
                        style: TextStyle(color: AppTheme.scoreColor(score), fontSize: 12),
                      ),
                    ],
                    if (isFailed && result?.error != null) ...[
                      const SizedBox(height: 3),
                      Text(result!.error!, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: AppColors.error, fontSize: 11)),
                    ],
                  ],
                ),
              ),

              // Status
              Row(
                children: [
                  if (isProcessing)
                    const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2, color: AppColors.threshold),
                    )
                  else
                    Icon(statusIcon, color: statusColor, size: 20),

                  const SizedBox(width: 6),
                  if (isCompleted && score != null)
                    Text(statusLabel,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  const SizedBox(width: 4),
                  const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 16),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Overall score card ────────────────────────────────────────────────────────
class _OverallScoreCard extends StatelessWidget {
  final Assessment assessment;
  const _OverallScoreCard({required this.assessment});

  @override
  Widget build(BuildContext context) {
    final score = assessment.overallScore ?? 0;
    final color = AppTheme.scoreColor(score);
    final band  = AppConstants.scoreBand(score);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.primary, AppColors.primaryLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Overall Talent Score',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                const SizedBox(height: 6),
                Text(score.toStringAsFixed(1),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 42,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.25),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: color.withOpacity(0.5)),
                  ),
                  child: Text(band,
                    style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
          // Score arc
          SizedBox(
            width: 80, height: 80,
            child: Stack(
              children: [
                CircularProgressIndicator(
                  value: score / 100,
                  strokeWidth: 6,
                  backgroundColor: Colors.white24,
                  valueColor: AlwaysStoppedAnimation<Color>(color),
                ),
                Center(
                  child: Text('${score.toStringAsFixed(0)}%',
                    style: const TextStyle(
                      color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
