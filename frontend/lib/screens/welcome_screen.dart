import 'package:flutter/material.dart';

class WelcomeScreen extends StatelessWidget {
  final Future<void> Function() onContinue;

  const WelcomeScreen({super.key, required this.onContinue});

  Widget _featureCard(IconData icon, String title, String description) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.green.shade100),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Colors.green.shade700),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(color: Colors.black87),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight - 44,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Icon(
                        Icons.eco_rounded,
                        size: 72,
                        color: Colors.green.shade700,
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Center(
                      child: Text(
                        'FoodLens',
                        style: TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    const Center(
                      child: Text(
                        'Gıda ürünlerinin içindekiler bilgisini hızlıca analiz edin, hassasiyetlerinizi takip edin ve önemli ürünleri cihazınıza kaydedin.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 15,
                          color: Colors.black87,
                          height: 1.4,
                        ),
                      ),
                    ),
                    const SizedBox(height: 28),
                    _featureCard(
                      Icons.photo_camera_back_rounded,
                      '3 farklı giriş seçeneği',
                      'Kamerayla fotoğraf çekin, galeriden seçin veya metni doğrudan elle girin.',
                    ),
                    const SizedBox(height: 12),
                    _featureCard(
                      Icons.warning_amber_rounded,
                      'Hassasiyet takibi',
                      'Seçtiğiniz alerjenlerle eşleşen maddeler analiz sonucunda kırmızı şekilde vurgulanır.',
                    ),
                    const SizedBox(height: 12),
                    _featureCard(
                      Icons.bookmark_added_rounded,
                      'Cihaz içi kayıt',
                      'Ürünleri isim vererek kendi cihazınızda saklayabilir ve daha sonra tekrar görüntüleyebilirsiniz.',
                    ),
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Öneri ve Geri Bildirim',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                          SizedBox(height: 6),
                          Text(
                            'Öneri ve geri bildirimleriniz için şu mail adresinden iletişime geçebilirsiniz: foodlens@gmail.com',
                            style: TextStyle(
                              color: Colors.black87,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: () async {
                          await onContinue();
                        },
                        icon: const Icon(Icons.arrow_forward_rounded),
                        label: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 14),
                          child: Text(
                            'Uygulamayı Başlat',
                            style: TextStyle(fontSize: 16),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
