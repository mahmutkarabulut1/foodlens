import 'package:flutter/material.dart';

class PreferencesScreen extends StatefulWidget {
  const PreferencesScreen({super.key});

  // Raporundaki FR-4 gereği: Yazım varyasyonlarını yakalamak için eş anlamlılar listesi [cite: 105]
static const Map<String, List<String>> allergenKeywords = {
  "Süt ve Süt Ürünleri": ["süt", "peynir", "yoğurt", "laktoz", "kazein", "whey", "sut"],
  "Gluten (Buğday, Arpa, vb.)": ["buğday", "arpa", "yulaf", "gluten", "un", "nişasta", "bugday"],
  "Sert Kabuklu Yemişler (Fındık, Antep Fıstığı vb.)": ["fındık", "fıstık", "badem", "ceviz", "kaju", "findik", "fistik"],
  "Deniz Kabukluları": ["karides", "midye", "yengeç", "istakoz", "kalamar", "yengec"],
  "Soya Fasulyesi": ["soya", "lesitin", "soy"],
  "Yumurta": ["yumurta", "albumin", "sarısı", "akı", "yumurta"],
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
          // Map'teki her alerjen için bir Switch (Aç/Kapat) oluşturuyoruz [cite: 113]
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
                activeThumbColor: Colors.green,
                onChanged: (bool value) {
                  setState(() {
                    _allergens[key] = value;
                  });
                  // İleride buraya yerel veritabanı (Hive) kaydetme gelecek [cite: 114, 137]
                },
              ),
            );
          }),
        ],
      ),
    );
  }
}