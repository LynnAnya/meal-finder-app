import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'auth_screen.dart';
import '../providers/user_provider.dart';
import 'change_password_screen.dart';
import '../models/user.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});
  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  // 🎨 Theme Colors
  final Color bgColor = const Color(0xFFFEFDF7);
  final Color cardColor = Colors.white;
  final Color accentColor = const Color.fromARGB(255, 187, 182, 242);
  final Color textMain = const Color.fromARGB(255, 48, 48, 48);
  final Color textMuted = const Color(0xFF757575);
  final Color outlineColor = const Color.fromARGB(255, 88, 88, 88);

  bool _notificationsEnabled = true;
  
  // 📸 Image Picker Instance
  final ImagePicker _picker = ImagePicker();

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

  //
  Widget _buildProfileAvatar(User user, {required double radius, required double iconSize}) {
    // 1. Get image string from model
    final String? imageName = user.imageFile ?? user.imagePath;

    String? fullImageUrl;
    if (imageName != null && imageName.isNotEmpty) {
      // Clean any accidental leading slash
      final cleanPath = imageName.startsWith('/') ? imageName.substring(1) : imageName;

      if (cleanPath.startsWith('http')) {
        fullImageUrl = cleanPath;
      } else if (cleanPath.startsWith('media/')) {
        // Backend returned 'media/profile_pics/sample.jpg'
        fullImageUrl = 'http://127.0.0.1:8000/$cleanPath';
      } else if (cleanPath.startsWith('profile_pics/')) {
        // Backend returned 'profile_pics/sample.jpg'
        fullImageUrl = 'http://127.0.0.1:8000/media/$cleanPath';
      } else {
        // Backend returned raw filename 'sample.jpg'
        fullImageUrl = 'http://127.0.0.1:8000/media/profile_pics/$cleanPath';
      }
    }

    return CircleAvatar(
      radius: radius,
      backgroundColor: accentColor,
      foregroundImage: fullImageUrl != null ? NetworkImage(fullImageUrl) : null,
      child: Icon(Icons.person_rounded, color: textMain, size: iconSize),
    );
  }
 
  // 🗑️ Delete Account Logic
  Future<void> _executeDeleteAccount() async {
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);

    navigator.pop(); // Pop confirmation dialog
    
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    try {
      await ref.read(userProvider.notifier).deleteAccount();
      
      navigator.pop(); // Remove spinner
      navigator.pushAndRemoveUntil(
        MaterialPageRoute(builder: (context) => const AuthScreen()), 
        (route) => false,
      );
    } catch (e) {
      navigator.pop(); // Remove spinner
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to delete account: $e')),
      );
    }
  }

  void _showDeleteConfirmation() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.5)),
          title: Text('Delete Account', style: TextStyle(color: textMain, fontWeight: FontWeight.bold)),
          content: Text(
            'Are you sure you want to delete your account? This action cannot be undone and all your data will be lost.',
            style: TextStyle(color: textMain),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('Cancel', style: TextStyle(color: textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: _executeDeleteAccount,
              child: const Text('Delete', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  // 📸 Handle Pick & Upload Image
  Future<void> _pickAndUploadImage() async {
    final messenger = ScaffoldMessenger.of(context); 
    try {
      final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
      if (image != null) {
        await ref.read(userProvider.notifier).uploadProfilePicture(File(image.path));
        
        messenger.showSnackBar(
          const SnackBar(content: Text('Profile picture updated! 📸')),
        );
      }
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to upload image: $e')),
      );
    }
  }

  //Handle Delete Image
  Future<void> _removeImage() async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(userProvider.notifier).deleteProfilePicture();
      
      messenger.showSnackBar(
        const SnackBar(content: Text('Profile picture removed! 🗑️')),
      );
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to remove image: $e')),
      );
    }
  }

  //  Show Tall User Details Modal
  void _showUserDetailsModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Consumer(
          builder: (context, ref, child) {
            final userState = ref.watch(userProvider);
            final user = userState.value;
            
            if (user == null) return const SizedBox();

            final String? imageName = user.imageFile ?? user.imagePath;

            return FractionallySizedBox(
              heightFactor: 0.85,
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                  border: Border.all(color: outlineColor, width: 2.0),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Drag Handle
                    Center(
                      child: Container(
                        width: 40,
                        height: 5,
                        margin: const EdgeInsets.only(bottom: 24),
                        decoration: BoxDecoration(
                          color: outlineColor.withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                    
                    //  Modern Social Avatar with Camera Badge Overlay
                    Center(
                      child: Column(
                        children: [
                          GestureDetector(
                            onTap: _pickAndUploadImage,
                            child: Stack(
                              children: [
                                // 1. Avatar Container
                                Container(
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(color: outlineColor, width: 2.0),
                                  ),
                                  child: _buildProfileAvatar(user, radius: 48, iconSize: 50),
                                ),

                                // 2. Floating Camera Badge 
                                Positioned(
                                  bottom: 0,
                                  right: 0,
                                  child: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: cardColor,
                                      shape: BoxShape.circle,
                                      border: Border.all(color: outlineColor, width: 1.5),
                                      boxShadow: [
                                        BoxShadow(
                                          color: outlineColor,
                                          offset: const Offset(1, 1),
                                          blurRadius: 0,
                                        ),
                                      ],
                                    ),
                                    child: Icon(Icons.camera_alt_rounded, size: 18, color: textMain),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          
                          // Smart Remove Button (Only shown when image exists)
                          if (imageName != null && imageName.isNotEmpty) ...[
                            const SizedBox(height: 12),
                            TextButton.icon(
                              onPressed: _removeImage,
                              icon: const Icon(Icons.delete, size: 16, color: Colors.redAccent),
                              label: const Text(
                                'Remove Photo',
                                style: TextStyle(color: Colors.redAccent, fontSize: 13, fontWeight: FontWeight.w600),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    
                    const SizedBox(height: 32),
                    Text('Account Details', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: textMain)),
                    const SizedBox(height: 20),
                    
                    _buildDetailRow(Icons.person_outline, 'Username', user.username),
                    const SizedBox(height: 12),
                    _buildDetailRow(Icons.email_outlined, 'Email', user.email),
                    const SizedBox(height: 12),
                    _buildDetailRow(Icons.calendar_today, 'First joined', 'Recently'),
                    
                    const Spacer(),
                    const Divider(),
                    
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.delete_forever, color: Colors.redAccent),
                      title: const Text('Delete my account and data', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
                      onTap: () {
                        Navigator.pop(context); 
                        _showDeleteConfirmation(); 
                      },
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: textMuted, size: 20),
        const SizedBox(width: 12),
        Text('$label: ', style: TextStyle(color: textMuted, fontSize: 16)),
        Expanded(child: Text(value, style: TextStyle(color: textMain, fontSize: 16, fontWeight: FontWeight.w600))),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final userState = ref.watch(userProvider);
    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: IconThemeData(color: textMain),
        title: Text(
          'My Profile',
          style: TextStyle(color: textMain, fontWeight: FontWeight.w600, fontSize: 22),
        ),
      ),
      body: userState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error: $err', style: const TextStyle(color: Colors.redAccent))),
        data: (user) {
          if (user == null) return const Center(child: Text('No user found.'));

          return ListView(
            padding: const EdgeInsets.all(16.0),
            children: [
              // 1. Dynamic Profile Header Card
              GestureDetector(
                onTap: _showUserDetailsModal,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: _doodleDecoration(),
                  child: Row(
                    children: [
                      _buildProfileAvatar(user, radius: 28, iconSize: 32),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${user.username} 🍕',
                              style: TextStyle(color: textMain, fontSize: 18, fontWeight: FontWeight.bold),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              user.email,
                              style: TextStyle(color: textMuted, fontSize: 14),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right, color: textMuted),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // 2. Settings Options List
              Container(
                decoration: _doodleDecoration(),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12.5),
                  child: Material(
                    color: Colors.transparent,
                    child: Column(
                      children: [
                        ListTile(
                          leading: Icon(Icons.person_outline, color: textMain),
                          title: Text('Change Password', style: TextStyle(color: textMain, fontWeight: FontWeight.w500)),
                          trailing: Icon(Icons.chevron_right, color: textMuted),
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (context) => const ChangePasswordScreen(),
                              ),
                            );
                          },
                        ),
                        Divider(height: 1, color: Colors.grey.shade300),
                        SwitchListTile(
                          secondary: Icon(Icons.notifications_none, color: textMain),
                          title: Text('Push Notifications', style: TextStyle(color: textMain, fontWeight: FontWeight.w500)),
                          activeThumbColor: accentColor,
                          activeTrackColor: accentColor.withValues(alpha: 0.5), 
                          value: _notificationsEnabled,
                          onChanged: (val) {
                            setState(() {
                              _notificationsEnabled = val;
                            });
                          },
                        ),
                        Divider(height: 1, color: Colors.grey.shade300),
                        ListTile(
                          leading: Icon(Icons.lock_outline, color: textMain),
                          title: Text('Privacy Policy', style: TextStyle(color: textMain, fontWeight: FontWeight.w500)),
                          trailing: Icon(Icons.chevron_right, color: textMuted),
                          onTap: () {},
                        ),
                        Divider(height: 1, color: Colors.grey.shade300),
                        ListTile(
                          leading: const Icon(Icons.logout, color: Colors.redAccent),
                          title: const Text('Log Out', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.w600)),
                          onTap: () async {
                            final navigator = Navigator.of(context);
                            
                            await ref.read(userProvider.notifier).clearSession();
                            
                            navigator.pushAndRemoveUntil(
                              MaterialPageRoute(builder: (context) => const AuthScreen()), 
                              (route) => false,
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}