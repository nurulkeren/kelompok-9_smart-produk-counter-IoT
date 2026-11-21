<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');
Route::post('/batches', [DashboardController::class, 'storeBatch'])->name('batches.store');
Route::post('/products', [DashboardController::class, 'storeProduct'])->name('products.store');
Route::get('/export-csv', [DashboardController::class, 'exportCsv'])->name('export.csv');