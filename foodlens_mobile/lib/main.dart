import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const FoodLensApp());
}

class FoodLensApp extends StatelessWidget {
  const FoodLensApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FoodLens AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const AnalysisScreen(),
    );
  }
}

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  File? _image;
  bool _isLoading = false;
  List<dynamic> _results = [];
  
  // ignore: unused_field
  String _ocrText = "";

  // SENİN CANLI CLOUD RUN ADRESİN
  final String apiUrl = "https://foodlens-api-592742840350.europe-west3.run.app/analyze";

  final ImagePicker _picker = ImagePicker();

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

  // --- AKILLI FİLTRELEME VE OCR MOTORU ---
  Future<void> _processImage() async {
    if (_image == null) return;

    setState(() => _isLoading = true);

    try {
      // 1. ADIM: OCR ile Metni Oku (Google ML Kit)
      final inputImage = InputImage.fromFile(_image!);
      final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final RecognizedText recognizedText = await textRecognizer.processImage(inputImage);
      
      String rawText = recognizedText.text;
      
      // OCR boş dönerse uyar
      if (rawText.trim().isEmpty) {
        _showError("Yazı okunamadı. Lütfen daha net bir fotoğraf çekin.");
        setState(() => _isLoading = false);
        return;
      }

      // 2. ADIM: İÇİNDEKİLER FİLTRESİ
      // Metni "içindekiler" kelimesinden itibaren kes
      String processedText = rawText;
      String lowerText = rawText.toLowerCase();
      
      int indexTR = lowerText.indexOf("içindekiler");
      int indexEN = lowerText.indexOf("ingredients");

      if (indexTR != -1) {
        processedText = rawText.substring(indexTR); 
      } else if (indexEN != -1) {
        processedText = rawText.substring(indexEN);
      }

      // 3. ADIM: "YOKTUR/İÇERMEZ" TUZAĞINI TEMİZLE
      List<String> lines = processedText.split('\n');
      List<String> cleanLines = [];
      
      for (String line in lines) {
        String lowerLine = line.toLowerCase();
        // Yasaklı kelimeler (Negation words) - Bunlar varsa o satırı sil
        if (!lowerLine.contains("yoktur") && 
            !lowerLine.contains("içermez") && 
            !lowerLine.contains("free from") && 
            !lowerLine.contains("no added")) {
          cleanLines.add(line);
        }
      }
      
      String finalText = cleanLines.join("\n");
      setState(() => _ocrText = finalText);

      // 4. ADIM: Metni API'ye Gönder
      await _analyzeWithApi(finalText);

      textRecognizer.close();
    } catch (e) {
      _showError("OCR Hatası: $e");
      setState(() => _isLoading = false);
    }
  }

  // --- SUNUCUYA GÖNDERME ---
  Future<void> _analyzeWithApi(String text) async {
    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"ocr_text": text}),
      );

      if (response.statusCode == 200) {
        // Türkçe karakterler için utf8 decode
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

  // --- AÇIKLAMA PENCERESİ (POP-UP) ---
  void _showDescriptionDialog(BuildContext context, String title, String description) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          content: SingleChildScrollView(
            child: ListBody(
              children: <Widget>[
                Text(
                  description.isNotEmpty 
                    ? description 
                    : "Bu madde için detaylı açıklama bulunmamaktadır.",
                  style: const TextStyle(fontSize: 16),
                ),
              ],
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text("Tamam"),
              onPressed: () {
                Navigator.of(context).pop(); // Pencereyi kapat
              },
            ),
          ],
        );
      },
    );
  }

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("FoodLens AI", style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        backgroundColor: Colors.green.shade100,
      ),
      body: Column(
        children: [
          // FOTOĞRAF ALANI
          Container(
            height: 220,
            width: double.infinity,
            color: Colors.grey.shade200,
            child: _image != null
                ? Image.file(_image!, fit: BoxFit.cover)
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.camera_alt, size: 50, color: Colors.grey),
                      const SizedBox(height: 10),
                      const Text("Analiz için bir fotoğraf çekin 📸"),
                    ],
                  ),
          ),
          
          const SizedBox(height: 15),
          
          // BUTONLAR
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton.icon(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.camera),
                label: const Text("Kamera"),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade50),
              ),
              ElevatedButton.icon(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.photo),
                label: const Text("Galeri"),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.purple.shade50),
              ),
            ],
          ),

          const Divider(thickness: 1, height: 30),

          // SONUÇ BAŞLIĞI
          if (_results.isNotEmpty)
             Padding(
               padding: const EdgeInsets.symmetric(horizontal: 16.0),
               child: const Align(
                 alignment: Alignment.centerLeft,
                 child: Text("Tespit Edilenler (Detay için tıkla)", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
               ),
             ),

          // SONUÇ LİSTESİ
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _results.isEmpty
                    ? Center(
                        child: Text(
                          _image == null ? "" : "Riskli madde bulunamadı",
                          style: const TextStyle(color: Colors.grey),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _results.length,
                        padding: const EdgeInsets.all(10),
                        itemBuilder: (context, index) {
                          final item = _results[index];
                          return Card(
                            color: _getRiskColor(item['risk_level']),
                            margin: const EdgeInsets.only(bottom: 8),
                            elevation: 2,
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: Colors.white,
                                child: Icon(
                                  item['risk_level'] == 'High' ? Icons.warning : Icons.check,
                                  color: _getIconColor(item['risk_level']),
                                ),
                              ),
                              title: Text(item['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Text("Risk: ${item['risk_level']}"),
                              trailing: const Icon(Icons.info_outline, color: Colors.black54),
                              
                              // TIKLAMA İŞLEMİ BURADA
                              onTap: () {
                                _showDescriptionDialog(
                                  context, 
                                  item['name'], 
                                  item['description'] ?? "" 
                                );
                              },
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