import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/user_provider.dart';
import 'auth_screen.dart';

class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});
  @override
  ConsumerState<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 88, 88, 88);

  final _currentController = TextEditingController();
  final _newController = TextEditingController();
  final _confirmController = TextEditingController();

  bool _isLoading = false;
  String? _serverError;

  bool _obscureCurrent = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  bool get _isLongEnough => _newController.text.length >= 8;
  bool get _passwordsMatch =>
      _confirmController.text.isNotEmpty && _newController.text == _confirmController.text;
  bool get _isFormValid =>
      _currentController.text.isNotEmpty && _isLongEnough && _passwordsMatch;

  @override
  void dispose() {
    _currentController.dispose();
    _newController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  BoxDecoration _doodleDecoration({Color? color, double borderRadius = 12.5}) {
    return BoxDecoration(
      color: color ?? cardColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: outlineColor, width: 1.0),
      boxShadow: [BoxShadow(color: outlineColor, offset: const Offset(2, 2), blurRadius: 0)],
    );
  }

  InputDecoration _fieldDecoration(
    String hint, {
    required bool obscure,
    required VoidCallback onToggle,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: textMuted, fontSize: 13),
      filled: true,
      fillColor: cardColor,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      suffixIcon: IconButton(
        icon: Icon(
          obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
          color: textMuted,
          size: 20,
        ),
        onPressed: onToggle,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: outlineColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: outlineColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: accentColor, width: 1.5),
      ),
      disabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: outlineColor.withValues(alpha: 0.4)),
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _isLoading = true;
      _serverError = null;
    });

    try {
      await ref.read(userProvider.notifier).changePassword(
            currentPassword: _currentController.text,
            newPassword: _newController.text,
          );

      TextInput.finishAutofillContext(); // lets the OS offer to save the new password

      if (!mounted) return;
      // Password changed server-side → current session token should no
      // longer be trusted client-side either, so force a fresh login.
      await ref.read(userProvider.notifier).clearSession();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password changed! Please log in again.')),
      );
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (context) => const AuthScreen()),
        (route) => false,
      );
    } catch (e) {
      if (mounted) {
        setState(() => _serverError = e.toString().replaceAll('NetworkException: ', ''));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final newTouched = _newController.text.isNotEmpty;
    final confirmTouched = _confirmController.text.isNotEmpty;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: IconThemeData(color: textMain),
        title: Text('Change Password', style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 20)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: _doodleDecoration(),
            child: AutofillGroup(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_serverError != null) ...[
                    Text(_serverError!, style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 12),
                  ],

                  Text('Current Password', style: TextStyle(color: textMain, fontSize: 13, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _currentController,
                    obscureText: _obscureCurrent,
                    enabled: !_isLoading,
                    autofillHints: const [AutofillHints.password],
                    onChanged: (_) => setState(() {}),
                    decoration: _fieldDecoration(
                      'Enter current password',
                      obscure: _obscureCurrent,
                      onToggle: () => setState(() => _obscureCurrent = !_obscureCurrent),
                    ),
                  ),
                  const SizedBox(height: 18),

                  Text('New Password', style: TextStyle(color: textMain, fontSize: 13, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _newController,
                    obscureText: _obscureNew,
                    enabled: !_isLoading,
                    autofillHints: const [AutofillHints.newPassword],
                    onChanged: (_) => setState(() {}),
                    decoration: _fieldDecoration(
                      'At least 8 characters',
                      obscure: _obscureNew,
                      onToggle: () => setState(() => _obscureNew = !_obscureNew),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    newTouched && !_isLongEnough ? 'Password should be at least 8 characters' : 'At least 8 characters',
                    style: TextStyle(
                      fontSize: 12,
                      color: newTouched && !_isLongEnough ? Colors.redAccent : textMuted,
                      fontWeight: newTouched && !_isLongEnough ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                  const SizedBox(height: 18),

                  Text('Re-enter New Password', style: TextStyle(color: textMain, fontSize: 13, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _confirmController,
                    obscureText: _obscureConfirm,
                    enabled: !_isLoading,
                    autofillHints: const [AutofillHints.newPassword],
                    onChanged: (_) => setState(() {}),
                    decoration: _fieldDecoration(
                      'Confirm new password',
                      obscure: _obscureConfirm,
                      onToggle: () => setState(() => _obscureConfirm = !_obscureConfirm),
                    ),
                  ),
                  if (confirmTouched && !_passwordsMatch) ...[
                    const SizedBox(height: 6),
                    const Text('Passwords do not match',
                        style: TextStyle(fontSize: 12, color: Colors.redAccent, fontWeight: FontWeight.w600)),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          GestureDetector(
            onTap: (_isFormValid && !_isLoading) ? _submit : null,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: _doodleDecoration(
                color: _isFormValid ? accentColor : Colors.grey.shade300,
                borderRadius: 16,
              ),
              alignment: Alignment.center,
              child: _isLoading
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(
                      'Change Password',
                      style: TextStyle(
                        color: _isFormValid ? textMain : textMuted,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}