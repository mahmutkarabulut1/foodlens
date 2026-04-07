import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocalStorageService {
  static const String _selectedAllergensKey = 'selected_allergens';
  static const String _savedItemsKey = 'saved_items';
  static const String _hasSeenWelcomeKey = 'has_seen_welcome';

  static final ValueNotifier<int> preferencesVersion = ValueNotifier<int>(0);
  static final ValueNotifier<int> savedItemsVersion = ValueNotifier<int>(0);

  static Future<Set<String>> getSelectedAllergens() async {
    final prefs = await SharedPreferences.getInstance();
    final values = prefs.getStringList(_selectedAllergensKey) ?? <String>[];
    return values.toSet();
  }

  static Future<void> saveSelectedAllergens(Set<String> allergens) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_selectedAllergensKey, allergens.toList());
    preferencesVersion.value++;
  }

  static Future<List<Map<String, dynamic>>> getSavedItems() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_savedItemsKey);

    if (raw == null || raw.trim().isEmpty) {
      return <Map<String, dynamic>>[];
    }

    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        return decoded
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList();
      }
    } catch (e) {
      debugPrint('Kaydedilen ürünler okunurken hata: $e');
      return <Map<String, dynamic>>[];
    }

    return <Map<String, dynamic>>[];
  }

  static Object? _toJsonSafe(Object? value) {
    if (value == null || value is String || value is num || value is bool) {
      return value;
    }

    if (value is Map) {
      return value.map(
        (key, val) => MapEntry(key.toString(), _toJsonSafe(val)),
      );
    }

    if (value is Iterable) {
      return value.map(_toJsonSafe).toList();
    }

    return value.toString();
  }

  static Future<void> saveSavedItem(Map<String, dynamic> item) async {
    final prefs = await SharedPreferences.getInstance();
    final items = await getSavedItems();

    final safeItem = Map<String, dynamic>.from(
      (_toJsonSafe(item) as Map).map(
        (key, value) => MapEntry(key.toString(), value),
      ),
    );

    items.insert(0, safeItem);

    final safeItems = _toJsonSafe(items);
    await prefs.setString(_savedItemsKey, jsonEncode(safeItems));
    savedItemsVersion.value++;
  }

  static Future<void> deleteSavedItem(int index) async {
    final prefs = await SharedPreferences.getInstance();
    final items = await getSavedItems();

    if (index < 0 || index >= items.length) {
      return;
    }

    items.removeAt(index);
    await prefs.setString(_savedItemsKey, jsonEncode(_toJsonSafe(items)));
    savedItemsVersion.value++;
  }

  static Future<bool> getHasSeenWelcome() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_hasSeenWelcomeKey) ?? false;
  }

  static Future<void> setHasSeenWelcome(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_hasSeenWelcomeKey, value);
  }
}
