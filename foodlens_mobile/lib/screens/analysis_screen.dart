import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart'; // Hafıza için eklendi
import 'preferences_screen.dart'; // Sözlük verisi için gerekli

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  File? _image;
  bool _isLoading = false;
  List<dynamic> _results = [];
  List<String> _activeAllergens = []; // Kullanıcının seçtiği aktif alerjenler
  
  // ignore: unused_field
  String _ocrText = "";

  final String apiUrl = "https://foodlens-api-592742840350.europe-west3.run.app/analyze";
  final ImagePicker _picker = ImagePicker();

@override
  void initState() {
    super.initState();
    _loadUserPreferences(); // İlk açılışta yükle
  }


  // FR-6: Kullanıcı tercihlerini hafızadan en hızlı şekilde yükler
  Future<void> _loadUserPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _activeAllergens = prefs.getStringList('user_allergens') ?? [];
    });
  }


  // --- FOTOĞRAF SEÇME VE OPTİMİZASYON ---
  Future<void> _pickImage(ImageSource source) async {
    try {
      // BURASI KRİTİK: Hem Kamera hem Galeri için optimizasyon yapıyoruz
      final XFile? pickedFile = await _picker.pickImage(
        source: source,
        maxWidth: 2160,   // Genişliği 1080 pikselle sınırla (Full HD yeterli)
        maxHeight: 3840,  // Yüksekliği sınırla
        imageQuality: 90, // Kaliteyi %85'e çek (Dosya boyutu küçülür, hız artar)
      );

      if (pickedFile != null) {
        setState(() {
          _image = File(pickedFile.path);
          _results = []; // Eski sonuçları temizle
          _ocrText = "";
        });
        
        // Kullanıcıya bilgi verelim
        if (mounted) {
           ScaffoldMessenger.of(context).showSnackBar(
             const SnackBar(
               content: Text("Fotoğraf optimize ediliyor ve taranıyor... ⏳"), 
               duration: Duration(seconds: 1),
             )
           );
        }

        // Resmi seçince otomatik işle
        _processImage();
      }
    } catch (e) {
      _showError("Resim seçilirken hata oluştu: $e");
    }
  }

  // --- OCR VE İÇERİK FİLTRELEME ---
  Future<void> _processImage() async {
    if (_image == null) return;
    setState(() => _isLoading = true);



    try {
      await _loadUserPreferences();
      final inputImage = InputImage.fromFile(_image!);
      final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final RecognizedText recognizedText = await textRecognizer.processImage(inputImage);
      
      String rawText = recognizedText.text;
      
      if (rawText.trim().isEmpty) {
        _showError("Yazı okunamadı. Lütfen net bir fotoğraf çekin.");
        setState(() => _isLoading = false);
        return;
      }

      // İçindekiler filtresi
      String lowerText = rawText.toLowerCase();
      int index = lowerText.indexOf("içindekiler");
      if (index == -1) index = lowerText.indexOf("ingredients");

      String processedText = index != -1 ? rawText.substring(index) : rawText;

      // Negatif ifadeleri temizle (Yoktur/İçermez)
      List<String> cleanLines = processedText.split('\n').where((line) {
        String l = line.toLowerCase();
        return !l.contains("yoktur") && !l.contains("içermez") && !l.contains("free from");
      }).toList();
      
      String finalText = cleanLines.join("\n");
      setState(() => _ocrText = finalText);

      await _analyzeWithApi(finalText);
      textRecognizer.close();
    } catch (e) {
      _showError("OCR Hatası: $e");
      setState(() => _isLoading = false);
    }
  }

  // --- API İLETİŞİMİ ---
  Future<void> _analyzeWithApi(String text) async {
    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"ocr_text": text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)); 
        setState(() {
          _results = data['results'];
          _isLoading = false;
        });
      } else {
        _showError("Sunucu Hatası: ${response.statusCode}");
        setState(() => _isLoading = false);
      }
    } catch (e) {
      _showError("Bağlantı Hatası: $e");
      setState(() => _isLoading = false);
    }
  }

  void _showError(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message), backgroundColor: Colors.red));
    }
  }
  // --- SONUCU KAYDETME DİYALOĞU ---
  Future<void> _saveResultDialog() async {
    if (_results.isEmpty) return;
    
    TextEditingController nameController = TextEditingController();
    
    showDialog(
      // context ismini dialogContext yaptık ki ana sayfanın context'i ile karışmasın
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text("Sonucu Kaydet", style: TextStyle(fontWeight: FontWeight.bold)),
        content: TextField(
          controller: nameController,
          decoration: const InputDecoration(
            hintText: "Ürün adı (Örn: Çikolatalı Gofret)",
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text("İptal")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
            onPressed: () async {
              if (nameController.text.trim().isEmpty) return;

              // 1. Adını al
              final String productName = nameController.text.trim();

              // 2. DİYALOĞU HEMEN KAPAT (Bekletmeye gerek yok)
              Navigator.pop(dialogContext);
              
              // 3. Arka planda kaydetme işlemini yap
              final prefs = await SharedPreferences.getInstance();
              List<String> savedList = prefs.getStringList('saved_products') ?? [];
              
              Map<String, dynamic> newProduct = {
                'id': DateTime.now().millisecondsSinceEpoch.toString(),
                'name': productName,
                'date': "${DateTime.now().day}/${DateTime.now().month}/${DateTime.now().year}",
                'results': _results, 
              };
              
              savedList.add(jsonEncode(newProduct));
              await prefs.setStringList('saved_products', savedList);
              
              // 4. Ana sayfa hala açıksa bildirimi göster
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Ürün başarıyla kaydedildi!"), backgroundColor: Colors.green)
                );
              }
            }, 
            child: const Text("Kaydet")
          ),
        ],
      )
    );
  }

  // --- RENK VE İKON MANTIĞI ---
  Color _getRiskColor(String risk) {
    switch (risk.toLowerCase()) {
      case 'high': return Colors.red.shade100;
      case 'moderate': return Colors.orange.shade100;
      case 'low': return Colors.green.shade100;
      default: return Colors.grey.shade100;
    }
  }

  Color _getIconColor(String risk) {
    switch (risk.toLowerCase()) {
      case 'high': return Colors.red;
      case 'moderate': return Colors.orange;
      case 'low': return Colors.green;
      default: return Colors.grey;
    }
  }

  void _showDescriptionDialog(BuildContext context, String title, String description) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        content: Text(description.isNotEmpty ? description : "Açıklama bulunmamaktadır."),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text("Tamam"))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("FoodLens AI Scan", style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        backgroundColor: Colors.green.shade100,
        actions: [
          // Sadece sonuç varsa kaydet butonunu göster
          if (_results.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.bookmark_add, size: 28),
              onPressed: _saveResultDialog,
              tooltip: "Sonucu Kaydet",
            )
        ],
      ),
      body: Column(
        children: [
          // FOTOĞRAF ÖNİZLEME
          Container(
            height: 220,
            width: double.infinity,
            color: Colors.grey.shade200,
            child: _image != null
                ? Image.file(_image!, fit: BoxFit.cover)
                : const Center(child: Icon(Icons.camera_alt, size: 50, color: Colors.grey)),
          ),
          
          const SizedBox(height: 15),
          
          // AKSİYON BUTONLARI
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton.icon(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.camera),
                label: const Text("Kamera"),
              ),
              ElevatedButton.icon(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.photo),
                label: const Text("Galeri"),
              ),
            ],
          ),

          const Divider(height: 30),

          // ANALİZ SONUÇLARI
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _results.isEmpty
                    ? const Center(child: Text("Analiz sonucu bulunamadı", style: TextStyle(color: Colors.grey)))
                    : ListView.builder(
                        itemCount: _results.length,
                        padding: const EdgeInsets.all(10),
                        itemBuilder: (context, index) {
                          final item = _results[index];
                          final String itemName = item['name'].toString().toLowerCase();
                          
                          // FR-4 & FR-6: Hızlı Alerjen Eşleşme Kontrolü
                          bool isAllergicMatch = false;
                          for (String allergyKey in _activeAllergens) {
                            List<String>? synonyms = PreferencesScreen.allergenKeywords[allergyKey];
                            if (synonyms != null && synonyms.any((syn) => itemName.contains(syn.toLowerCase()))) {
                              isAllergicMatch = true;
                              break;
                            }
                          }

                          return Card(
                            color: isAllergicMatch ? Colors.red.shade400 : _getRiskColor(item['risk_level']),
                            elevation: isAllergicMatch ? 6 : 2,
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: Colors.white,
                                child: Icon(
                                  isAllergicMatch ? Icons.report_problem : Icons.info_outline,
                                  color: isAllergicMatch ? Colors.red : _getIconColor(item['risk_level']),
                                ),
                              ),
                              title: Text(item['name'], 
                                style: TextStyle(
                                  fontWeight: FontWeight.bold, 
                                  color: isAllergicMatch ? Colors.white : Colors.black)),
                              subtitle: Text(
                                isAllergicMatch ? "⚠️ HASSASİYETİNİZ!" : "Risk: ${item['risk_level']}",
                                style: TextStyle(color: isAllergicMatch ? Colors.white70 : Colors.black54)),
                              trailing: const Icon(Icons.chevron_right, color: Colors.white54),
                              onTap: () => _showDescriptionDialog(context, item['name'], item['description'] ?? ""),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}