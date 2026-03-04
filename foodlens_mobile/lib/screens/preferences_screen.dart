import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart'; // Hafıza için ekledik

class PreferencesScreen extends StatefulWidget {
  const PreferencesScreen({super.key});

// FR-4: Tüm alerjen grupları için genişletilmiş anahtar kelime sözlüğü
  static const Map<String, List<String>> allergenKeywords = {
    "Süt ve Süt Ürünleri": [
      "süt", "peynir", "yoğurt", "laktoz", "kazein", "whey", "sut", "kaymak", "tereyağ", "krema", "peyniraltı"
    ],
    "Gluten (Buğday, Arpa, vb.)": [
      "buğday", "arpa", "yulaf", "gluten", "un", "nişasta", "bugday", "çavdar", "irmik", "bulgur", "malt"
    ],
    "Yer Fıstığı": [
      "yer fıstığı", "yerfistigi", "peanut", "yer fıstıgı", "yerfıstığı"
    ],
    "Sert Kabuklu Yemişler (Fındık, Antep Fıstığı vb.)": [
      "fındık", "fıstık", "badem", "ceviz", "kaju", "findik", "fistik", "antep"
    ],
    "Soya Fasulyesi": [
      "soya", "lesitin", "soy", "soya fasulyesi", "soya proteini"
    ],
    "Yumurta": [
      "yumurta", "albumin", "sarısı", "akı", "yumurta akı", "yumurta sarısı", "ovalbumin"
    ],
    "Balık": [
      "balık", "balik", "fish", "ton balığı", "mezgit", "somon", "uskumru", "palamut"
    ],
    "Deniz Kabukluları": [
      "karides", "midye", "yengeç", "istakoz", "kalamar", "yengec", "deniz kabuklusu"
    ],
    "Susam": [
      "susam", "tahin", "sesame", "susam tohumu"
    ],
    "Kereviz": [
      "kereviz", "celery", "kereviz tohumu", "kereviz sapı"
    ],
    "Hardal": [
      "hardal", "mustard", "hardal tohumu", "hardal unu"
    ],
    "Kükürt Dioksit ve Sülfitler": [
      "kükürt", "sülfit", "dioksit", "e220", "e221", "e222", "e223", "e224", "e225", "e226", "e227", "e228", "sulfit"
    ],
    "Acı Bakla (Lüpen)": [
      "acı bakla", "lüpen", "lupin", "aci bakla", "lupen"
    ],
  };

  @override
  State<PreferencesScreen> createState() => _PreferencesScreenState();
}

class _PreferencesScreenState extends State<PreferencesScreen> {
  // Başlangıç değerleri
  final Map<String, bool> _allergens = {
    "Süt ve Süt Ürünleri": false,
    "Gluten (Buğday, Arpa, vb.)": false,
    "Yer Fıstığı": false,
    "Sert Kabuklu Yemişler (Fındık, Antep Fıstığı vb.)": false,
    "Soya Fasulyesi": false,
    "Yumurta": false,
    "Balık": false,
    "Deniz Kabukluları": false,
    "Susam": false,
    "Kereviz": false,
    "Hardal": false,
    "Kükürt Dioksit ve Sülfitler": false,
    "Acı Bakla (Lüpen)": false,
  };

  @override
  void initState() {
    super.initState();
    _loadPreferences(); // Sayfa açılırken hafızayı anında yükle
  }

  // FR-6: Kayıtlı tercihleri hafızadan okuma
  Future<void> _loadPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final List<String>? savedAllergens = prefs.getStringList('user_allergens');

    if (savedAllergens != null) {
      setState(() {
        for (var allergen in savedAllergens) {
          if (_allergens.containsKey(allergen)) {
            _allergens[allergen] = true;
          }
        }
      });
    }
  }

  // Tercihleri arka planda kaydetme (Hız için async işlemi bekletilmez)
  Future<void> _savePreferences() async {
    final prefs = await SharedPreferences.getInstance();
    List<String> activeList = _allergens.entries
        .where((entry) => entry.value == true)
        .map((entry) => entry.key)
                .toList();
    await prefs.setStringList('user_allergens', activeList);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Hassasiyetlerim", style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
      ),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              "Aşağıdaki maddelerden birine hassasiyetiniz varsa seçiniz. Analiz sonuçlarında bu maddeler öncelikli olarak vurgulanacaktır.",
              style: TextStyle(color: Colors.grey),
            ),
          ),
          ..._allergens.keys.map((String key) {
            return Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: Colors.grey.shade200),
              ),
              child: SwitchListTile(
                title: Text(key, style: const TextStyle(fontWeight: FontWeight.w500)),
                value: _allergens[key]!,
                activeThumbColor: Colors.green, // Seçildiğinde yeşil olur
                onChanged: (bool value) {
                  setState(() {
                    _allergens[key] = value;
                  });
                  _savePreferences(); // Kaydetme işlemini arka planda tetikle
                },
              ),
            );
          }),
        ],
      ),
    );
  }
}