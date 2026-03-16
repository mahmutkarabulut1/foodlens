import 'package:flutter/material.dart';
import 'package:foodlens_mobile/services/local_storage_service.dart';

class SavedItemsScreen extends StatefulWidget {
  const SavedItemsScreen({super.key});

  @override
  State<SavedItemsScreen> createState() => _SavedItemsScreenState();
}

class _SavedItemsScreenState extends State<SavedItemsScreen> {
  List<Map<String, dynamic>> _savedItems = <Map<String, dynamic>>[];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    LocalStorageService.savedItemsVersion.addListener(_handleSavedItemsChanged);
    _loadSavedItems();
  }

  @override
  void dispose() {
    LocalStorageService.savedItemsVersion.removeListener(
      _handleSavedItemsChanged,
    );
    super.dispose();
  }

  void _handleSavedItemsChanged() {
    _loadSavedItems();
  }

  Future<void> _loadSavedItems() async {
    final items = await LocalStorageService.getSavedItems();
    if (!mounted) return;

    setState(() {
      _savedItems = items;
      _isLoading = false;
    });
  }

  Future<void> _deleteItem(int index) async {
    await LocalStorageService.deleteSavedItem(index);
    if (!mounted) return;

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text("Kayıt silindi.")));
  }

  String _formatSavedAt(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Tarih bilgisi yok';
    }

    final parsed = DateTime.tryParse(value);
    if (parsed == null) {
      return value;
    }

    String twoDigits(int number) => number.toString().padLeft(2, '0');

    return '${twoDigits(parsed.day)}.${twoDigits(parsed.month)}.${parsed.year} '
        '${twoDigits(parsed.hour)}:${twoDigits(parsed.minute)}';
  }

  void _showSavedItemDetails(Map<String, dynamic> item) {
    final rawResults = item['results'];
    final List<Map<String, dynamic>> results = rawResults is List
        ? rawResults
              .whereType<Map>()
              .map((result) => Map<String, dynamic>.from(result))
              .toList()
        : <Map<String, dynamic>>[];

    final String content = (item['content'] ?? '').toString();

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(
            (item['title'] ?? 'Kayıtlı ürün').toString(),
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'İçindekiler Metni',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      content.isEmpty ? 'Kayıtlı metin bulunmuyor.' : content,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Analiz Sonuçları',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  if (results.isEmpty)
                    const Text('Bu kayıt için analiz sonucu bulunmuyor.')
                  else
                    ...results.map((result) {
                      final name = (result['name'] ?? 'Bilinmeyen madde')
                          .toString();
                      final risk = (result['risk_level'] ?? 'Belirsiz')
                          .toString();

                      return Container(
                        width: double.infinity,
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.green.shade50,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.green.shade100),
                        ),
                        child: Text(
                          '$name\nRisk: $risk',
                          style: const TextStyle(height: 1.4),
                        ),
                      );
                    }),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Kapat'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Kaydedilen Ürünler",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _savedItems.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.bookmark_border_rounded,
                    size: 80,
                    color: Colors.grey.shade300,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "Henüz kayıtlı ürün yok.",
                    style: TextStyle(
                      color: Colors.grey,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 40, vertical: 8),
                    child: Text(
                      "Analiz ekranındaki kaydet butonunu kullanarak ürünleri burada listeleyebilirsiniz.",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _savedItems.length,
              itemBuilder: (context, index) {
                final item = _savedItems[index];
                final rawResults = item['results'];
                final int resultCount = rawResults is List
                    ? rawResults.length
                    : 0;

                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    leading: CircleAvatar(
                      backgroundColor: Colors.green.shade100,
                      child: Icon(
                        Icons.inventory_2_rounded,
                        color: Colors.green.shade700,
                      ),
                    ),
                    title: Text(
                      (item['title'] ?? 'Adsız ürün').toString(),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      '$resultCount eşleşme • ${_formatSavedAt(item['savedAt']?.toString())}',
                    ),
                    onTap: () => _showSavedItemDetails(item),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline_rounded),
                      onPressed: () => _deleteItem(index),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
