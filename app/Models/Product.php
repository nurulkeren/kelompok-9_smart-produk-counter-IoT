<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Product extends Model
{
    protected $fillable = ['batch_id', 'product_code', 'nama_produk', 'berat_gram'];

    public function batch()
    {
        return $this->belongsTo(Batch::class);
    }

    public function scanLogs()
    {
        return $this->hasMany(ScanLog::class);
    }
}