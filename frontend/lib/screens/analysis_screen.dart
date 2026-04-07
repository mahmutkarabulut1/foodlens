import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:foodlens_mobile/services/local_storage_service.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  File? _image;
  bool _isLoading = false;
  List<dynamic> _results = [];
  String _ocrText = "";

  final String apiUrl =
      "https://foodlens-api-592742840350.europe-west3.run.app/analyze";

  final ImagePicker _picker = ImagePicker();
  final TextEditingController _manualTextController = TextEditingController();

  Set<String> _activeAllergens = <String>{};

  @override
  void initState() {
    super.initState();
    LocalStorageService.preferencesVersion.addListener(
      _handlePreferencesChanged,
    );
    _loadActiveAllergens();
  }

  @override
  void dispose() {
    LocalStorageService.preferencesVersion.removeListener(
      _handlePreferencesChanged,
    );
    _manualTextController.dispose();
    super.dispose();
  }

  void _handlePreferencesChanged() {
    _loadActiveAllergens();
  }

  Future<void> _loadActiveAllergens() async {
    final active = await LocalStorageService.getSelectedAllergens();
    if (!mounted) return;

    setState(() {
      _activeAllergens = active;
    });
  }

  String _canonicalizeInputText(String text) {
    String value = text.trim();

    if (value.isEmpty) {
      return "";
    }

    value = value.replaceAll(RegExp(r'\s+'), ' ').trim();

    final hasCue = RegExp(
      r'^\s*(içindekiler|icindekiler|ingredients|ingredient list|bileşenler|bilesenler)\s*:',
      caseSensitive: false,
    ).hasMatch(value);

    if (!hasCue) {
      value = "İçindekiler: $value";
    }

    value = value.replaceAll(
      RegExp(r'\bglukoz\s+şurubu\b', caseSensitive: false),
      'glikoz şurubu',
    );
    value = value.replaceAll(
      RegExp(r'\bglukoz\s+surubu\b', caseSensitive: false),
      'glikoz şurubu',
    );

    return value;
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? pickedFile = await _picker.pickImage(
        source: source,
        maxWidth: 2160,
        maxHeight: 3840,
        imageQuality: 90,
      );

      if (pickedFile == null) {
        return;
      }

      setState(() {
        _image = File(pickedFile.path);
        _results = [];
        _ocrText = "";
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Fotoğraf seçildi. Analiz başlatılıyor..."),
            duration: Duration(seconds: 1),
          ),
        );
      }

      await _processImage();
    } catch (e) {
      _showError("Resim seçilirken hata oluştu: $e");
    }
  }

  Future<void> _processImage() async {
    if (_image == null) return;

    setState(() => _isLoading = true);

    final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);

    try {
      final inputImage = InputImage.fromFile(_image!);
      final RecognizedText recognizedText = await textRecognizer.processImage(
        inputImage,
      );

      final String rawText = recognizedText.text.trim();

      if (rawText.isEmpty) {
        setState(() {
          _isLoading = false;
          _results = [];
          _ocrText = "";
        });

        _showError("Fotoğrafta okunabilir bir içerik metni bulunamadı.");
        return;
      }

      String processedText = rawText;
      final String lowerText = rawText.toLowerCase();

      final int indexTR = lowerText.indexOf("içindekiler");
      final int indexEN = lowerText.indexOf("ingredients");

      if (indexTR != -1) {
        processedText = rawText.substring(indexTR);
      } else if (indexEN != -1) {
        processedText = rawText.substring(indexEN);
      }

      final List<String> lines = processedText.split('\n');
      final List<String> cleanLines = [];

      for (final line in lines) {
        final lowerLine = line.toLowerCase();
        if (!lowerLine.contains("yoktur") &&
            !lowerLine.contains("içermez") &&
            !lowerLine.contains("free from") &&
            !lowerLine.contains("no added")) {
          cleanLines.add(line);
        }
      }

      final String finalText = _canonicalizeInputText(cleanLines.join("\n"));

      if (finalText.trim().isEmpty) {
        setState(() {
          _isLoading = false;
          _results = [];
          _ocrText = "";
        });

        _showError("Fotoğraftaki metin analiz için yeterli değil.");
        return;
      }

      setState(() {
        _ocrText = finalText;
      });

      await _analyzeWithApi(finalText);
    } catch (e) {
      setState(() => _isLoading = false);
      _showError("OCR hatası: $e");
    } finally {
      textRecognizer.close();
    }
  }

  Future<void> _analyzeManualText() async {
    final String raw = _manualTextController.text.trim();

    if (raw.isEmpty) {
      _showError("Lütfen analiz etmek istediğiniz içindekiler metnini girin.");
      return;
    }

    final String text = _canonicalizeInputText(raw);

    setState(() {
      _image = null;
      _results = [];
      _ocrText = text;
      _isLoading = true;
    });

    await _analyzeWithApi(text);
  }

  Future<void> _analyzeWithApi(String text) async {
    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "ocr_text": text,
          "selected_allergens": _activeAllergens.toList(),
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _results = data['results'] ?? [];
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
        _showError("Sunucu hatası: ${response.statusCode}");
      }
    } catch (e) {
      setState(() => _isLoading = false);
      _showError("Bağlantı hatası: $e");
    }
  }

  Future<void> _promptSaveItem() async {
    if (_ocrText.trim().isEmpty) {
      _showError("Kaydetmek için önce bir ürün analizi yapın.");
      return;
    }

    final TextEditingController nameController = TextEditingController();

    final String? productName = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            "Ürünü Kaydet",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          content: TextField(
            controller: nameController,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: "Ürün adı",
              hintText: "Örn. Bitter çikolata",
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text("İptal"),
            ),
            FilledButton(
              onPressed: () {
                final value = nameController.text.trim();
                if (value.isEmpty) return;
                Navigator.of(dialogContext).pop(value);
              },
              child: const Text("Kaydet"),
            ),
          ],
        );
      },
    );

    Future.delayed(
      const Duration(milliseconds: 300),
      () => nameController.dispose(),
    );

    if (productName == null || productName.trim().isEmpty) {
      return;
    }

    await LocalStorageService.saveSavedItem({
      "title": productName.trim(),
      "content": _ocrText,
      "results": _results,
      "savedAt": DateTime.now().toIso8601String(),
    });

    if (!mounted) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final messenger = ScaffoldMessenger.maybeOf(context);
      messenger?.hideCurrentSnackBar();
      messenger?.showSnackBar(
        const SnackBar(content: Text("Ürün cihazınıza kaydedildi.")),
      );
    });
  }

  Future<void> _openManualInputSheet() async {
    _manualTextController.clear();

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            16,
            8,
            16,
            MediaQuery.of(sheetContext).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "İçindekiler Metnini Gir",
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              const SizedBox(height: 8),
              const Text(
                "Fotoğraf net değilse veya ambalaj çok kıvrımlıysa içindekiler metnini doğrudan yazabilirsiniz.",
                style: TextStyle(color: Colors.black87),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: _manualTextController,
                autofocus: true,
                minLines: 5,
                maxLines: 7,
                decoration: const InputDecoration(
                  hintText:
                      "Örn. şeker, glukoz şurubu, süt tozu, soya lesitini...",
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(sheetContext).pop(),
                      child: const Text("Vazgeç"),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () async {
                        Navigator.of(sheetContext).pop();
                        await _analyzeManualText();
                      },
                      icon: const Icon(Icons.analytics_rounded),
                      label: const Text("Analiz Et"),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _showError(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  List<String> _extractParsedIngredients() {
    String text = _ocrText.trim();

    if (text.isEmpty) {
      return <String>[];
    }

    text = text.replaceFirst(
      RegExp(
        r'^\s*(içindekiler|icindekiler|ingredients|bileşenler|bilesenler)\s*:\s*',
        caseSensitive: false,
      ),
      '',
    );

    final rawParts = text.split(RegExp(r'[,;\n]'));
    final seen = <String>{};
    final items = <String>[];

    for (final raw in rawParts) {
      final cleaned = raw.trim();
      if (cleaned.isEmpty) continue;

      final key = cleaned.toLowerCase();
      if (seen.add(key)) {
        items.add(cleaned);
      }
    }

    return items;
  }

  Widget _buildParsedIngredientFallback() {
    final ingredients = _extractParsedIngredients();

    if (ingredients.isEmpty) {
      return const Center(
        child: Text(
          "Eşleşen riskli madde bulunamadı.",
          style: TextStyle(color: Colors.grey),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    "Hassasiyet veya risk eşleşmesi bulunamadı. Yine de algılanan içerikler aşağıda listelenmiştir.",
                    style: TextStyle(height: 1.35),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            "Algılanan İçerikler",
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ingredients
                .map(
                  (item) => Chip(
                    label: Text(item),
                    backgroundColor: Colors.grey.shade200,
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  void _showDescriptionDialog(
    BuildContext context,
    String title,
    String description,
  ) {
    showDialog(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          content: SingleChildScrollView(
            child: Text(
              description.isNotEmpty
                  ? description
                  : "Bu madde için detaylı açıklama bulunmamaktadır.",
              style: const TextStyle(fontSize: 16),
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text("Kapat"),
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },
            ),
          ],
        );
      },
    );
  }

  Color _getRiskColor(String risk) {
    switch (risk.toLowerCase()) {
      case 'high':
        return Colors.red.shade100;
      case 'moderate':
        return Colors.orange.shade100;
      case 'low':
        return Colors.green.shade100;
      default:
        return Colors.grey.shade100;
    }
  }

  Color _getIconColor(String risk) {
    switch (risk.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'moderate':
        return Colors.orange;
      case 'low':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  Widget _buildTopPanel() {
    return Container(
      height: 210,
      width: double.infinity,
      color: Colors.grey.shade200,
      child: Stack(
        fit: StackFit.expand,
        children: [
          _image != null
              ? Image.file(_image!, fit: BoxFit.cover)
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.document_scanner_rounded,
                      size: 54,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(height: 10),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 18),
                      child: Text(
                        "İçindekiler analizini başlatmak için fotoğraf çekin, galeriden seçin veya metni elle girin.",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.black87),
                      ),
                    ),
                  ],
                ),
          if (_isLoading)
            Container(
              color: Colors.black.withValues(alpha: 0.45),
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.white),
                    SizedBox(height: 14),
                    Text(
                      "Analiz ediliyor...",
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      "Lütfen bekleyin",
                      style: TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInputButtons() {
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 10,
      runSpacing: 10,
      children: [
        ElevatedButton.icon(
          onPressed: _isLoading ? null : () => _pickImage(ImageSource.camera),
          icon: const Icon(Icons.camera_alt_rounded),
          label: const Text("Fotoğraf Çek"),
          style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade50),
        ),
        ElevatedButton.icon(
          onPressed: _isLoading ? null : () => _pickImage(ImageSource.gallery),
          icon: const Icon(Icons.photo_library_rounded),
          label: const Text("Galeriden Seç"),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.purple.shade50,
          ),
        ),
        ElevatedButton.icon(
          onPressed: _isLoading ? null : _openManualInputSheet,
          icon: const Icon(Icons.edit_note_rounded),
          label: const Text("Metin Gir"),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.orange.shade50,
          ),
        ),
      ],
    );
  }

  Widget _buildResultsList() {
    if (_isLoading) {
      return const Center(child: SizedBox.shrink());
    }

    if (_results.isEmpty) {
      if (_ocrText.trim().isEmpty && _image == null) {
        return const Center(
          child: Text(
            "Henüz analiz yapılmadı.",
            style: TextStyle(color: Colors.grey),
          ),
        );
      }

      return _buildParsedIngredientFallback();
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 16),
      itemCount: _results.length,
      itemBuilder: (context, index) {
        final item = _results[index];
        final String itemName = (item['name'] ?? 'Bilinmeyen madde').toString();
        final String riskLevel = (item['risk_level'] ?? 'Belirsiz').toString();
        final String description = (item['description'] ?? '').toString();

        final bool isSensitiveMatch = item['user_sensitive_match'] == true;
        final String matchedUserAllergen = (item['matched_user_allergen'] ?? '')
            .toString();

        return Card(
          color: isSensitiveMatch
              ? Colors.red.shade400
              : _getRiskColor(riskLevel),
          margin: const EdgeInsets.only(bottom: 8),
          elevation: isSensitiveMatch ? 6 : 2,
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(
                isSensitiveMatch
                    ? Icons.report_problem_rounded
                    : (riskLevel.toLowerCase() == 'high'
                          ? Icons.warning_amber_rounded
                          : Icons.check_circle_outline_rounded),
                color: isSensitiveMatch ? Colors.red : _getIconColor(riskLevel),
              ),
            ),
            title: Text(
              itemName,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: isSensitiveMatch ? Colors.white : Colors.black,
              ),
            ),
            subtitle: Text(
              isSensitiveMatch
                  ? (matchedUserAllergen.isNotEmpty
                        ? "Hassasiyet eşleşmesi: $matchedUserAllergen"
                        : "Hassasiyetiniz ile eşleşiyor")
                  : "Risk düzeyi: $riskLevel",
              style: TextStyle(
                color: isSensitiveMatch ? Colors.white70 : Colors.black54,
              ),
            ),
            trailing: Icon(
              Icons.info_outline_rounded,
              color: isSensitiveMatch ? Colors.white : Colors.black54,
            ),
            onTap: () {
              _showDescriptionDialog(context, itemName, description);
            },
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "FoodLens",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        backgroundColor: Colors.green.shade100,
        actions: [
          IconButton(
            onPressed: _isLoading ? null : _promptSaveItem,
            tooltip: "Son analizi kaydet",
            icon: const Icon(Icons.bookmark_add_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildTopPanel(),
          const SizedBox(height: 14),
          _buildInputButtons(),
          const SizedBox(height: 10),
          const Divider(thickness: 1, height: 20),
          Expanded(child: _buildResultsList()),
        ],
      ),
    );
  }
}
