import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../shared/theme/app_theme.dart';
import '../providers/player_provider.dart';
import '../models/player_model.dart';

class NewPlayerScreen extends StatefulWidget {
  const NewPlayerScreen({super.key});

  @override
  State<NewPlayerScreen> createState() => _NewPlayerScreenState();
}

class _NewPlayerScreenState extends State<NewPlayerScreen> {
  final _formKey     = GlobalKey<FormState>();
  final _nameCtrl    = TextEditingController();
  final _ageCtrl     = TextEditingController();
  final _heightCtrl  = TextEditingController();
  final _weightCtrl  = TextEditingController();
  final _villageCtrl = TextEditingController();
  final _districtCtrl= TextEditingController();

  String _gender      = 'M';
  String _foot        = 'right';
  String _experience  = 'none';

  @override
  void dispose() {
    _nameCtrl.dispose(); _ageCtrl.dispose();
    _heightCtrl.dispose(); _weightCtrl.dispose();
    _villageCtrl.dispose(); _districtCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    final player = Player(
      fullName:        _nameCtrl.text.trim(),
      age:             int.parse(_ageCtrl.text.trim()),
      gender:          _gender,
      dominantFoot:    _foot,
      heightCm:        double.tryParse(_heightCtrl.text),
      weightKg:        double.tryParse(_weightCtrl.text),
      village:         _villageCtrl.text.trim(),
      district:        _districtCtrl.text.trim(),
      state:           'Andhra Pradesh',
      experienceLevel: _experience,
    );

    final created = await context.read<PlayerProvider>().createPlayer(player);

    if (mounted) {
      if (created != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${player.fullName} registered successfully'),
            backgroundColor: AppColors.strong,
          ),
        );
        Navigator.pop(context, created);
      } else {
        final error = context.read<PlayerProvider>().error;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error), backgroundColor: AppColors.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Register Player')),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _SectionLabel('Personal Information'),
              const SizedBox(height: 12),

              // Full name
              _Field(
                controller: _nameCtrl,
                label: 'Full Name',
                hint: 'e.g. Suresh Kumar',
                validator: (v) => v!.trim().isEmpty ? 'Name is required' : null,
              ),
              const SizedBox(height: 14),

              // Age + Gender row
              Row(
                children: [
                  Expanded(
                    child: _Field(
                      controller: _ageCtrl,
                      label: 'Age',
                      hint: '14–35',
                      keyboard: TextInputType.number,
                      validator: (v) {
                        final age = int.tryParse(v ?? '');
                        if (age == null) return 'Enter a valid age';
                        if (age < 10 || age > 40) return '10–40 only';
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _DropdownField(
                      label: 'Gender',
                      value: _gender,
                      items: const [
                        DropdownMenuItem(value: 'M', child: Text('Male')),
                        DropdownMenuItem(value: 'F', child: Text('Female')),
                        DropdownMenuItem(value: 'O', child: Text('Other')),
                      ],
                      onChanged: (v) => setState(() => _gender = v!),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Dominant foot
              _DropdownField(
                label: 'Dominant Foot',
                value: _foot,
                items: const [
                  DropdownMenuItem(value: 'right', child: Text('Right')),
                  DropdownMenuItem(value: 'left',  child: Text('Left')),
                  DropdownMenuItem(value: 'both',  child: Text('Both')),
                ],
                onChanged: (v) => setState(() => _foot = v!),
              ),
              const SizedBox(height: 24),

              _SectionLabel('Physical Stats (Optional)'),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: _Field(
                      controller: _heightCtrl,
                      label: 'Height (cm)',
                      hint: 'e.g. 172',
                      keyboard: TextInputType.number,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _Field(
                      controller: _weightCtrl,
                      label: 'Weight (kg)',
                      hint: 'e.g. 65',
                      keyboard: TextInputType.number,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              _SectionLabel('Location'),
              const SizedBox(height: 12),

              _Field(
                controller: _villageCtrl,
                label: 'Village / Town',
                hint: 'e.g. Bhimavaram',
                validator: (v) => v!.trim().isEmpty ? 'Location is required' : null,
              ),
              const SizedBox(height: 14),

              _Field(
                controller: _districtCtrl,
                label: 'District',
                hint: 'e.g. West Godavari',
                validator: (v) => v!.trim().isEmpty ? 'District is required' : null,
              ),
              const SizedBox(height: 24),

              _SectionLabel('Background'),
              const SizedBox(height: 12),

              _DropdownField(
                label: 'Badminton Experience',
                value: _experience,
                items: const [
                  DropdownMenuItem(value: 'none',   child: Text('None')),
                  DropdownMenuItem(value: 'street', child: Text('Street play')),
                  DropdownMenuItem(value: 'school', child: Text('School team')),
                  DropdownMenuItem(value: 'club',   child: Text('Club level')),
                ],
                onChanged: (v) => setState(() => _experience = v!),
              ),
              const SizedBox(height: 32),

              // Save button
              Consumer<PlayerProvider>(
                builder: (_, prov, __) => ElevatedButton(
                  onPressed: prov.isLoading ? null : _save,
                  child: prov.isLoading
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white))
                      : const Text('Register Player'),
                ),
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(text.toUpperCase(),
      style: const TextStyle(
        color: AppColors.textMuted,
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 1.2,
      ),
    );
  }
}

class _Field extends StatelessWidget {
  final TextEditingController controller;
  final String  label;
  final String  hint;
  final TextInputType keyboard;
  final String? Function(String?)? validator;

  const _Field({
    required this.controller,
    required this.label,
    required this.hint,
    this.keyboard = TextInputType.text,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller:   controller,
      keyboardType: keyboard,
      style: const TextStyle(color: AppColors.textPrimary),
      decoration: InputDecoration(labelText: label, hintText: hint),
      validator: validator,
    );
  }
}

class _DropdownField<T> extends StatelessWidget {
  final String label;
  final T value;
  final List<DropdownMenuItem<T>> items;
  final void Function(T?) onChanged;

  const _DropdownField({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<T>(
      value:       value,
      items:       items,
      onChanged:   onChanged,
      dropdownColor: AppColors.backgroundCard,
      style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
      decoration: InputDecoration(labelText: label),
    );
  }
}
