import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/user_provider.dart';

class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() =>
      _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  static const Color _bgColor = Color(0xFFFEFDF7);
  static const Color _cardColor = Colors.white;
  static const Color _accentColor = Color.fromARGB(255, 187, 182, 242);
  static const Color _textMain = Color.fromARGB(255, 48, 48, 48);
  static const Color _textMuted = Color(0xFF757575);
  static const Color _outlineColor = Color.fromARGB(255, 88, 88, 88);

  final _formKey = GlobalKey<FormState>();

  final _currentController = TextEditingController();
  final _newController = TextEditingController();
  final _confirmController = TextEditingController();

  bool _isLoading = false;
  String? _serverError;

  bool _obscureCurrent = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _currentController.clear();
    _newController.clear();
    _confirmController.clear();

    _currentController.dispose();
    _newController.dispose();
    _confirmController.dispose();

    super.dispose();
  }

  BoxDecoration _doodleDecoration({
    Color? color,
    double borderRadius = 12.5,
  }) {
    return BoxDecoration(
      color: color ?? _cardColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: _outlineColor,
        width: 1,
      ),
      boxShadow: const [
        BoxShadow(
          color: _outlineColor,
          offset: Offset(2, 2),
          blurRadius: 0,
        ),
      ],
    );
  }

  InputDecoration _fieldDecoration({
    required String hint,
    required bool obscure,
    required VoidCallback onToggle,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(
        color: _textMuted,
        fontSize: 13,
      ),
      filled: true,
      fillColor: _cardColor,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: 14,
      ),
      suffixIcon: IconButton(
        tooltip: obscure ? 'Show password' : 'Hide password',
        icon: Icon(
          obscure
              ? Icons.visibility_off_outlined
              : Icons.visibility_outlined,
          color: _textMuted,
          size: 20,
        ),
        onPressed: _isLoading ? null : onToggle,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(
          color: _outlineColor,
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(
          color: _outlineColor,
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(
          color: _accentColor,
          width: 1.5,
        ),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(
          color: Colors.redAccent,
        ),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(
          color: Colors.redAccent,
          width: 1.5,
        ),
      ),
      disabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(
          color: _outlineColor.withValues(alpha: 0.4),
        ),
      ),
    );
  }

  Widget _fieldLabel(String text) {
    return Text(
      text,
      style: const TextStyle(
        color: _textMain,
        fontSize: 13,
        fontWeight: FontWeight.w600,
      ),
    );
  }

  String? _validateCurrentPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter your current password';
    }

    return null;
  }

  String? _validateNewPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter a new password';
    }

    if (value.length < 8) {
      return 'Password should be at least 8 characters';
    }

    return null;
  }

  String? _validateConfirmPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please re-enter your new password';
    }

    if (value != _newController.text) {
      return 'Passwords do not match';
    }

    return null;
  }

  Future<void> _submit() async {
    if (_isLoading) return;

    final isValid = _formKey.currentState?.validate() ?? false;

    if (!isValid) return;

    setState(() {
      _isLoading = true;
      _serverError = null;
    });

    try {
      await ref.read(userProvider.notifier).changePassword(
            currentPassword: _currentController.text,
            newPassword: _newController.text,
          );

      TextInput.finishAutofillContext();

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Password changed successfully! 🔒'),
        ),
      );

      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _serverError = _getUserFriendlyError(e);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  String _getUserFriendlyError(Object error) {
    final message = error.toString();

    if (message.contains('current password') ||
        message.contains('Current password')) {
      return 'Your current password is incorrect.';
    }

    if (message.contains('network') ||
        message.contains('Network') ||
        message.contains('connection') ||
        message.contains('Connection')) {
      return 'Unable to connect to the server. Please try again.';
    }

    return 'Unable to change your password. Please try again.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(
          color: _textMain,
        ),
        title: const Text(
          'Change Password',
          style: TextStyle(
            color: _textMain,
            fontWeight: FontWeight.w600,
            fontSize: 20,
          ),
        ),
      ),
      body: AutofillGroup(
        child: Form(
          key: _formKey,
          autovalidateMode: AutovalidateMode.onUserInteraction,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: _doodleDecoration(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_serverError != null) ...[
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.redAccent.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: Colors.redAccent.withValues(alpha: 0.35),
                          ),
                        ),
                        child: Text(
                          _serverError!,
                          style: const TextStyle(
                            color: Colors.redAccent,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    _fieldLabel('Current Password'),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _currentController,
                      enabled: !_isLoading,
                      obscureText: _obscureCurrent,
                      keyboardType: TextInputType.visiblePassword,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [
                        AutofillHints.password,
                      ],
                      validator: _validateCurrentPassword,
                      decoration: _fieldDecoration(
                        hint: 'Enter current password',
                        obscure: _obscureCurrent,
                        onToggle: () {
                          setState(() {
                            _obscureCurrent = !_obscureCurrent;
                          });
                        },
                      ),
                    ),
                    const SizedBox(height: 18),
                    _fieldLabel('New Password'),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _newController,
                      enabled: !_isLoading,
                      obscureText: _obscureNew,
                      keyboardType: TextInputType.visiblePassword,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [
                        AutofillHints.newPassword,
                      ],
                      validator: _validateNewPassword,
                      decoration: _fieldDecoration(
                        hint: 'At least 8 characters',
                        obscure: _obscureNew,
                        onToggle: () {
                          setState(() {
                            _obscureNew = !_obscureNew;
                          });
                        },
                      ),
                    ),
                    const SizedBox(height: 18),
                    _fieldLabel('Re-enter New Password'),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _confirmController,
                      enabled: !_isLoading,
                      obscureText: _obscureConfirm,
                      keyboardType: TextInputType.visiblePassword,
                      textInputAction: TextInputAction.done,
                      autofillHints: const [
                        AutofillHints.newPassword,
                      ],
                      validator: _validateConfirmPassword,
                      onFieldSubmitted: (_) {
                        if (!_isLoading) {
                          _submit();
                        }
                      },
                      decoration: _fieldDecoration(
                        hint: 'Confirm new password',
                        obscure: _obscureConfirm,
                        onToggle: () {
                          setState(() {
                            _obscureConfirm = !_obscureConfirm;
                          });
                        },
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: DecoratedBox(
                  decoration: _doodleDecoration(
                    color: _isLoading
                        ? Colors.grey.shade300
                        : _accentColor,
                    borderRadius: 16,
                  ),
                  child: FilledButton(
                    onPressed: _isLoading ? null : _submit,
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      disabledBackgroundColor: Colors.transparent,
                      foregroundColor: _textMain,
                      disabledForegroundColor: _textMuted,
                      elevation: 0,
                      shadowColor: Colors.transparent,
                      padding: const EdgeInsets.symmetric(
                        vertical: 14,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: _textMain,
                            ),
                          )
                        : const Text(
                            'Change Password',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
