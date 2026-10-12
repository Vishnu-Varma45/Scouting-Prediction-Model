import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../shared/theme/app_theme.dart';
import '../../players/providers/player_provider.dart';
import '../../players/models/player_model.dart';
import '../../assessments/providers/assessment_provider.dart';
import 'assessment_detail_screen.dart';
import '../../players/screens/new_player_screen.dart';

class NewAssessmentScreen extends StatefulWidget {
  const NewAssessmentScreen({super.key});

  @override
  State<NewAssessmentScreen> createState() => _NewAssessmentScreenState();
}

class _NewAssessmentScreenState extends State<NewAssessmentScreen> {
  Player? _selectedPlayer;
  final _notesCtrl = TextEditingController();
  String  _search  = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<PlayerProvider>().loadPlayers();
    });
  }

  @override
  void dispose() {
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _startAssessment() async {
    if (_selectedPlayer == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select a player first'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }

    final assessment = await context.read<AssessmentProvider>().createAssessment(
      _selectedPlayer!.id!,
      notes: _notesCtrl.text.trim(),
    );

    if (assessment != null && mounted) {
      Navigator.pushReplacement(context,
        MaterialPageRoute(
          builder: (_) => AssessmentDetailScreen(assessmentId: assessment.id!),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Assessment')),
      body: Column(
        children: [
          // ── Search bar ──────────────────────────────────────────────────────
          Container(
            color: AppColors.backgroundCard,
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextFormField(
                  onChanged: (v) => setState(() => _search = v),
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    hintText: 'Search player by name or village...',
                    prefixIcon: Icon(Icons.search, color: AppColors.textMuted),
                  ),
                ),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const NewPlayerScreen()),
                  ).then((_) => context.read<PlayerProvider>().loadPlayers()),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.person_add, size: 16),
                      SizedBox(width: 8),
                      Text('Register New Player'),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── Player list ─────────────────────────────────────────────────────
          Expanded(
            child: Consumer<PlayerProvider>(
              builder: (_, provider, __) {
                print("Consumer provider players: ${provider.players.length}");
                print("Provider hash: ${provider.hashCode}");
                if (provider.isLoading) {
                  return const Center(child: CircularProgressIndicator(color: AppColors.accent));
                }
                final players = provider.search(_search);
                print("Players received by UI: ${players.length}");
                if (players.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.person_off, size: 48, color: AppColors.textMuted),
                        const SizedBox(height: 12),
                        Text(_search.isEmpty ? 'No players registered yet' : 'No players found',
                          style: const TextStyle(color: AppColors.textMuted)),
                      ],
                    ),
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: players.length,
                  itemBuilder: (_, i) {
                    final p       = players[i];
                    final selected = _selectedPlayer?.id == p.id;
                    return Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                        side: BorderSide(
                          color: selected ? AppColors.primaryLight : AppColors.border,
                          width: selected ? 1.5 : 0.5,
                        ),
                      ),
                      color: selected
                          ? AppColors.primaryLight.withOpacity(0.12)
                          : AppColors.backgroundCard,
                      child: ListTile(
                        onTap: () => setState(() => _selectedPlayer = p),
                        leading: CircleAvatar(
                          backgroundColor: selected
                              ? AppColors.primaryLight
                              : AppColors.backgroundInput,
                          child: Text(
                            p.fullName.substring(0, 1).toUpperCase(),
                            style: TextStyle(
                              color: selected ? Colors.white : AppColors.textSecondary,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        title: Text(p.fullName,
                          style: TextStyle(
                            color: selected ? AppColors.textPrimary : AppColors.textPrimary,
                            fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                        subtitle: Text(
                          '${p.age}y  •  ${p.locationStr}  •  ${p.experienceLevel}',
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                        trailing: selected
                            ? const Icon(Icons.check_circle, color: AppColors.primaryLight)
                            : null,
                      ),
                    );
                  },
                );
              },
            ),
          ),

          // ── Notes + Start button ────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppColors.backgroundCard,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: Column(
              children: [
                if (_selectedPlayer != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.primary.withOpacity(0.4)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.person, color: AppColors.primaryLight, size: 18),
                        const SizedBox(width: 8),
                        Text(_selectedPlayer!.fullName,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Spacer(),
                        Text(_selectedPlayer!.locationStr,
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: _notesCtrl,
                    maxLines: 2,
                    style: const TextStyle(color: AppColors.textPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Scout notes (optional)...',
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Consumer<AssessmentProvider>(
                  builder: (_, prov, __) => ElevatedButton(
                    onPressed: prov.isLoading ? null : _startAssessment,
                    child: prov.isLoading
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Start Assessment →'),
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

// Minimal outlined button helper
extension on OutlinedButton {
  static Widget minimal({required VoidCallback? onPressed, required Widget child}) {
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(double.infinity, 42),
        side: const BorderSide(color: AppColors.border),
        foregroundColor: AppColors.textSecondary,
      ),
      child: child,
    );
  }
}
