import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'package:http/http.dart' as http;
import 'network_exceptions.dart';
import '../storage/token_storage.dart';

class ApiClient {
  final String baseUrl = 'http://127.0.0.1:8000' ;
  final http.Client _client;

  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  // ==========================================
  //  AUTO-HEADER INJECTION
  // ==========================================
  Future<Map<String, String>> _getHeaders({bool isForm = false}) async {
    final String? token = await TokenStorage.getToken();

    final Map<String, String> headers = {
      'Content-Type': isForm ? 'application/x-www-form-urlencoded' : 'application/json',
      'Accept': 'application/json',
    };

    // If the user is logged in, attach the token to every request automatically!
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Handles JSON GET requests with optional query parameters
  Future<T> getJson<T>({
    required String path,
    Map<String, String>? queryParameters,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: queryParameters?.isNotEmpty == true ? queryParameters : null,
    );

    try {
      // Attached headers 
      final response = await _client
          .get(uri, headers: await _getHeaders())
          .timeout(const Duration(seconds: 10));

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } on SocketException catch (e, stack) {
      developer.log(
        'Network unreachable',
        error: e,
        stackTrace: stack,
        name: 'ApiClient',
      );
      throw NetworkException('No internet connection.', e);
    } on TimeoutException catch (e, stack) {
      developer.log(
        'Request timed out: $uri',
        error: e,
        stackTrace: stack,
        name: 'ApiClient',
      );
      throw NetworkException('Server took too long to respond.', e);
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Unexpected request error: $e', e);
    }
  }

  /// Handles JSON POST requests
  Future<T> postJson<T>({
    required String path,
    required Map<String, dynamic> body,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final url = Uri.parse('$baseUrl$path');

    try {
      final response = await _client
          .post(
            url,
            headers: await _getHeaders(), 
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 10));

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } on SocketException catch (e, stack) {
      developer.log('Network unreachable', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('No internet connection.', e);
    } on TimeoutException catch (e, stack) {
      developer.log('Request timed out', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('Server took too long to respond.', e);
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Unexpected request error: $e', e);
    }
  }

  /// Handles Form-UrlEncoded POST requests (OAuth2 / Login)
  Future<T> postForm<T>({
    required String path,
    required Map<String, String> body,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final url = Uri.parse('$baseUrl$path');

    try {
      final response = await _client
          .post(
            url,
            headers: await _getHeaders(isForm: true), 
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } on SocketException catch (e, stack) {
      developer.log('Network unreachable', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('No internet connection.', e);
    } on TimeoutException catch (e, stack) {
      developer.log('Request timed out', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('Server took too long to respond.', e);
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Unexpected request error: $e', e);
    }
  }

  /// Handles JSON DELETE requests 
  Future<T> deleteJson<T>({
    required String path,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final url = Uri.parse('$baseUrl$path');

    try {
      final response = await _client
          .delete(
            url,
            headers: await _getHeaders(), 
          )
          .timeout(const Duration(seconds: 10));

      // 204 means "Success, No Content" (Common for DELETE)
      if (response.statusCode == 204) {
        return onSuccess(null); 
      }

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } on SocketException catch (e, stack) {
      developer.log('Network unreachable', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('No internet connection.', e);
    } on TimeoutException catch (e, stack) {
      developer.log('Request timed out', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('Server took too long to respond.', e);
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Unexpected request error: $e', e);
    }
  }

  /// patch 
  Future<T> patchJson<T>({
    required String path,
    required Map<String, dynamic> body,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final url = Uri.parse('$baseUrl$path');
    try {
      final response = await _client
          .patch(
            url,
            headers: await _getHeaders(),
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 10));

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } on SocketException catch (e, stack) {
      developer.log('Network unreachable', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('No internet connection.', e);
    } on TimeoutException catch (e, stack) {
      developer.log('Request timed out', error: e, stackTrace: stack, name: 'ApiClient');
      throw NetworkException('Server took too long to respond.', e);
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Unexpected request error: $e', e);
    }
  }

  /// Handles Multipart File Uploads (for profile pictures, documents, etc.)
  Future<T> patchMultipart<T>({
    required String path,
    required File file,
    required String fileFieldName, // e.g. 'file' matching FastAPI's file parameter
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final String? token = await TokenStorage.getToken();

    try {
      final request = http.MultipartRequest('PATCH', uri);

      // Auto-attach Authorization Token
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }

      // Attach file stream
      request.files.add(
        await http.MultipartFile.fromPath(fileFieldName, file.path),
      );

      final streamedResponse = await request.send().timeout(const Duration(seconds: 30));
      final response = await http.Response.fromStream(streamedResponse);

      return _parseResponse<T>(
        response: response,
        endpointName: endpointName,
        onSuccess: onSuccess,
      );
    } catch (e) {
      if (e is NetworkException) rethrow;
      throw NetworkException('Failed to upload image: $e', e);
    }
  }

  /// Standardized HTTP response parsing & error extraction
  T _parseResponse<T>({
    required http.Response response,
    required String endpointName,
    required T Function(dynamic data) onSuccess,
  }) {
    dynamic jsonBody;
    try {
      jsonBody = json.decode(response.body);
    } catch (_) {
      jsonBody = null;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return onSuccess(jsonBody);
    } else {
      developer.log(
        'Server Error [${response.statusCode}]: ${response.body}',
        name: 'ApiClient.$endpointName',
      );

      String errorMessage = 'Server returned status ${response.statusCode}';
      if (jsonBody is Map<String, dynamic> && jsonBody.containsKey('detail')) {
        final detail = jsonBody['detail'];
        if (detail is String) {
          errorMessage = detail;
        } else if (detail is List && detail.isNotEmpty) {
          errorMessage = detail.first['msg'] ?? detail.toString();
        }
      }

      throw NetworkException(errorMessage);
    }
  }
}