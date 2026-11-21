<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Batch extends Model
{
    protected $fillable = ['batch_code', 'nama_batch', 'target_jumlah', 'status'];

    public function products()
    {
        return $this->hasMany(Product::class);
    }

    public function scanLogs()
    {
        return $this->hasMany(ScanLog::class);
    }
}