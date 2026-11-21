<?php

namespace App\Console\Commands;

use App\Models\Batch;
use App\Models\Product;
use App\Models\ScanLog;
use Illuminate\Console\Command;
use PhpMqtt\Client\ConnectionSettings;
use PhpMqtt\Client\MqttClient;

class MqttConveyorWorker extends Command
{
    protected $signature = 'mqtt:worker';
    protected $description = 'Background worker untuk menangkap log scan MQTT ke database MySQL';

    public function handle()
    {
        $host = env('MQTT_HOST', '192.168.137.230');
        $port = (int) env('MQTT_PORT', 1883);
        $clientId = 'Laravel-Worker-' . uniqid();

        $mqtt = new MqttClient($host, $port, $clientId);
        $settings = (new ConnectionSettings)->setKeepAliveInterval(60);

        $this->info("[MQTT WORKER] Menghubungkan ke broker {$host}:{$port}...");
        $mqtt->connect($settings, true);
        $this->info("[MQTT WORKER] Terhubung! Menunggu data scan dari konveyor...");

        $mqtt->subscribe('kel9_iot/conveyor/data', function (string $topic, string $message) {
            $data = json_decode($message, true);
            if (!$data || !isset($data['uid_barcode'])) {
                return;
            }

            $uid = trim($data['uid_barcode']);
            $statusScan = strtoupper($data['status_scan'] ?? 'VALID');
            $batchId = null;
            $productId = null;

            $parts = explode('-', $uid);
            if (count($parts) >= 2) {
                $batch = Batch::where('batch_code', $parts[0])->first();
                $product = Product::where('product_code', $parts[1])->first();
                $batchId = $batch?->id;
                $productId = $product?->id;
            }

            if (!$batchId) {
                $batchId = Batch::where('status', 'AKTIF')->latest()->value('id');
            }

            ScanLog::create([
                'batch_id'      => $batchId,
                'product_id'    => $productId,
                'uid_barcode'   => $uid,
                'tipe_kode'     => $data['tipe_kode'] ?? 'QRCODE',
                'status_scan'   => in_array($statusScan, ['VALID', 'FAILED']) ? $statusScan : 'VALID',
                'rpm_saat_scan' => (float) ($data['rpm_aktual'] ?? 0),
                'waktu_scan'    => $data['waktu_scan'] ?? now(),
            ]);

            $this->line("[" . now()->format('H:i:s') . "] Tersimpan: {$uid} ({$statusScan})");
        }, 0);

        $mqtt->loop(true);
    }
}