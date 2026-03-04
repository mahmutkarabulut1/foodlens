import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SavedItemsScreen extends StatefulWidget {
  const SavedItemsScreen({super.key});

  @override
  State<SavedItemsScreen> createState() => _SavedItemsScreenState();
}

class _SavedItemsScreenState extends State<SavedItemsScreen> {
  List<Map<String, dynamic>> _savedItems = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSavedItems();
  }

  // Hafızadan kaydedilmiş ürünleri çekme (Yenileme işlemlerinde de bu çağrılır)
  Future<void> _loadSavedItems() async {
    final prefs = await SharedPreferences.getInstance();
    final List<String> savedStrings = prefs.getStringList('saved_products') ?? [];

    if (mounted) {
      setState(() {
        _savedItems = savedStrings.map((str) => jsonDecode(str) as Map<String, dynamic>).toList();
        _savedItems = _savedItems.reversed.toList(); 
        _isLoading = false;
      });
    }
  }

  // Ürünü silme fonksiyonu
  Future<void> _deleteItem(int index) async {
    final prefs = await SharedPreferences.getInstance();
    
    setState(() {
      _savedItems.removeAt(index);
    });

    List<String> updatedStrings = _savedItems.reversed.map((item) => jsonEncode(item)).toList();
    await prefs.setStringList('saved_products', updatedStrings);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Ürün silindi."), duration: Duration(seconds: 1))
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Kaydedilen Ürünler", style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        actions: [
          // YENİLEME BUTONU: Ekrana geçince tıklayarak anında güncelleyebilirsin
          IconButton(
            icon: const Icon(Icons.refresh, size: 28),
            tooltip: "Listeyi Yenile",
            onPressed: () {
              setState(() => _isLoading = true); // Yükleniyor animasyonu göster
              _loadSavedItems();
            },
          )
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _savedItems.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.bookmark_border_rounded, size: 80, color: Colors.grey.shade300),
                      const SizedBox(height: 16),
                      const Text("Henüz bir ürün kaydetmediniz.", style: TextStyle(color: Colors.grey, fontWeight: FontWeight.w500)),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 40, vertical: 8),
                        child: Text(
                          "Analiz ekranından kaydettiğiniz ürünleri görmek için sağ üstteki yenile butonuna basabilirsiniz.",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey, fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                )
              // PULL-TO-REFRESH: Liste doluyken ekranı aşağı çekerek yenileme
              : RefreshIndicator(
                  onRefresh: _loadSavedItems,
                  color: Colors.green,
                  child: ListView.builder(
                    itemCount: _savedItems.length,
                    padding: const EdgeInsets.all(12),
                    // Liste az elemanlıysa bile aşağı çekme animasyonu çalışsın diye:
                    physics: const AlwaysScrollableScrollPhysics(), 
                    itemBuilder: (context, index) {
                      final product = _savedItems[index];
                      final List<dynamic> ingredients = product['results'];

                      return Card(
                        elevation: 2,
                        margin: const EdgeInsets.only(bottom: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: ExpansionTile(
                          leading: const CircleAvatar(
                            backgroundColor: Colors.green,
                            child: Icon(Icons.fastfood, color: Colors.white),
                          ),
                          title: Text(product['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text("Kayıt: ${product['date']}"),
                          childrenPadding: const EdgeInsets.all(8),
                          children: [
                            const Divider(),
                            ...ingredients.map((item) {
                              return ListTile(
                                dense: true,
                                leading: Icon(
                                  item['risk_level'] == 'High' ? Icons.warning : Icons.info,
                                  color: item['risk_level'] == 'High' ? Colors.red : Colors.orange,
                                ),
                                title: Text(item['name']),
                                trailing: Text(item['risk_level']),
                              );
                            }),
                            const SizedBox(height: 10),
                            Align(
                              alignment: Alignment.centerRight,
                              child: TextButton.icon(
                                onPressed: () => _deleteItem(index),
                                icon: const Icon(Icons.delete, color: Colors.red),
                                label: const Text("Bu Ürünü Sil", style: TextStyle(color: Colors.red)),
                              ),
                            )
                          ],
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}