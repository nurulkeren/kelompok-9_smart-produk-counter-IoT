<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ScanLog extends Model
{
    protected $fillable = [
        'batch_id', 'product_id', 'uid_barcode', 'tipe_kode',
        'status_scan', 'rpm_saat_scan', 'waktu_scan'
    ];

    protected $casts = [
        'waktu_scan' => 'datetime',
    ];

    public function batch()
    {
        return $this->belongsTo(Batch::class);
    }

    public function product()
    {
        return $this->belongsTo(Product::class);
    }
}