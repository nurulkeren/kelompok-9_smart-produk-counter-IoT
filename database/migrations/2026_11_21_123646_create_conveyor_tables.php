<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('batches', function (Blueprint $table) {
            $table->id();
            $table->string('batch_code', 30)->unique();
            $table->string('nama_batch', 100);
            $table->integer('target_jumlah')->default(50);
            $table->enum('status', ['AKTIF', 'SELESAI'])->default('AKTIF');
            $table->timestamps();
        });

        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->foreignId('batch_id')->constrained('batches')->cascadeOnDelete();
            $table->string('product_code', 30)->unique();
            $table->string('nama_produk', 100);
            $table->integer('berat_gram')->default(0);
            $table->timestamps();
        });

        Schema::create('scan_logs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('batch_id')->nullable()->constrained('batches')->nullOnDelete();
            $table->foreignId('product_id')->nullable()->constrained('products')->nullOnDelete();
            $table->string('uid_barcode', 100)->index();
            $table->string('tipe_kode', 30)->default('QRCODE');
            $table->enum('status_scan', ['VALID', 'FAILED'])->default('VALID');
            $table->float('rpm_saat_scan')->default(0);
            $table->timestamp('waktu_scan')->useCurrent();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('scan_logs');
        Schema::dropIfExists('products');
        Schema::dropIfExists('batches');
    }
};