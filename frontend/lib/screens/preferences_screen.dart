import 'package:flutter/material.dart';
import 'package:foodlens_mobile/services/local_storage_service.dart';

class PreferencesScreen extends StatefulWidget {
  const PreferencesScreen({super.key});

  static const Map<String, List<String>> allergenKeywords = {
    "Süt ve Süt Ürünleri": [
      "süt",
      "sut",
      "laktoz",
      "lactose",
      "kazein",
      "casein",
      "whey",
      "peynir",
      "yoğurt",
      "yogurt",
      "tereyağı",
      "tereyagi",
      "krema",
    ],
    "Gluten (Buğday, Arpa, vb.)": [
      "gluten",
      "buğday",
      "bugday",
      "arpa",
      "çavdar",
      "cavdar",
      "yulaf",
      "un",
      "irmik",
      "semolina",
      "malt",
    ],
    "Yer Fıstığı": [
      "yer fıstığı",
      "yer fistigi",
      "peanut",
      "peanuts",
      "arachis",
    ],
    "Sert Kabuklu Yemişler (Fındık, Antep Fıstığı vb.)": [
      "fındık",
      "findik",
      "badem",
      "ceviz",
      "kaju",
      "antep fıstığı",
      "antep fistigi",
      "hazelnut",
      "almond",
      "walnut",
      "cashew",
      "pistachio",
      "pecan",
      "macadamia",
    ],
    "Soya Fasulyesi": [
      "soya",
      "soy",
      "soy protein",
      "soy flour",
      "soya lesitini",
      "soy lecithin",
    ],
    "Yumurta": [
      "yumurta",
      "egg",
      "albumin",
      "ovalbumin",
      "egg white",
      "egg yolk",
    ],
    "Balık": [
      "balık",
      "balik",
      "fish",
      "somon",
      "ton balığı",
      "ton baligi",
      "hamsi",
    ],
    "Deniz Kabukluları": [
      "karides",
      "shrimp",
      "prawn",
      "midye",
      "mussel",
      "yengeç",
      "yengec",
      "crab",
      "istakoz",
      "lobster",
      "kalamar",
      "squid",
    ],
    "Susam": ["susam", "sesame", "tahin"],
    "Kereviz": ["kereviz", "celery"],
    "Hardal": ["hardal", "mustard"],
    "Kükürt Dioksit ve Sülfitler": [
      "sülfit",
      "sulfit",
      "sulfite",
      "sulphite",
      "kükürt dioksit",
      "kukurt dioksit",
      "sulfur dioxide",
    ],
    "Acı Bakla (Lüpen)": ["lüpen", "lupen", "lupin"],
  };

  @override
  State<PreferencesScreen> createState() => _PreferencesScreenState();
}

class _PreferencesScreenState extends State<PreferencesScreen> {
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

  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSelectedAllergens();
  }

  Future<void> _loadSelectedAllergens() async {
    final selected = await LocalStorageService.getSelectedAllergens();
    if (!mounted) return;

    setState(() {
      for (final key in _allergens.keys) {
        _allergens[key] = selected.contains(key);
      }
      _isLoading = false;
    });
  }

  Future<void> _persistSelections() async {
    final selected = _allergens.entries
        .where((entry) => entry.value)
        .map((entry) => entry.key)
        .toSet();

    await LocalStorageService.saveSelectedAllergens(selected);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(
          title: const Text(
            "Hassasiyetlerim",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          centerTitle: true,
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Hassasiyetlerim",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
      ),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              "Aşağıdaki maddelerden hassasiyetiniz veya alerjiniz olanları seçin. Analiz sonuçlarında eşleşen maddeler kırmızı şekilde vurgulanacaktır.",
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
                title: Text(
                  key,
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                value: _allergens[key]!,
                activeThumbColor: Colors.green,
                onChanged: (bool value) async {
                  setState(() {
                    _allergens[key] = value;
                  });
                  await _persistSelections();
                },
              ),
            );
          }),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
