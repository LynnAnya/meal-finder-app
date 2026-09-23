import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart'; 
import '../services/auth_api.dart';
import '../core/storage/token_storage.dart'; 
import '../providers/user_provider.dart'; 
import 'forgot_password_screen.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  bool _isLogin = true;
  bool _isLoading = false; 
  bool _isPasswordVisible = false; 

  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  final AuthApi _authApi = AuthApi();

  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color registerAccent = const Color(0xFFFF8FA3);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 88, 88, 88);

  BoxDecoration _doodleDecoration({Color? color, double borderRadius = 12.5}) {
    return BoxDecoration(
      color: color ?? cardColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: outlineColor, width: 1.0),
      boxShadow: [
        BoxShadow(
          color: outlineColor,
          offset: const Offset(2, 2),
          blurRadius: 0,
        ),
      ],
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    setState(() {
      _isLoading = true; 
    });

    try {
      if (_isLogin) {
        final token = await _authApi.loginForAccessToken(
          email: _emailController.text.trim(), 
          password: _passwordController.text.trim(),
        );

        await TokenStorage.saveToken(
          accessToken: token.accessToken,
          tokenType: token.tokenType,
        );

        ref.invalidate(userProvider);

        if (mounted) {
          Navigator.pushReplacementNamed(context, '/main');
        }
      } else {
        final username = _usernameController.text.trim();
        final email = _emailController.text.trim();
        final password = _passwordController.text.trim();

        if (password.length < 8) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Password must be at least 8 characters long.'),
              backgroundColor: Colors.orangeAccent,
            ),
          );
          return;
        }

        await _authApi.registerUser(
          username: username,
          email: email,
          password: password,
        );

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Account $username ($email) created! Please log in.')),
          );
          setState(() {
            _isLogin = true;
            _passwordController.clear(); 
            _usernameController.clear(); 
          });
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Meal Finder 🍽️',
                  style: TextStyle(
                    color: textMain,
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _isLogin 
                      ? 'Welcome back! Get ready to find your next meal' 
                      : 'Create an account to join the community!',
                  style: TextStyle(color: textMuted, fontSize: 14),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),

                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: _doodleDecoration(),
                  child: Column(
                    children: [
                      if (!_isLogin) ...[
                        TextField(
                          controller: _usernameController,
                          decoration: InputDecoration(
                            labelText: 'Username',
                            prefixIcon: Icon(Icons.person_outline, color: textMain),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      TextField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        decoration: InputDecoration(
                          labelText: 'Email Address',
                          prefixIcon: Icon(Icons.email_outlined, color: textMain),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      TextField(
                        controller: _passwordController,
                        obscureText: !_isPasswordVisible, 
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: Icon(Icons.lock_outline, color: textMain),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _isPasswordVisible ? Icons.visibility : Icons.visibility_off,
                              color: textMain,
                            ),
                            onPressed: () {
                              setState(() {
                                _isPasswordVisible = !_isPasswordVisible;
                              });
                            },
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                      
                      if (_isLogin) ...[
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: _isLoading
                                ? null
                                : () {
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => const ForgotPasswordScreen(),
                                      ),
                                    );
                                  },
                            child: Text(
                              'Forgot your Password?',
                              style: TextStyle(
                                color: textMuted,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ] else ...[
                        const SizedBox(height: 24),
                      ],

                      GestureDetector(
                        onTap: _isLoading ? null : _handleSubmit, 
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          decoration: _doodleDecoration(
                            color: _isLoading 
                                ? Colors.grey.shade300 
                                : (_isLogin ? accentColor : registerAccent),
                            borderRadius: 10,
                          ),
                          alignment: Alignment.center,
                          child: _isLoading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.black,
                                  ),
                                )
                              : Text(
                                  _isLogin ? 'Sign In' : 'Register',
                                  style: TextStyle(
                                    color: textMain,
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _isLogin ? "Don't have an account?" : "Already have an account?",
                      style: TextStyle(color: textMuted),
                    ),
                    TextButton(
                      onPressed: _isLoading 
                          ? null 
                          : () {
                              setState(() {
                                _isLogin = !_isLogin;
                                _passwordController.clear();
                              });
                            },
                      child: Text(
                        _isLogin ? 'Register' : 'Sign In',
                        style: TextStyle(
                          color: textMain,
                          fontWeight: FontWeight.bold,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}