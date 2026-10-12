import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../shared/theme/app_theme.dart';
import '../../../core/constants/app_constants.dart';
import '../../auth/providers/auth_provider.dart';
import '../../assessments/providers/assessment_provider.dart';
import '../../assessments/models/assessment_model.dart';
import '../../auth/screens/login_screen.dart';
import '../../players/screens/player_list_screen.dart';
import 'assessment_detail_screen.dart';
import 'new_assessment_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AssessmentProvider>().loadAssessments();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Dashboard'),
            Text('Welcome, ${auth.fullName.isNotEmpty ? auth.fullName : auth.username}',
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => const PlayerListScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (mounted) {
                Navigator.pushReplacement(context,
                  MaterialPageRoute(builder: (_) => const LoginScreen()));
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () => context.read<AssessmentProvider>().loadAssessments(),
        child: Consumer<AssessmentProvider>(
          builder: (_, provider, __) {
            if (provider.isLoading && provider.assessments.isEmpty) {
              return const Center(child: CircularProgressIndicator(color: AppColors.accent));
            }
            return CustomScrollView(
              slivers: [
                // ── Stats row ────────────────────────────────────────────────
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    child: _StatsRow(assessments: provider.assessments),
                  ),
                ),

                // ── Recent heading ────────────────────────────────────────────
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Recent Assessments',
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text('${provider.assessments.length} total',
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),

                // ── Assessment list ───────────────────────────────────────────
                if (provider.assessments.isEmpty)
                  const SliverFillRemaining(child: _EmptyState())
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final a = provider.assessments[index];
                          return _AssessmentCard(
                            assessment: a,
                            onTap: () => Navigator.push(context,
                              MaterialPageRoute(
                                builder: (_) => AssessmentDetailScreen(assessmentId: a.id!),
                              ),
                            ).then((_) => provider.loadAssessments()),
                          );
                        },
                        childCount: provider.assessments.length,
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),

      // ── FAB ────────────────────────────────────────────────────────────────
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('New Assessment'),
        onPressed: () => Navigator.push(context,
          MaterialPageRoute(builder: (_) => const NewAssessmentScreen()),
        ).then((_) => context.read<AssessmentProvider>().loadAssessments()),
      ),
    );
  }
}

// ── Stats row ─────────────────────────────────────────────────────────────────
class _StatsRow extends StatelessWidget {
  final List<Assessment> assessments;
  const _StatsRow({required this.assessments});

  @override
  Widget build(BuildContext context) {
    final total       = assessments.length;
    final completed   = assessments.where((a) => a.status == 'completed').length;
    final recommended = assessments.where((a) => a.recommendation == true).length;
    final avgScore    = assessments
        .where((a) => a.overallScore != null)
        .map((a) => a.overallScore!)
        .fold(0.0, (a, b) => a + b);
    final avg = completed > 0 ? (avgScore / completed) : 0.0;

    return Row(
      children: [
        _StatCard(label: 'Total',       value: '$total',          color: AppColors.primaryLight),
        const SizedBox(width: 10),
        _StatCard(label: 'Completed',   value: '$completed',      color: AppColors.strong),
        const SizedBox(width: 10),
        _StatCard(label: 'Recommended', value: '$recommended',    color: AppColors.elite),
        const SizedBox(width: 10),
        _StatCard(label: 'Avg Score',   value: avg.toStringAsFixed(0), color: AppColors.threshold),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color  color;
  const _StatCard({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Text(value,
              style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(label,
              style: const TextStyle(color: AppColors.textMuted, fontSize: 10),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ── Assessment card ───────────────────────────────────────────────────────────
class _AssessmentCard extends StatelessWidget {
  final Assessment assessment;
  final VoidCallback onTap;
  const _AssessmentCard({required this.assessment, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final score     = assessment.overallScore;
    final scoreColor = score != null ? AppTheme.scoreColor(score) : AppColors.textMuted;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // Score circle
              Container(
                width: 52, height: 52,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: score != null
                      ? scoreColor.withOpacity(0.15)
                      : AppColors.backgroundInput,
                  border: Border.all(
                    color: score != null ? scoreColor : AppColors.border,
                    width: 1.5,
                  ),
                ),
                child: Center(
                  child: Text(
                    score != null ? score.toStringAsFixed(0) : '—',
                    style: TextStyle(
                      color: score != null ? scoreColor : AppColors.textMuted,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),

              const SizedBox(width: 14),

              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(assessment.playerName,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(assessment.player?.locationStr ?? '',
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                    ),
                    const SizedBox(height: 6),
                    // Test progress dots
                    Row(
                      children: AppConstants.testTypes.map((t) {
                        final result = assessment.getTest(t['key']!);
                        final done   = result?.isCompleted ?? false;
                        return Container(
                          width: 8, height: 8,
                          margin: const EdgeInsets.only(right: 4),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: done ? AppColors.strong : AppColors.border,
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),

              // Status + chevron
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _StatusChip(status: assessment.status),
                  const SizedBox(height: 8),
                  const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 18),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color color;
    String label;
    switch (status) {
      case 'completed': color = AppColors.strong;     label = 'Done';        break;
      case 'in_progress': color = AppColors.threshold; label = 'In Progress'; break;
      case 'synced':    color = AppColors.info;       label = 'Synced';      break;
      default:          color = AppColors.textMuted;  label = 'Draft';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(label,
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.sports_tennis,
            size: 64, color: AppColors.textMuted.withOpacity(0.4)),
          const SizedBox(height: 16),
          const Text('No assessments yet',
            style: TextStyle(color: AppColors.textMuted, fontSize: 16)),
          const SizedBox(height: 8),
          const Text('Tap + New Assessment to get started',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
        ],
      ),
    );
  }
}
